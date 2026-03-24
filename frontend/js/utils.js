/**
 * Utils Module
 * Utility functions for markdown rendering, data processing, etc.
 */

const Utils = {
    /**
     * Render markdown to HTML
     */
    renderMarkdown: (text) => {
        if (!text) return '';
        try {
            return marked.parse(text);
        } catch (e) {
            return text;
        }
    },

    /**
     * Parse markdown tables from text
     */
    parseMarkdownTables: (text) => {
        if (!text) return { hasTable: false, beforeTable: '', tables: [], afterTable: '' };

        const lines = text.split('\n');
        const tables = [];
        let currentTable = null;
        let beforeTable = [];
        let afterTable = [];
        let inTable = false;
        let tableStarted = false;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];

            // Check if this line is a table row
            if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
                if (!inTable) {
                    inTable = true;
                    tableStarted = true;
                    currentTable = { headers: [], rows: [] };
                }

                const cells = line.split('|').map(c => c.trim()).filter(c => c !== '');

                // Check if this is a separator line
                if (cells.every(c => c.match(/^-+$/))) {
                    continue;
                }

                if (currentTable.headers.length === 0) {
                    currentTable.headers = cells;
                } else {
                    currentTable.rows.push(cells);
                }
            } else {
                if (inTable) {
                    // End of table
                    if (currentTable && currentTable.headers.length > 0) {
                        tables.push(currentTable);
                    }
                    currentTable = null;
                    inTable = false;
                }

                if (tableStarted) {
                    afterTable.push(line);
                } else {
                    beforeTable.push(line);
                }
            }
        }

        // Handle table at end of text
        if (inTable && currentTable && currentTable.headers.length > 0) {
            tables.push(currentTable);
        }

        return {
            hasTable: tables.length > 0,
            beforeTable: beforeTable.join('\n'),
            tables: tables,
            afterTable: afterTable.join('\n')
        };
    },

    /**
     * Check if message has exportable data
     */
    hasExportableData: (msg) => {
        if (!msg) return false;
        if (msg.data && msg.data.rows && msg.data.rows.length > 0) return true;
        if (msg.reasoningLog && msg.reasoningLog.steps) {
            for (const step of msg.reasoningLog.steps) {
                if (step.observation && step.observation.includes('获取到')) {
                    return true;
                }
            }
        }
        return false;
    },

    /**
     * Check if raw data has exportable data
     */
    hasExportableDataRaw: (data) => {
        return data && data.rows && data.rows.length > 0;
    },

    /**
     * Format date for display
     */
    formatDate: (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    },

    /**
     * Generate unique ID
     */
    generateId: () => {
        return 'id-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    },

    /**
     * Debounce function
     */
    debounce: (func, wait) => {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Throttle function
     */
    throttle: (func, limit) => {
        let inThrottle;
        return function(...args) {
            if (!inThrottle) {
                func.apply(this, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
};

// Export for global use
window.Utils = Utils;