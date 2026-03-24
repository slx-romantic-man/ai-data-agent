/**
 * API Service Module for AI Data Agent
 */
const API_BASE = 'http://localhost:8002/api/v1';

const api = {
    token: localStorage.getItem('token'),

    setToken(token) {
        this.token = token;
        localStorage.setItem('token', token);
    },

    clearToken() {
        this.token = null;
        localStorage.removeItem('token');
    },

    getHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
    },

    async get(path, config = {}) {
        const res = await axios.get(`${API_BASE}${path}`, {
            headers: this.getHeaders(),
            ...config
        });
        return res.data;
    },

    async post(path, data = {}) {
        const res = await axios.post(`${API_BASE}${path}`, data, { headers: this.getHeaders() });
        return res.data;
    },

    async put(path, data = {}) {
        const res = await axios.put(`${API_BASE}${path}`, data, { headers: this.getHeaders() });
        return res.data;
    },

    async delete(path) {
        const res = await axios.delete(`${API_BASE}${path}`, { headers: this.getHeaders() });
        return res.data;
    },

    async login(username, password) {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        console.log('Attempting login to:', `${API_BASE}/auth/login`);
        try {
            const res = await axios.post(`${API_BASE}/auth/login`, formData);
            console.log('Login response:', res.data);
            return res.data;
        } catch (error) {
            console.error('Login API error:', error.response?.status, error.response?.data || error.message);
            throw error;
        }
    },

    async register(data) {
        const res = await axios.post(`${API_BASE}/auth/register`, data);
        return res.data;
    },

    async getSuggestions() {
        const res = await axios.get(`${API_BASE}/chat/suggestions`, { headers: this.getHeaders() });
        return res.data;
    },

    async getMe() {
        const res = await axios.get(`${API_BASE}/auth/me`, { headers: this.getHeaders() });
        return res.data;
    },

    async getPermissions() {
        const res = await axios.get(`${API_BASE}/auth/permissions`, { headers: this.getHeaders() });
        return res.data;
    },

    async chat(sessionId, message) {
        const res = await axios.post(`${API_BASE}/chat`, {
            session_id: sessionId,
            message: message
        }, { headers: this.getHeaders() });
        return res.data;
    },

    // Streaming chat with SSE
    streamChat(sessionId, message, onEvent) {
        return new Promise((resolve, reject) => {
            const url = `${API_BASE}/chat/stream`;
            const body = JSON.stringify({
                session_id: sessionId,
                message: message
            });

            fetch(url, {
                method: 'POST',
                headers: {
                    ...this.getHeaders(),
                    'Content-Type': 'application/json'
                },
                body: body
            }).then(response => {
                if (!response.ok) {
                    reject(new Error(`Server error: ${response.status} ${response.statusText}`));
                    return;
                }
                if (!response.body) {
                    reject(new Error('Server did not return stream'));
                    return;
                }
                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                function read() {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            resolve();
                            return;
                        }

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || '';

                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                try {
                                    const event = JSON.parse(line.slice(6));
                                    onEvent(event);
                                } catch (e) {
                                    console.error('Parse error:', e);
                                }
                            }
                        }

                        read();
                    }).catch(reject);
                }

                read();
            }).catch(reject);
        });
    },

    async getSchema() {
        const res = await axios.get(`${API_BASE}/chat/debug/schema`, { headers: this.getHeaders() });
        return res.data;
    },

    async getTableData(tableName, limit = 10) {
        const res = await axios.get(`${API_BASE}/chat/debug/tables/${tableName}?limit=${limit}`, { headers: this.getHeaders() });
        return res.data;
    },

    async exportData(sessionId) {
        const res = await axios.get(`${API_BASE}/export/${sessionId}.xlsx`, {
            headers: this.getHeaders(),
            responseType: 'blob'
        });
        return res.data;
    },

    async createExport(data, format = 'xlsx') {
        const res = await axios.post(`${API_BASE}/export`, {
            data: data,
            format: format
        }, { headers: this.getHeaders() });
        return res.data;
    },

    // API Management
    async getApis() {
        const res = await axios.get(`${API_BASE}/apis`, { headers: this.getHeaders() });
        return res.data;
    },

    async getApiDetail(apiId) {
        const res = await axios.get(`${API_BASE}/apis/${apiId}`, { headers: this.getHeaders() });
        return res.data;
    },

    async createApi(data) {
        const res = await axios.post(`${API_BASE}/apis`, data, { headers: this.getHeaders() });
        return res.data;
    },

    async updateApi(apiId, data) {
        const res = await axios.put(`${API_BASE}/apis/${apiId}`, data, { headers: this.getHeaders() });
        return res.data;
    },

    async deleteApi(apiId) {
        const res = await axios.delete(`${API_BASE}/apis/${apiId}`, { headers: this.getHeaders() });
        return res.data;
    },

    // History API
    async getHistory() {
        const res = await axios.get(`${API_BASE}/history`, { headers: this.getHeaders() });
        return res.data;
    },

    async searchHistory(keyword) {
        const res = await axios.get(`${API_BASE}/history/search/query?keyword=${encodeURIComponent(keyword)}`, { headers: this.getHeaders() });
        return res.data;
    },

    // Admin API
    async getAdminUsers() {
        const res = await axios.get(`${API_BASE}/admin/users`, { headers: this.getHeaders() });
        return res.data;
    },

    async adjustUserQuota(userId, amount) {
        const res = await axios.put(`${API_BASE}/admin/users/${userId}/quota`, { amount }, { headers: this.getHeaders() });
        return res.data;
    },

    async getAdminConversations() {
        const res = await axios.get(`${API_BASE}/admin/conversations`, { headers: this.getHeaders() });
        return res.data;
    },

    async searchAllConversations(keyword) {
        const res = await axios.get(`${API_BASE}/admin/conversations/search?keyword=${encodeURIComponent(keyword)}`, { headers: this.getHeaders() });
        return res.data;
    },

    async searchConversationsWithFilters(queryParams) {
        const res = await axios.get(`${API_BASE}/admin/conversations/search?${queryParams}`, { headers: this.getHeaders() });
        return res.data;
    },

    async getAnyAdminConversation(userId, sessionId) {
        const res = await axios.get(`${API_BASE}/admin/conversations/${userId}/${sessionId}`, { headers: this.getHeaders() });
        return res.data;
    },

    async getCreditLogs(userId = null, limit = 100) {
        let url = `${API_BASE}/admin/credit-logs?limit=${limit}`;
        if (userId) url += `&user_id=${userId}`;
        const res = await axios.get(url, { headers: this.getHeaders() });
        return res.data;
    },

    // API Permission Management
    async getApiCategories() {
        const res = await axios.get(`${API_BASE}/api-permission/categories/tree`, { headers: this.getHeaders() });
        return res.data;
    },

    async createApiCategory(data) {
        const res = await axios.post(`${API_BASE}/api-permission/categories`, data, { headers: this.getHeaders() });
        return res.data;
    },

    async updateApiCategory(categoryId, data) {
        const res = await axios.put(`${API_BASE}/api-permission/categories/${categoryId}`, data, { headers: this.getHeaders() });
        return res.data;
    },

    async deleteApiCategory(categoryId) {
        const res = await axios.delete(`${API_BASE}/api-permission/categories/${categoryId}`, { headers: this.getHeaders() });
        return res.data;
    },

    async getSystemApis() {
        const res = await axios.get(`${API_BASE}/api-permission/system-apis`, { headers: this.getHeaders() });
        return res.data;
    },

    async createSystemApi(data) {
        const res = await axios.post(`${API_BASE}/api-permission/system-apis`, data, { headers: this.getHeaders() });
        return res.data;
    },

    async updateSystemApi(apiId, data) {
        const res = await axios.put(`${API_BASE}/api-permission/system-apis/${apiId}`, data, { headers: this.getHeaders() });
        return res.data;
    },

    async deleteSystemApi(apiId) {
        const res = await axios.delete(`${API_BASE}/api-permission/system-apis/${apiId}`, { headers: this.getHeaders() });
        return res.data;
    },

    async getUserPermissions(userId) {
        const res = await axios.get(`${API_BASE}/api-permission/permissions/user/${userId}`, { headers: this.getHeaders() });
        return res.data;
    },

    async grantPermission(userId, apiId, expiresInDays = null) {
        const res = await axios.post(`${API_BASE}/api-permission/permissions/grant`, {
            user_id: userId,
            api_id: apiId,
            expires_in_days: expiresInDays
        }, { headers: this.getHeaders() });
        return res.data;
    },

    async revokePermission(userId, apiId) {
        const res = await axios.post(`${API_BASE}/api-permission/permissions/revoke`, {
            user_id: userId,
            api_id: apiId
        }, { headers: this.getHeaders() });
        return res.data;
    },

    async getPermissionsOverview() {
        const res = await axios.get(`${API_BASE}/api-permission/permissions/overview`, { headers: this.getHeaders() });
        return res.data;
    },

    async batchGrantPermissions(apiIds, userIds) {
        const res = await axios.post(`${API_BASE}/api-permission/permissions/batch-grant`, {
            api_ids: apiIds,
            user_ids: userIds
        }, { headers: this.getHeaders() });
        return res.data;
    },

    async batchRevokePermissions(permissionIds) {
        const res = await axios.post(`${API_BASE}/api-permission/permissions/batch-revoke`, {
            permission_ids: permissionIds
        }, { headers: this.getHeaders() });
        return res.data;
    },

    async searchUsers(query, limit = 50) {
        const res = await axios.get(`${API_BASE}/api-permission/users/search?q=${encodeURIComponent(query)}&limit=${limit}`, { headers: this.getHeaders() });
        return res.data;
    },

    async getUncategorizedApis() {
        const res = await axios.get(`${API_BASE}/api-permission/system-apis/uncategorized`, { headers: this.getHeaders() });
        return res.data;
    },

    async batchCategorizeApis(apiIds, categoryId) {
        const res = await axios.post(`${API_BASE}/api-permission/system-apis/batch-categorize`, {
            api_ids: apiIds,
            category_id: categoryId
        }, { headers: this.getHeaders() });
        return res.data;
    },

    async getUserPermissionOverview(userId) {
        const res = await axios.get(`${API_BASE}/api-permission/users/${userId}/permission-overview`, { headers: this.getHeaders() });
        return res.data;
    },

    async getMyApis() {
        const res = await axios.get(`${API_BASE}/api-permission/my-apis`, { headers: this.getHeaders() });
        return res.data;
    },

    async rebuildApiEmbeddings() {
        const res = await axios.post(`${API_BASE}/api-permission/system-apis/rebuild-embeddings`, {}, { headers: this.getHeaders() });
        return res.data;
    },

    // Expose base URL for download links
    getBaseURL() {
        return API_BASE;
    }
};