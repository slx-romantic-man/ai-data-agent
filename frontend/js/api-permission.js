/**
 * API Permission Management Module
 * Handles API Center, Permission Management, and User API views
 */

// API Permission State
const apiPermissionState = {
    // Categories
    categories: [],
    categoriesTree: [],
    selectedCategory: null,

    // APIs
    apis: [],
    selectedApi: null,

    // Permissions
    userPermissions: [],
    apiGrantedUsers: [],
    permissionOverview: null,

    // My APIs (user view)
    myApis: [],

    // UI State
    activePermissionTab: 'by-user', // 'by-user' or 'by-api'
    showCategoryModal: false,
    showApiModal: false,
    showPermissionModal: false,
    editingCategory: null,
    editingApi: null,

    // Loading states
    loading: {
        categories: false,
        apis: false,
        permissions: false,
        myApis: false
    }
};

// API Permission Methods
const apiPermissionMethods = {
    // ==================== Category Methods ====================

    async loadCategories() {
        apiPermissionState.loading.categories = true;
        try {
            const response = await api.get('/api-permission/categories/tree');
            apiPermissionState.categories = response.categories || [];
            // Build tree structure
            apiPermissionState.categoriesTree = this.buildCategoryTree(apiPermissionState.categories);
        } catch (error) {
            console.error('Failed to load categories:', error);
            showToast('加载分类失败', 'error');
        } finally {
            apiPermissionState.loading.categories = false;
        }
    },

    buildCategoryTree(categories) {
        const map = {};
        const roots = [];

        // Create map
        categories.forEach(cat => {
            map[cat.id] = { ...cat, children: [] };
        });

        // Build tree
        categories.forEach(cat => {
            if (cat.parent_id && map[cat.parent_id]) {
                map[cat.parent_id].children.push(map[cat.id]);
            } else {
                roots.push(map[cat.id]);
            }
        });

        return roots;
    },

    async createCategory(data) {
        try {
            await api.post('/api-permission/categories', data);
            showToast('分类创建成功', 'success');
            await this.loadCategories();
            return true;
        } catch (error) {
            showToast(error.response?.data?.detail || '创建失败', 'error');
            return false;
        }
    },

    async updateCategory(categoryId, data) {
        try {
            await api.put(`/api-permission/categories/${categoryId}`, data);
            showToast('分类更新成功', 'success');
            await this.loadCategories();
            return true;
        } catch (error) {
            showToast(error.response?.data?.detail || '更新失败', 'error');
            return false;
        }
    },

    async deleteCategory(categoryId) {
        if (!confirm('确定要删除此分类吗？如果分类下有API，将无法删除。')) {
            return false;
        }
        try {
            await api.delete(`/api-permission/categories/${categoryId}`);
            showToast('分类删除成功', 'success');
            await this.loadCategories();
            return true;
        } catch (error) {
            showToast(error.response?.data?.detail || '删除失败', 'error');
            return false;
        }
    },

    // ==================== API Methods ====================

    async loadApis(categoryId = null) {
        apiPermissionState.loading.apis = true;
        try {
            const params = categoryId ? { category_id: categoryId } : {};
            const response = await api.get('/api-permission/system-apis', { params });
            apiPermissionState.apis = response.apis || [];
        } catch (error) {
            console.error('Failed to load APIs:', error);
            showToast('加载API列表失败', 'error');
        } finally {
            apiPermissionState.loading.apis = false;
        }
    },

    async createApi(data) {
        try {
            await api.post('/api-permission/system-apis', data);
            showToast('API创建成功', 'success');
            await this.loadApis();
            return true;
        } catch (error) {
            showToast(error.response?.data?.detail || '创建失败', 'error');
            return false;
        }
    },

    async updateApi(apiId, data) {
        try {
            await api.put(`/api-permission/system-apis/${apiId}`, data);
            showToast('API更新成功', 'success');
            await this.loadApis();
            return true;
        } catch (error) {
            showToast(error.response?.data?.detail || '更新失败', 'error');
            return false;
        }
    },

    async deleteApi(apiId) {
        if (!confirm('确定要删除此API吗？相关的用户权限也将被删除。')) {
            return false;
        }
        try {
            await api.delete(`/api-permission/system-apis/${apiId}`);
            showToast('API删除成功', 'success');
            await this.loadApis();
            return true;
        } catch (error) {
            showToast(error.response?.data?.detail || '删除失败', 'error');
            return false;
        }
    },

    // ==================== Permission Methods ====================

    async loadPermissionOverview() {
        apiPermissionState.loading.permissions = true;
        try {
            const response = await api.get('/api-permission/permissions/overview');
            apiPermissionState.permissionOverview = response;
        } catch (error) {
            console.error('Failed to load permission overview:', error);
        } finally {
            apiPermissionState.loading.permissions = false;
        }
    },

    async loadUserPermissions(userId) {
        try {
            const response = await api.get(`/api-permission/permissions/user/${userId}`);
            apiPermissionState.userPermissions = response.permissions || [];
        } catch (error) {
            console.error('Failed to load user permissions:', error);
        }
    },

    async loadApiGrantedUsers(apiId) {
        try {
            const response = await api.get(`/api-permission/permissions/api/${apiId}`);
            apiPermissionState.apiGrantedUsers = response.users || [];
        } catch (error) {
            console.error('Failed to load granted users:', error);
        }
    },

    async grantPermissions(userId, apiConfigIds) {
        try {
            await api.post('/api-permission/permissions/grant', {
                user_id: userId,
                api_config_ids: apiConfigIds
            });
            showToast('权限授予成功', 'success');
            return true;
        } catch (error) {
            showToast(error.response?.data?.detail || '授权失败', 'error');
            return false;
        }
    },

    async revokePermissions(userId, apiConfigIds) {
        try {
            await api.post('/api-permission/permissions/revoke', {
                user_id: userId,
                api_config_ids: apiConfigIds
            });
            showToast('权限撤销成功', 'success');
            return true;
        } catch (error) {
            showToast(error.response?.data?.detail || '撤销失败', 'error');
            return false;
        }
    },

    // ==================== My APIs (User View) ====================

    async loadMyApis() {
        apiPermissionState.loading.myApis = true;
        try {
            const response = await api.get('/api-permission/my-apis');
            apiPermissionState.myApis = response.apis || [];
        } catch (error) {
            console.error('Failed to load my APIs:', error);
        } finally {
            apiPermissionState.loading.myApis = false;
        }
    },

    // ==================== Embedding Methods ====================

    async rebuildEmbeddings() {
        if (!confirm('确定要重建所有API的向量索引吗？这可能需要一些时间。')) {
            return;
        }
        try {
            showToast('正在重建向量索引...', 'info');
            const response = await api.post('/api-permission/system-apis/rebuild-embeddings');
            if (response.success) {
                showToast(response.message, 'success');
            } else {
                showToast(response.message, 'error');
            }
        } catch (error) {
            showToast('重建向量索引失败', 'error');
        }
    }
};

// API Permission Templates
const apiPermissionTemplates = {
    // Category Tree Node
    categoryTreeNode(category, level = 0) {
        const indent = level * 20;
        const hasChildren = category.children && category.children.length > 0;
        return `
            <div class="category-tree-node" data-id="${category.id}" style="padding-left: ${indent}px;">
                <div class="category-node-content ${apiPermissionState.selectedCategory?.id === category.id ? 'active' : ''}">
                    <span class="category-expand" onclick="toggleCategoryExpand(${category.id})">
                        ${hasChildren ? '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>' : ''}
                    </span>
                    <span class="category-name" onclick="selectCategory(${category.id})">${category.name}</span>
                    <span class="category-api-count">(${category.api_count || 0})</span>
                    <div class="category-actions">
                        <button onclick="editCategory(${category.id})" class="btn-icon" title="编辑">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                            </svg>
                        </button>
                        <button onclick="deleteCategory(${category.id})" class="btn-icon text-red-500" title="删除">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-4v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="category-children ${hasChildren ? '' : 'hidden'}">
                    ${hasChildren ? category.children.map(child => this.categoryTreeNode(child, level + 1)).join('') : ''}
                </div>
            </div>
        `;
    },

    // API Card
    apiCard(api) {
        const statusClass = api.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500';
        const statusText = api.is_active ? '启用' : '禁用';
        return `
            <div class="api-card" data-id="${api.id}">
                <div class="api-card-header">
                    <h4 class="api-name">${api.name}</h4>
                    <span class="api-status ${statusClass}">${statusText}</span>
                </div>
                <p class="api-description">${api.description || '暂无描述'}</p>
                <div class="api-meta">
                    <span class="api-category">${api.category_path || '未分类'}</span>
                    <span class="api-id">ID: ${api.config_id}</span>
                </div>
                <div class="api-card-actions">
                    <button onclick="editApi(${api.id})" class="btn-sm btn-secondary">编辑</button>
                    <button onclick="manageApiPermissions(${api.id})" class="btn-sm btn-primary">权限管理</button>
                </div>
            </div>
        `;
    },

    // My API Card (User View - no auth info)
    myApiCard(api) {
        return `
            <div class="my-api-card">
                <div class="my-api-header">
                    <div class="my-api-icon">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                        </svg>
                    </div>
                    <h4 class="my-api-name">${api.name}</h4>
                </div>
                <p class="my-api-description">${api.description || '暂无描述'}</p>
                <div class="my-api-category">${api.category_path || '未分类'}</div>
                ${api.endpoints && Object.keys(api.endpoints).length > 0 ? `
                    <div class="my-api-endpoints">
                        <span class="endpoints-label">可用端点:</span>
                        ${Object.keys(api.endpoints).map(ep => `<span class="endpoint-tag">${ep}</span>`).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    },

    // Permission Overview Stats
    overviewStats() {
        const overview = apiPermissionState.permissionOverview;
        if (!overview) return '<div class="loading-placeholder">加载中...</div>';

        return `
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">${overview.total_apis || 0}</div>
                    <div class="stat-label">API 总数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${overview.active_apis || 0}</div>
                    <div class="stat-label">启用中</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">${overview.total_users_with_permissions || 0}</div>
                    <div class="stat-label">有权限用户</div>
                </div>
            </div>
        `;
    },

    // User Permission Summary Table
    userPermissionTable() {
        const overview = apiPermissionState.permissionOverview;
        if (!overview || !overview.by_user) return '';

        return `
            <table class="permission-table">
                <thead>
                    <tr>
                        <th>用户</th>
                        <th>部门</th>
                        <th>API数量</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${overview.by_user.map(user => `
                        <tr>
                            <td>${user.username || user.user_id}</td>
                            <td>${user.department || '-'}</td>
                            <td>${user.api_count}</td>
                            <td>
                                <button onclick="showUserPermissionDetail('${user.user_id}')" class="btn-sm btn-secondary">
                                    查看详情
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    },

    // API Permission Summary Table
    apiPermissionTable() {
        const overview = apiPermissionState.permissionOverview;
        if (!overview || !overview.by_api) return '';

        return `
            <table class="permission-table">
                <thead>
                    <tr>
                        <th>API名称</th>
                        <th>授权用户数</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${overview.by_api.map(api => `
                        <tr>
                            <td>${api.api_name}</td>
                            <td>${api.user_count}</td>
                            <td>
                                <button onclick="showApiGrantedUsers(${api.api_id})" class="btn-sm btn-secondary">
                                    查看用户
                                </button>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    },

    // Recent Calls Table
    recentCallsTable() {
        const overview = apiPermissionState.permissionOverview;
        if (!overview || !overview.recent_calls) return '';

        return `
            <table class="call-log-table">
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>用户</th>
                        <th>API</th>
                        <th>状态</th>
                        <th>耗时</th>
                    </tr>
                </thead>
                <tbody>
                    ${overview.recent_calls.map(log => `
                        <tr>
                            <td>${formatDateTime(log.called_at)}</td>
                            <td>${log.user_id || '-'}</td>
                            <td>${log.api_name || '-'}</td>
                            <td>
                                <span class="status-badge ${log.status === 'success' ? 'success' : 'failed'}">
                                    ${log.status === 'success' ? '成功' : '失败'}
                                </span>
                            </td>
                            <td>${log.response_time_ms ? log.response_time_ms + 'ms' : '-'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }
};

// Helper functions
function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showToast(message, type = 'info') {
    // Use existing toast implementation or create a simple one
    console.log(`[${type}] ${message}`);
    if (window.showToast) {
        window.showToast(message, type);
    }
}

// Category functions
function toggleCategoryExpand(categoryId) {
    const node = document.querySelector(`.category-tree-node[data-id="${categoryId}"]`);
    const children = node?.querySelector('.category-children');
    const expandIcon = node?.querySelector('.category-expand svg');

    if (children) {
        children.classList.toggle('hidden');
        if (expandIcon) {
            expandIcon.style.transform = children.classList.contains('hidden') ? '' : 'rotate(90deg)';
        }
    }
}

function selectCategory(categoryId) {
    const category = apiPermissionState.categories.find(c => c.id === categoryId);
    apiPermissionState.selectedCategory = category;
    // Reload APIs filtered by category
    apiPermissionMethods.loadApis(categoryId);
    // Re-render to update selection state
    renderCategoryTree();
}

async function editCategory(categoryId) {
    const category = apiPermissionState.categories.find(c => c.id === categoryId);
    if (!category) return;

    apiPermissionState.editingCategory = category;
    apiPermissionState.showCategoryModal = true;

    // Show modal
    showCategoryModal(category);
}

async function deleteCategory(categoryId) {
    await apiPermissionMethods.deleteCategory(categoryId);
}

function showCategoryModal(category = null) {
    const modal = document.getElementById('categoryModal');
    if (!modal) return;

    const title = category ? '编辑分类' : '新建分类';
    const name = category?.name || '';
    const description = category?.description || '';
    const parentId = category?.parent_id || '';

    modal.innerHTML = `
        <div class="modal-overlay" onclick="closeCategoryModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button onclick="closeCategoryModal()" class="btn-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>分类名称</label>
                        <input type="text" id="categoryName" value="${name}" placeholder="请输入分类名称">
                    </div>
                    <div class="form-group">
                        <label>描述</label>
                        <textarea id="categoryDescription" placeholder="请输入描述">${description}</textarea>
                    </div>
                    <div class="form-group">
                        <label>父分类</label>
                        <select id="categoryParent">
                            <option value="">无（顶级分类）</option>
                            ${apiPermissionState.categories
                                .filter(c => !category || c.id !== category.id)
                                .map(c => `<option value="${c.id}" ${c.id === parentId ? 'selected' : ''}>${c.name}</option>`)
                                .join('')}
                        </select>
                    </div>
                </div>
                <div class="modal-footer">
                    <button onclick="closeCategoryModal()" class="btn btn-secondary">取消</button>
                    <button onclick="saveCategory(${category?.id || 'null'})" class="btn btn-primary">保存</button>
                </div>
            </div>
        </div>
    `;

    modal.classList.remove('hidden');
}

function closeCategoryModal() {
    const modal = document.getElementById('categoryModal');
    if (modal) {
        modal.classList.add('hidden');
    }
    apiPermissionState.showCategoryModal = false;
    apiPermissionState.editingCategory = null;
}

async function saveCategory(categoryId) {
    const name = document.getElementById('categoryName').value.trim();
    const description = document.getElementById('categoryDescription').value.trim();
    const parentId = document.getElementById('categoryParent').value || null;

    if (!name) {
        showToast('请输入分类名称', 'error');
        return;
    }

    const data = { name, description, parent_id: parentId ? parseInt(parentId) : null };

    let success;
    if (categoryId && categoryId !== 'null') {
        success = await apiPermissionMethods.updateCategory(parseInt(categoryId), data);
    } else {
        success = await apiPermissionMethods.createCategory(data);
    }

    if (success) {
        closeCategoryModal();
    }
}

// API functions
async function editApi(apiId) {
    const apiData = apiPermissionState.apis.find(a => a.id === apiId);
    if (!apiData) return;

    apiPermissionState.editingApi = apiData;
    showApiModal(apiData);
}

async function manageApiPermissions(apiId) {
    const apiData = apiPermissionState.apis.find(a => a.id === apiId);
    if (!apiData) return;

    apiPermissionState.selectedApi = apiData;
    await apiPermissionMethods.loadApiGrantedUsers(apiId);
    showPermissionModal(apiData, 'by-api');
}

function showApiModal(apiData = null) {
    const modal = document.getElementById('apiModal');
    if (!modal) return;

    const title = apiData ? '编辑API' : '新建API';
    const isNew = !apiData;

    modal.innerHTML = `
        <div class="modal-overlay" onclick="closeApiModal()">
            <div class="modal-content modal-lg" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button onclick="closeApiModal()" class="btn-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-row">
                        <div class="form-group">
                            <label>API ID</label>
                            <input type="text" id="apiConfigId" value="${apiData?.config_id || ''}" ${!isNew ? 'disabled' : ''} placeholder="唯一标识符">
                        </div>
                        <div class="form-group">
                            <label>名称</label>
                            <input type="text" id="apiName" value="${apiData?.name || ''}" placeholder="API名称">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>描述</label>
                        <textarea id="apiDescription" placeholder="API描述">${apiData?.description || ''}</textarea>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Base URL</label>
                            <input type="text" id="apiBaseUrl" value="${apiData?.base_url || ''}" placeholder="https://api.example.com">
                        </div>
                        <div class="form-group">
                            <label>分类</label>
                            <select id="apiCategory">
                                <option value="">未分类</option>
                                ${apiPermissionState.categories.map(c =>
                                    `<option value="${c.id}" ${c.id === apiData?.category_id ? 'selected' : ''}>${c.name}</option>`
                                ).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>认证类型</label>
                        <select id="apiAuthType" onchange="toggleAuthFields()">
                            <option value="none" ${apiData?.auth_type === 'none' ? 'selected' : ''}>无认证</option>
                            <option value="api_key" ${apiData?.auth_type === 'api_key' ? 'selected' : ''}>API Key</option>
                            <option value="bearer" ${apiData?.auth_type === 'bearer' ? 'selected' : ''}>Bearer Token</option>
                            <option value="basic" ${apiData?.auth_type === 'basic' ? 'selected' : ''}>Basic Auth</option>
                        </select>
                    </div>
                    <div id="authFields" class="auth-fields-container" style="display: none;">
                        <div class="form-group" id="apiKeyFields">
                            <label>API Key Header</label>
                            <input type="text" id="apiKeyHeader" value="X-API-Key" placeholder="X-API-Key">
                            <label>API Key Value</label>
                            <input type="password" id="apiKeyValue" placeholder="sk-xxx">
                        </div>
                        <div class="form-group" id="bearerFields" style="display: none;">
                            <label>Bearer Token</label>
                            <input type="password" id="bearerToken" placeholder="token">
                        </div>
                        <div class="form-group" id="basicFields" style="display: none;">
                            <label>用户名</label>
                            <input type="text" id="basicUsername" placeholder="username">
                            <label>密码</label>
                            <input type="password" id="basicPassword" placeholder="password">
                        </div>
                    </div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>超时(秒)</label>
                            <input type="number" id="apiTimeout" value="${apiData?.timeout || 30}" min="1" max="300">
                        </div>
                        <div class="form-group">
                            <label>重试次数</label>
                            <input type="number" id="apiRetry" value="${apiData?.retry_count || 3}" min="0" max="10">
                        </div>
                    </div>
                    <div class="form-group">
                        <label class="checkbox-label">
                            <input type="checkbox" id="apiActive" ${apiData?.is_active !== false ? 'checked' : ''}>
                            启用此API
                        </label>
                    </div>
                </div>
                <div class="modal-footer">
                    <button onclick="closeApiModal()" class="btn btn-secondary">取消</button>
                    <button onclick="saveApi(${apiData?.id || 'null'})" class="btn btn-primary">保存</button>
                </div>
            </div>
        </div>
    `;

    modal.classList.remove('hidden');
    toggleAuthFields();
}

function toggleAuthFields() {
    const authType = document.getElementById('apiAuthType').value;
    const authFields = document.getElementById('authFields');
    const apiKeyFields = document.getElementById('apiKeyFields');
    const bearerFields = document.getElementById('bearerFields');
    const basicFields = document.getElementById('basicFields');

    if (authType === 'none') {
        authFields.style.display = 'none';
    } else {
        authFields.style.display = 'block';
        apiKeyFields.style.display = authType === 'api_key' ? 'block' : 'none';
        bearerFields.style.display = authType === 'bearer' ? 'block' : 'none';
        basicFields.style.display = authType === 'basic' ? 'block' : 'none';
    }
}

function closeApiModal() {
    const modal = document.getElementById('apiModal');
    if (modal) {
        modal.classList.add('hidden');
    }
    apiPermissionState.showApiModal = false;
    apiPermissionState.editingApi = null;
}

async function saveApi(apiId) {
    const configId = document.getElementById('apiConfigId').value.trim();
    const name = document.getElementById('apiName').value.trim();
    const description = document.getElementById('apiDescription').value.trim();
    const baseUrl = document.getElementById('apiBaseUrl').value.trim();
    const categoryId = document.getElementById('apiCategory').value || null;
    const authType = document.getElementById('apiAuthType').value;
    const timeout = parseInt(document.getElementById('apiTimeout').value) || 30;
    const retryCount = parseInt(document.getElementById('apiRetry').value) || 3;
    const isActive = document.getElementById('apiActive').checked;

    if (!configId || !name || !baseUrl) {
        showToast('请填写必要信息', 'error');
        return;
    }

    // Build auth config
    let auth = { type: authType };
    if (authType === 'api_key') {
        auth.api_key_header = document.getElementById('apiKeyHeader').value.trim() || 'X-API-Key';
        auth.api_key_value = document.getElementById('apiKeyValue').value.trim();
    } else if (authType === 'bearer') {
        auth.bearer_token = document.getElementById('bearerToken').value.trim();
    } else if (authType === 'basic') {
        auth.username = document.getElementById('basicUsername').value.trim();
        auth.password = document.getElementById('basicPassword').value.trim();
    }

    const data = {
        config_id: configId,
        name,
        description,
        base_url: baseUrl,
        category_id: categoryId ? parseInt(categoryId) : null,
        auth: auth,
        timeout,
        retry_count: retryCount,
        is_active: isActive
    };

    let success;
    if (apiId && apiId !== 'null') {
        success = await apiPermissionMethods.updateApi(parseInt(apiId), data);
    } else {
        success = await apiPermissionMethods.createApi(data);
    }

    if (success) {
        closeApiModal();
    }
}

// Permission Modal
function showPermissionModal(apiOrUser, mode) {
    const modal = document.getElementById('permissionModal');
    if (!modal) return;

    const isByApi = mode === 'by-api';
    const title = isByApi ? `管理 "${apiOrUser.name}" 的用户权限` : `管理用户 "${apiOrUser.username}" 的API权限`;

    modal.innerHTML = `
        <div class="modal-overlay" onclick="closePermissionModal()">
            <div class="modal-content" onclick="event.stopPropagation()">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button onclick="closePermissionModal()" class="btn-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="permission-list">
                        ${isByApi ?
                            renderUsersForPermission(apiOrUser.id) :
                            renderApisForPermission(apiOrUser.user_id)
                        }
                    </div>
                </div>
                <div class="modal-footer">
                    <button onclick="closePermissionModal()" class="btn btn-secondary">关闭</button>
                    <button onclick="savePermissions('${isByApi ? 'api' : 'user'}', ${isByApi ? apiOrUser.id : "'" + apiOrUser.user_id + "'"})" class="btn btn-primary">保存更改</button>
                </div>
            </div>
        </div>
    `;

    modal.classList.remove('hidden');
}

function renderUsersForPermission(apiId) {
    // This would render users with checkboxes for granting/revoking permissions
    return '<p>用户列表加载中...</p>';
}

function renderApisForPermission(userId) {
    // This would render APIs with checkboxes for granting/revoking permissions
    return '<p>API列表加载中...</p>';
}

function closePermissionModal() {
    const modal = document.getElementById('permissionModal');
    if (modal) {
        modal.classList.add('hidden');
    }
    apiPermissionState.showPermissionModal = false;
}

// Render functions
function renderCategoryTree() {
    const container = document.getElementById('categoryTree');
    if (!container) return;

    container.innerHTML = apiPermissionState.categoriesTree.map(cat =>
        apiPermissionTemplates.categoryTreeNode(cat)
    ).join('');
}

function renderApiList() {
    const container = document.getElementById('apiList');
    if (!container) return;

    if (apiPermissionState.loading.apis) {
        container.innerHTML = '<div class="loading">加载中...</div>';
        return;
    }

    if (apiPermissionState.apis.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无API，请先创建分类并添加API</div>';
        return;
    }

    container.innerHTML = apiPermissionState.apis.map(api =>
        apiPermissionTemplates.apiCard(api)
    ).join('');
}

function renderMyApis() {
    const container = document.getElementById('myApisList');
    if (!container) return;

    if (apiPermissionState.loading.myApis) {
        container.innerHTML = '<div class="loading">加载中...</div>';
        return;
    }

    if (apiPermissionState.myApis.length === 0) {
        container.innerHTML = '<div class="empty-state">您暂无可用API，请联系管理员授权</div>';
        return;
    }

    container.innerHTML = apiPermissionState.myApis.map(api =>
        apiPermissionTemplates.myApiCard(api)
    ).join('');
}

function renderPermissionOverview() {
    const statsContainer = document.getElementById('overviewStats');
    const userTableContainer = document.getElementById('userPermTable');
    const apiTableContainer = document.getElementById('apiPermTable');
    const callsTableContainer = document.getElementById('recentCallsTable');

    if (statsContainer) {
        statsContainer.innerHTML = apiPermissionTemplates.overviewStats();
    }
    if (userTableContainer) {
        userTableContainer.innerHTML = apiPermissionTemplates.userPermissionTable();
    }
    if (apiTableContainer) {
        apiTableContainer.innerHTML = apiPermissionTemplates.apiPermissionTable();
    }
    if (callsTableContainer) {
        callsTableContainer.innerHTML = apiPermissionTemplates.recentCallsTable();
    }
}

// Initialize
async function initApiPermissionModule() {
    await Promise.all([
        apiPermissionMethods.loadCategories(),
        apiPermissionMethods.loadApis(),
        apiPermissionMethods.loadPermissionOverview()
    ]);

    renderCategoryTree();
    renderApiList();
    renderPermissionOverview();
}

async function initMyApisModule() {
    await apiPermissionMethods.loadMyApis();
    renderMyApis();
}

// Export for global access
window.apiPermissionState = apiPermissionState;
window.apiPermissionMethods = apiPermissionMethods;
window.apiPermissionTemplates = apiPermissionTemplates;
window.initApiPermissionModule = initApiPermissionModule;
window.initMyApisModule = initMyApisModule;

// Category functions
window.toggleCategoryExpand = toggleCategoryExpand;
window.selectCategory = selectCategory;
window.editCategory = editCategory;
window.deleteCategory = deleteCategory;
window.showCategoryModal = showCategoryModal;
window.closeCategoryModal = closeCategoryModal;
window.saveCategory = saveCategory;

// API functions
window.editApi = editApi;
window.manageApiPermissions = manageApiPermissions;
window.showApiModal = showApiModal;
window.closeApiModal = closeApiModal;
window.saveApi = saveApi;
window.toggleAuthFields = toggleAuthFields;

// Permission functions
window.showPermissionModal = showPermissionModal;
window.closePermissionModal = closePermissionModal;

// Render functions
window.renderCategoryTree = renderCategoryTree;
window.renderApiList = renderApiList;
window.renderMyApis = renderMyApis;
window.renderPermissionOverview = renderPermissionOverview;