window.AppSetup = function() {
    const { ref, reactive, computed, onMounted, watch, nextTick } = Vue;
    return function setup() {
        const isLoggedIn = ref(false);
        const user = ref(null);
        const currentView = ref('chat');
        const userQuota = ref(null);  // User quota info

        const loginForm = reactive({ username: '', password: '' });
        const loginLoading = ref(false);
        const loginError = ref('');

        // Registration state
        const showRegisterForm = ref(false);
        const registerForm = reactive({ login_id: '', username: '', password: '' });
        const registerLoading = ref(false);
        const registerError = ref('');

        const messages = ref([]);
        const chatInput = ref('');
        const chatLoading = ref(false);
        const chatContainer = ref(null);
        const currentSessionId = ref(null);  // Current session ID for context
        const conversations = ref([]);  // All conversations (session-based grouping)

        const showTableModal = ref(false);
        const selectedTable = ref('');
        const tableData = ref(null);
        const tableDataLoading = ref(false);

        // History Modal State
        const showHistoryModal = ref(false);
        const selectedHistory = ref(null);
        const historyChatInput = ref('');
        // F-23: History scroll position & selected conversation tracking
        const historySelectedConvId = ref(null);
        const historyListViewRef = ref(null);

        // API Management State
        const apiList = ref([]);
        const apiCategoriesWithApis = ref([]); // 新增：包含API的分类树
        const uncategorizedApis = ref([]);     // 新增：未分类API
        const expandedCategories = ref(new Set()); // 新增：控制折叠面板展开状态
        const apisLoading = ref(false);
        const deleteMode = ref(false);
        const showApiDetailModal = ref(false);
        const showAddCategoryModal = ref(false);
        const showAddApiModal = ref(false);
        const showEditApiModal = ref(false);
        const showDeleteConfirmModal = ref(false);
        const selectedApi = ref(null);
        const apiToDelete = ref(null);
        const newCategoryForm = reactive({
            name: '',
            description: ''
        });
        const categorySelectionByApi = reactive({});

        // API表单 - 使用更结构化的端点配置
        const apiForm = reactive({
            id: '',
            name: '',
            description: '',
            base_url: '',
            auth_type: 'none',
            api_key_header: 'X-API-Key',
            api_key_value: '',
            bearer_token: '',
            username: '',
            password: '',
            custom_headers: [],
            endpoints: [],  // 端点列表，每个端点是一个对象
            timeout: 30,
            retry_count: 3
        });

        // 添加新端点的模板
        const newEndpoint = () => ({
            name: '',
            path: '',
            method: 'GET',
            description: '',
            params: [],  // 参数列表
            required_params: [],
            response_data_path: ''
        });

        // 添加新参数的模板
        const newParam = () => ({
            name: '',
            description: '',
            required: false,
            default_value: ''
        });

        // Admin Panel State
        const adminTab = ref('users');
        const adminUsers = ref([]);
        const adminUsersLoading = ref(false);
        const adminConvSearch = ref('');
        const adminConvResults = ref([]);
        const adminConvLoading = ref(false);
        const adminLogs = ref([]);
        const adminLogsLoading = ref(false);
        const historySearch = ref('');

        // API Management State
        const apiCategories = ref([]);
        const selectedApiCategory = ref(null);
        const systemApis = ref([]);
        const uncategorizedSystemApis = ref([]);
        const adminApisLoading = ref(false);
        const userPermissions = ref([]);
        const selectedPermUser = ref('');

        // Batch Operations and Search State
        const selectedApiIds = ref([]);
        const selectedUncategorizedApiIds = ref([]);
        const showBatchGrantModal = ref(false);
        const batchGrantSource = ref('categorized');
        const showBatchCategorizeModal = ref(false);
        const batchCategoryTarget = ref(null);
        const selectedBatchUsers = ref([]);
        const batchUserSearchQuery = ref('');
        const showBatchUserDropdown = ref(false);

        // User Permission Overview State
        const userPermissionsOverview = ref(null);
        const selectedPermUserSearch = ref('');
        const showPermUserDropdown = ref(false);
        const overviewExpandedCategories = ref(new Set());
        const availableCategories = computed(() => {
            const result = [];
            const walk = (nodes = []) => {
                nodes.forEach(node => {
                    result.push({ id: node.id, name: node.name });
                    if (node.children && node.children.length > 0) {
                        walk(node.children);
                    }
                });
            };
            walk(apiCategoriesWithApis.value || []);
            return result;
        });

        // Conversation filter state
        const adminConvUsernameFilter = ref('');
        const adminConvStartDate = ref('');
        const adminConvEndDate = ref('');
        const showUserDropdown = ref(false);

        // 用户积分日志分组（按用户ID分组）
        const userLogsExpanded = ref({});
        const userLogsData = computed(() => {
            const grouped = {};
            for (const log of adminLogs.value) {
                if (!grouped[log.user_id]) {
                    grouped[log.user_id] = {
                        user_id: log.user_id,
                        username: log.username,
                        department: '',
                        logs: [],
                        totalCredits: 0,
                        totalTokens: 0
                    };
                }
                grouped[log.user_id].logs.push(log);
                grouped[log.user_id].totalCredits += log.credits_deducted || 0;
                grouped[log.user_id].totalTokens += log.total_tokens || 0;
            }
            for (const userId in grouped) {
                const user = adminUsers.value.find(u => u.user_id === userId);
                if (user) {
                    grouped[userId].department = user.department || '未分配';
                }
            }
            return Object.values(grouped);
        });

        const toggleUserLogs = (userId) => {
            userLogsExpanded.value[userId] = !userLogsExpanded.value[userId];
        };

        // 添加端点
        const addEndpoint = () => {
            apiForm.endpoints.push(newEndpoint());
        };

        // 删除端点
        const removeEndpoint = (index) => {
            apiForm.endpoints.splice(index, 1);
        };

        // 添加参数到端点
        const addParamToEndpoint = (epIndex) => {
            if (!apiForm.endpoints[epIndex].params) {
                apiForm.endpoints[epIndex].params = [];
            }
            apiForm.endpoints[epIndex].params.push(newParam());
        };

        // 删除端点的参数
        const removeParamFromEndpoint = (epIndex, paramIndex) => {
            apiForm.endpoints[epIndex].params.splice(paramIndex, 1);
        };

        // 添加自定义Header
        const addCustomHeader = () => {
            if (!apiForm.custom_headers) {
                apiForm.custom_headers = [];
            }
            apiForm.custom_headers.push({ key: '', value: '' });
        };

        // 删除自定义Header
        const removeCustomHeader = (index) => {
            apiForm.custom_headers.splice(index, 1);
        };

        // Dynamic question suggestions based on user's APIs
        const sampleQuestions = ref([]);

        const loadSuggestions = async () => {
            try {
                const res = await api.getSuggestions();
                sampleQuestions.value = res.suggestions || [];
            } catch (e) {
                console.error('Failed to load suggestions:', e);
                sampleQuestions.value = ['请配置您的API以获取智能推荐'];
            }
        };

        // F-22: Reload suggestions when page returns from background (e.g. tab switch)
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && isLoggedIn.value) {
                loadSuggestions();
            }
        });

        const getRoleName = (role) => {
            const roles = { admin: '管理员', manager: '经理', employee: '员工' };
            return roles[role] || role;
        };

        // DOMPurify configuration — XSS防护白名单（F-16）
        window.__DOMPURIFY_CONFIG__ = {
            ALLOWED_TAGS: [
                'h1','h2','h3','h4','h5','h6',
                'p','br','hr',
                'ul','ol','li',
                'strong','em','b','i','u','s','code','pre',
                'blockquote',
                'a',
                'table','thead','tbody','tr','th','td',
                'div','span',
                'img'
            ],
            ALLOWED_ATTR: ['href','src','alt','title','class','id','data-vkey']
        };

        // Safe markdown renderer — uses DOMPurify to sanitize marked output（F-16）
        const renderSafeMarkdown = (text) => {
            if (!text) return '';
            try {
                const html = marked.parse(text);
                return DOMPurify.sanitize(html, window.__DOMPURIFY_CONFIG__);
            } catch (e) {
                return text;
            }
        };
        window.renderSafeMarkdown = renderSafeMarkdown;  // expose globally for console/testing（F-16）

        // Markdown renderer (legacy alias for backward compatibility)
        const renderMarkdown = (text) => {
            if (!text) return '';
            try {
                return marked.parse(text);
            } catch (e) {
                return text;
            }
        };

        // Parse markdown tables from text content
        const parseMarkdownTables = (text) => {
            if (!text) return [];
            const tables = [];

            // Method 1: Standard markdown tables with | separators
            // Pattern: | col1 | col2 | ... | followed by |---|---|...| and data rows
            const standardTableRegex = /^\|(.+)\|\s*\n\|[-\s|:]+\|\s*\n((?:\|.+\|\s*\n?)+)/gm;

            let match;
            while ((match = standardTableRegex.exec(text)) !== null) {
                const headerLine = match[1];
                const bodyLines = match[2].trim().split('\n');

                // Parse headers
                const headers = headerLine.split('|')
                    .map(h => h.trim())
                    .filter(h => h.length > 0);

                // Parse rows
                const rows = [];
                for (const line of bodyLines) {
                    if (!line.trim()) continue;
                    const allCells = line.split('|').map(c => c.trim());
                    // Skip first and last empty elements (from leading/trailing |)
                    const dataCells = allCells.slice(1, -1);
                    if (dataCells.length > 0) {
                        rows.push(dataCells);
                    }
                }

                if (headers.length > 0 && rows.length > 0) {
                    tables.push({ headers, rows });
                }
            }

            // Method 2: Simple tables without separator row (just lines with |)
            // Try to find consecutive lines that all contain |
            if (tables.length === 0) {
                const lines = text.split('\n');
                let currentTable = null;

                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    // Check if line contains table markers (|)
                    if (line.includes('|') && line.split('|').length >= 3) {
                        const cells = line.split('|').map(c => c.trim()).filter(c => c !== '');

                        if (!currentTable) {
                            // First line could be header or needs separator check
                            const nextLine = lines[i + 1]?.trim() || '';
                            // Check if next line is separator
                            if (nextLine.match(/^\|?[-:\s|]+\|?$/)) {
                                currentTable = { headers: cells, rows: [], skipNext: true };
                                i++; // Skip separator line
                            } else {
                                // No separator, treat as first data row
                                currentTable = { headers: null, rows: [cells], skipNext: false };
                            }
                        } else if (currentTable.skipNext) {
                            currentTable.skipNext = false;
                            continue;
                        } else {
                            // Check if this might be a separator line
                            if (line.match(/^[-:\s|]+$/)) {
                                continue;
                            }
                            currentTable.rows.push(cells);
                        }
                    } else if (currentTable && currentTable.rows.length > 0) {
                        // End of table
                        if (currentTable.headers) {
                            tables.push({ headers: currentTable.headers, rows: currentTable.rows });
                        } else if (currentTable.rows.length >= 1) {
                            // Use first row as header if no explicit header
                            const headers = currentTable.rows[0];
                            const rows = currentTable.rows.slice(1);
                            if (headers.length > 0 && rows.length > 0) {
                                tables.push({ headers, rows });
                            }
                        }
                        currentTable = null;
                    }
                }

                // Handle table at end of text
                if (currentTable && currentTable.rows.length > 0) {
                    if (currentTable.headers) {
                        tables.push({ headers: currentTable.headers, rows: currentTable.rows });
                    } else if (currentTable.rows.length >= 1) {
                        const headers = currentTable.rows[0];
                        const rows = currentTable.rows.slice(1);
                        if (headers.length > 0 && rows.length > 0) {
                            tables.push({ headers, rows });
                        }
                    }
                }
            }

            return tables;
        };

        // Check if message has exportable data
        const hasExportableData = (msg) => {
            if (!msg) return false;

            // Check structured data
            if (msg.data) {
                const data = msg.data;
                if (data.rows && Array.isArray(data.rows) && data.rows.length > 0) return true;
                if (data.data && Array.isArray(data.data) && data.data.length > 0) return true;
                if (Array.isArray(data) && data.length > 0) return true;
            }

            // Check for markdown tables in content
            if (msg.content) {
                const tables = parseMarkdownTables(msg.content);
                if (tables.length > 0) return true;
            }

            return false;
        };

        // Check raw data structure for export
        const hasExportableDataRaw = (data) => {
            if (!data) return false;
            if (data.rows && Array.isArray(data.rows) && data.rows.length > 0) return true;
            if (data.data && Array.isArray(data.data) && data.data.length > 0) return true;
            if (Array.isArray(data) && data.length > 0) return true;
            return false;
        };

        const handleLogin = async () => {
            loginLoading.value = true;
            loginError.value = '';
            try {
                const res = await api.login(loginForm.username, loginForm.password);
                api.setToken(res.access_token);
                user.value = res.user;
                userQuota.value = res.quota || null;  // Store quota info
                isLoggedIn.value = true;
                // Load chat history after login
                loadChatHistory();
                // Load smart suggestions based on user's APIs
                loadSuggestions();
            } catch (err) {
                console.error('Login error:', err);
                let errorMsg = '登录失败';
                if (err.response?.data?.detail) {
                    errorMsg = err.response.data.detail;
                } else if (err.message) {
                    errorMsg = err.message;
                }
                loginError.value = errorMsg;
            } finally {
                loginLoading.value = false;
            }
        };

        const quickLogin = (username, password) => {
            loginForm.username = username;
            loginForm.password = password;
            handleLogin();
        };

        const handleRegister = async () => {
            registerLoading.value = true;
            registerError.value = '';
            try {
                await api.register(registerForm);
                alert('注册成功！请使用新账号登录。');
                showRegisterForm.value = false;
                registerForm.login_id = '';
                registerForm.username = '';
                registerForm.password = '';
            } catch (err) {
                console.error('Registration error:', err);
                registerError.value = err.response?.data?.detail || err.message || '注册失败';
            } finally {
                registerLoading.value = false;
            }
        };

        const cancelRegister = () => {
            showRegisterForm.value = false;
            registerForm.login_id = '';
            registerForm.username = '';
            registerForm.password = '';
            registerError.value = '';
        };

        const handleLogout = () => {
            // Clear auth state
            api.clearToken();
            user.value = null;
            userQuota.value = null;
            isLoggedIn.value = false;

            // Clear chat state
            messages.value = [];
            conversations.value = [];
            currentSessionId.value = null;
            chatInput.value = '';
            sampleQuestions.value = [];

            // Clear history state
            historySearch.value = '';
            showHistoryModal.value = false;
            selectedHistory.value = null;
            historyChatInput.value = '';
            historySelectedConvId.value = null;
            clearHistoryScrollState();

            // Clear admin panel state
            adminTab.value = 'users';
            adminUsers.value = [];
            adminConvSearch.value = '';
            adminConvResults.value = [];
            adminLogs.value = [];
            userLogsExpanded.value = {};
            adminConvUsernameFilter.value = '';
            adminConvStartDate.value = '';
            adminConvEndDate.value = '';
            showUserDropdown.value = false;

            // Clear other state
            currentView.value = 'chat';

            // Clear forms
            loginForm.username = '';
            loginForm.password = '';
            loginError.value = '';
        };

        // F-23: History scroll position tracking
        const onHistoryScroll = (scrollTop) => {
            // Save current scroll state to sessionStorage
            const selectedId = historySelectedConvId.value;
            saveHistoryScrollState(scrollTop, selectedId);
        };

        // Restore history scroll position and highlight when entering history view
        watch(currentView, (newView, oldView) => {
            if (newView === 'history') {
                // Entering history view — restore scroll state
                const state = restoreHistoryScrollState();
                historySelectedConvId.value = state.selectedId;
                nextTick(() => {
                    if (historyListViewRef.value) {
                        historyListViewRef.value.scrollTop = state.scrollTop;
                    }
                });
            } else if (oldView === 'history' && historyListViewRef.value) {
                // Leaving history view — save final scroll state
                saveHistoryScrollState(
                    historyListViewRef.value.scrollTop,
                    historySelectedConvId.value
                );
            }
        });

        // When clicking a conversation in history list, update selected ID
        const onHistoryConvClick = (convId) => {
            historySelectedConvId.value = convId;
        };

        // Thinking status for loading - ReAct style
        const thinkingStatus = ref('正在思考...');
        const thinkingSteps = [
            '正在思考...',
            'Thought: 分析问题...',
            'Action: 选择工具...',
            'Observation: 获取结果...',
            '生成最终回答...'
        ];
        let thinkingInterval = null;

        const startThinkingAnimation = () => {
            let step = 0;
            thinkingStatus.value = thinkingSteps[0];
            thinkingInterval = setInterval(() => {
                step = (step + 1) % thinkingSteps.length;
                thinkingStatus.value = thinkingSteps[step];
            }, 2000);
        };

        const stopThinkingAnimation = () => {
            if (thinkingInterval) {
                clearInterval(thinkingInterval);
                thinkingInterval = null;
            }
        };

        const chatFeature = window.AppModules.createChatFeature({
            api,
            nextTick,
            chatInput,
            chatLoading,
            messages,
            chatContainer,
            currentSessionId,
            conversations,
            currentView,
            userQuota,
            selectedTable,
            showTableModal,
            tableData,
            tableDataLoading,
            parseMarkdownTables,
            loadSuggestions
        });

        const {
            sendMessage,
            startNewConversation,
            saveCurrentConversation,
            saveChatHistory,
            loadChatHistory,
            loadConversation,
            askQuestion,
            showTableData,
            exportToExcel,
            handleApproval
        } = chatFeature;

        const historyFeature = window.AppModules.createHistoryFeature({
            messages,
            selectedHistory,
            showHistoryModal,
            historyChatInput,
            currentSessionId,
            currentView,
            chatInput,
            nextTick,
            sendMessage,
            exportToExcel,
            onSelectConversation: (convId) => { historySelectedConvId.value = convId; }
        });

        const {
            getMessagePairs,
            showHistoryDetail,
            continueHistoryChat,
            saveHistoryScrollState,
            restoreHistoryScrollState,
            clearHistoryScrollState
        } = historyFeature;

        // Admin Panel Methods
        const adminPermissionsFeature = window.AppModules.createAdminPermissionsFeature({
            api,
            computed,
            adminUsers,
            apiCategories,
            selectedApiCategory,
            systemApis,
            uncategorizedSystemApis,
            adminApisLoading,
            userPermissions,
            selectedPermUser,
            userPermissionsOverview,
            selectedPermUserSearch,
            showPermUserDropdown,
            overviewExpandedCategories,
            selectedApiIds,
            selectedUncategorizedApiIds,
            selectedBatchUsers,
            batchUserSearchQuery,
            showBatchUserDropdown,
            showBatchGrantModal,
            batchGrantSource
        });

        const {
            loadApiCategories,
            loadSystemApis,
            loadUserPermissions,
            loadUserPermissionOverview,
            filteredAdminUsers,
            filteredBatchUsers,
            toggleOverviewCategory,
            openBatchUserDropdown,
            closeBatchUserDropdown,
            selectPermUser,
            revokePermission,
            revokePermissionFromOverview,
            toggleSelectAllApis,
            toggleSelectAllUncategorizedApis,
            searchBatchUsers,
            isUserSelected,
            toggleBatchUser,
            removeBatchUser,
            openBatchGrantModal,
            closeBatchGrantModal,
            executeBatchGrant,
            rebuildEmbeddings
        } = adminPermissionsFeature;

        const adminUsersFeature = window.AppModules.createAdminUsersFeature({
            api,
            adminUsers,
            adminUsersLoading,
            adminConvSearch,
            adminConvResults,
            adminConvLoading,
            adminConvUsernameFilter,
            adminConvStartDate,
            adminConvEndDate,
            showUserDropdown,
            selectedHistory,
            showHistoryModal,
            adminLogs,
            adminLogsLoading
        });

        const {
            loadAdminUsers,
            adjustUserQuota,
            adjustUserQuotaPrompt,
            searchAllConversations,
            selectUserFilter,
            applyConvFilters,
            clearConvFilters,
            loadAdminConversationDetail,
            loadCreditLogs
        } = adminUsersFeature;

        const apiManagementFeature = window.AppModules.createApiManagementFeature({
            api,
            user,
            apiList,
            apiCategoriesWithApis,
            uncategorizedApis,
            expandedCategories,
            apisLoading,
            deleteMode,
            showApiDetailModal,
            showAddCategoryModal,
            showAddApiModal,
            showEditApiModal,
            showDeleteConfirmModal,
            selectedApi,
            apiToDelete,
            apiForm,
            newCategoryForm,
            categorySelectionByApi
        });

        const {
            loadApis,
            toggleCategory,
            toggleDeleteMode,
            viewApiDetail,
            editApi,
            closeApiModal,
            saveApi,
            confirmDeleteApi,
            deleteApi,
            createCategoryFromApisView,
            moveApiToUncategorized,
            moveApiToCategory
        } = apiManagementFeature;

        window.AppModules.setupViewWatchers({
            watch,
            onMounted,
            currentView,
            adminTab,
            user,
            loadAdminUsers,
            loadCreditLogs,
            loadApiCategories,
            loadSystemApis,
            selectedApiCategory,
            loadApis,
            api,
            isLoggedIn,
            loadChatHistory
        });

        return {
            isLoggedIn, user, currentView, userQuota,
            loginForm, loginLoading, loginError,
            // Registration
            showRegisterForm, registerForm, registerLoading, registerError,
            handleRegister, cancelRegister,
            messages, chatInput, chatLoading, chatContainer, currentSessionId,
            conversations,
            showTableModal, selectedTable, tableData, tableDataLoading,
            sampleQuestions,
            // History
            showHistoryModal, selectedHistory, historyChatInput, historySearch,
            getMessagePairs, showHistoryDetail, continueHistoryChat, loadConversation,
            saveHistoryScrollState, restoreHistoryScrollState, clearHistoryScrollState,
            historySelectedConvId, historyListViewRef, onHistoryScroll, onHistoryConvClick,
            // Admin Panel
            adminTab, adminUsers, adminUsersLoading, adminConvSearch, adminConvResults, adminConvLoading, adminLogs, adminLogsLoading,
            adminConvUsernameFilter, adminConvStartDate, adminConvEndDate, showUserDropdown,
            loadAdminUsers, adjustUserQuota, adjustUserQuotaPrompt, searchAllConversations, loadAdminConversationDetail, loadCreditLogs,
            selectUserFilter, applyConvFilters, clearConvFilters,
            userLogsExpanded, userLogsData, toggleUserLogs,
            // Admin API Management
            apiCategories, selectedApiCategory, systemApis, uncategorizedSystemApis, adminApisLoading,
            userPermissions, selectedPermUser,
            selectedApiIds, selectedUncategorizedApiIds, showBatchGrantModal, batchGrantSource, selectedBatchUsers, batchUserSearchQuery,
            showBatchUserDropdown,
            userPermissionsOverview, selectedPermUserSearch, showPermUserDropdown, filteredAdminUsers, filteredBatchUsers,
            overviewExpandedCategories,
            loadApiCategories, loadSystemApis, loadUserPermissions, loadUserPermissionOverview,
            revokePermission, rebuildEmbeddings, toggleOverviewCategory,
            toggleSelectAllApis, toggleSelectAllUncategorizedApis, searchBatchUsers, openBatchUserDropdown, closeBatchUserDropdown, isUserSelected, toggleBatchUser,
            removeBatchUser, openBatchGrantModal, closeBatchGrantModal, executeBatchGrant, selectPermUser, revokePermissionFromOverview,
            // API Management
            apiList, apiCategoriesWithApis, uncategorizedApis, expandedCategories, toggleCategory, apisLoading, deleteMode,
            showApiDetailModal, showAddCategoryModal, showAddApiModal, showEditApiModal, showDeleteConfirmModal,
            selectedApi, apiToDelete, apiForm, newCategoryForm, categorySelectionByApi, availableCategories,
            getRoleName, handleLogin, quickLogin, handleLogout,
            sendMessage, askQuestion, startNewConversation, showTableData, exportToExcel, handleApproval,
            loadSuggestions,
            renderMarkdown, renderSafeMarkdown, hasExportableData, hasExportableDataRaw,
            loadApis, toggleDeleteMode, viewApiDetail, editApi, closeApiModal, saveApi, confirmDeleteApi, deleteApi,
            createCategoryFromApisView, moveApiToUncategorized, moveApiToCategory,
            // 新增的端点和参数管理函数
            addEndpoint, removeEndpoint, addParamToEndpoint, removeParamFromEndpoint, addCustomHeader, removeCustomHeader
        };
    };
};
