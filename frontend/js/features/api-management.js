window.AppModules = window.AppModules || {};

window.AppModules.createApiManagementFeature = function(deps) {
    const {
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
    } = deps;

    const loadApis = async () => {
        apisLoading.value = true;
        try {
            if (user.value?.role === 'admin') {
                // Admin views all system APIs
                const res = await api.getSystemApis();
                apiList.value = res.apis || [];
            } else {
                // Normal user views their authorized APIs
                const res = await api.getMyApis();
                apiList.value = res.apis || [];
            }

            // Organize APIs into categories for the collapsible panel
            const uncategorized = [];

            if (user.value?.role === 'admin') {
                const categoryRes = await api.getApiCategories();
                const categories = categoryRes.categories || [];

                // Group APIs by category_id
                const apiMap = new Map(); // category_id -> [apis]
                apiList.value.forEach(apiItem => {
                    if (apiItem.category_id) {
                        if (!apiMap.has(apiItem.category_id)) {
                            apiMap.set(apiItem.category_id, []);
                        }
                        apiMap.get(apiItem.category_id).push(apiItem);
                    } else {
                        uncategorized.push(apiItem);
                    }
                });

                // Build tree with APIs
                const buildTreeWithApis = (nodes) => {
                    return nodes.map(node => {
                        const nodeApis = apiMap.get(node.id) || [];
                        return {
                            ...node,
                            apis: nodeApis,
                            children: buildTreeWithApis(node.children || []),
                            apiCount: nodeApis.length // Note: Doesn't count children's APIs
                        };
                    });
                };

                const rootCategories = categories.filter(c => !c.parent_id);
                apiCategoriesWithApis.value = buildTreeWithApis(rootCategories);
            } else {
                // Non-admin users should only see categories that contain authorized APIs
                const authorizedCategoryMap = new Map();

                apiList.value.forEach(apiItem => {
                    if (apiItem.category_id) {
                        if (!authorizedCategoryMap.has(apiItem.category_id)) {
                            const categoryPath = apiItem.category_path || '';
                            const categoryName = categoryPath
                                ? categoryPath.split(' > ').pop()
                                : `分类 ${apiItem.category_id}`;

                            authorizedCategoryMap.set(apiItem.category_id, {
                                id: apiItem.category_id,
                                name: categoryName,
                                description: '',
                                apis: [],
                                children: [],
                                apiCount: 0
                            });
                        }

                        const categoryNode = authorizedCategoryMap.get(apiItem.category_id);
                        categoryNode.apis.push(apiItem);
                        categoryNode.apiCount = categoryNode.apis.length;
                    } else {
                        uncategorized.push(apiItem);
                    }
                });

                apiCategoriesWithApis.value = Array.from(authorizedCategoryMap.values())
                    .sort((a, b) => String(a.name).localeCompare(String(b.name), 'zh-CN'));
            }

            uncategorizedApis.value = uncategorized;

            expandedCategories.value = new Set();
            if (apiCategoriesWithApis.value.length < 5) {
                const collectCategoryIds = (nodes) => {
                    nodes.forEach(node => {
                        expandedCategories.value.add(node.id);
                        collectCategoryIds(node.children || []);
                    });
                };
                collectCategoryIds(apiCategoriesWithApis.value);
            }

        } catch (err) {
            console.error('Failed to load APIs:', err);
            // Never expose fallback mock APIs to non-admin users
            apiList.value = [];
            uncategorizedApis.value = [];
            apiCategoriesWithApis.value = [];
        } finally {
            apisLoading.value = false;
        }
    };

    const toggleCategory = (categoryId) => {
        if (expandedCategories.value.has(categoryId)) {
            expandedCategories.value.delete(categoryId);
        } else {
            expandedCategories.value.add(categoryId);
        }
    };

    const toggleDeleteMode = () => {
        deleteMode.value = !deleteMode.value;
    };

    const viewApiDetail = (apiItem) => {
        selectedApi.value = apiItem;
        showApiDetailModal.value = true;
    };

    const editApi = (apiItem) => {
        selectedApi.value = apiItem;
        apiForm.id = apiItem.config_id || apiItem.id;
        apiForm.name = apiItem.name;
        apiForm.description = apiItem.description || '';
        apiForm.base_url = apiItem.base_url;
        apiForm.auth_type = apiItem.auth?.type || 'none';
        apiForm.api_key_header = apiItem.auth?.api_key_header || 'X-API-Key';
        apiForm.api_key_value = apiItem.auth?.api_key_value || '';
        apiForm.bearer_token = apiItem.auth?.bearer_token || '';
        apiForm.username = apiItem.auth?.username || '';
        apiForm.password = apiItem.auth?.password || '';
        apiForm.timeout = apiItem.timeout || 30;
        apiForm.retry_count = apiItem.retry_count || 3;

        // 加载自定义headers
        apiForm.custom_headers = [];
        if (apiItem.auth?.custom_headers) {
            for (const [key, value] of Object.entries(apiItem.auth.custom_headers)) {
                apiForm.custom_headers.push({ key, value });
            }
        }

        // 转换端点数据为新格式
        apiForm.endpoints = [];
        if (apiItem.endpoints) {
            for (const [name, ep] of Object.entries(apiItem.endpoints)) {
                const params = [];
                if (ep.params_mapping) {
                    for (const [pName, pValue] of Object.entries(ep.params_mapping)) {
                        params.push({
                            name: pName,
                            description: '',
                            required: (ep.required_params || []).includes(pName),
                            default_value: (ep.default_params || {})[pName] || ''
                        });
                    }
                }
                apiForm.endpoints.push({
                    name: name,
                    path: ep.path || '',
                    method: ep.method || 'GET',
                    description: ep.description || '',
                    params: params,
                    required_params: ep.required_params || [],
                    response_data_path: ep.response_data_path || '',
                    response_field_mapping: ep.response_field_mapping || {}
                });
            }
        }
        showEditApiModal.value = true;
    };

    const closeApiModal = () => {
        showAddApiModal.value = false;
        showEditApiModal.value = false;
        selectedApi.value = null;
        apiForm.id = '';
        apiForm.name = '';
        apiForm.description = '';
        apiForm.base_url = '';
        apiForm.auth_type = 'none';
        apiForm.api_key_header = 'X-API-Key';
        apiForm.api_key_value = '';
        apiForm.bearer_token = '';
        apiForm.username = '';
        apiForm.password = '';
        apiForm.custom_headers = [];
        apiForm.endpoints = [];
        apiForm.timeout = 30;
        apiForm.retry_count = 3;
    };

    const saveApi = async () => {
        // 验证必填字段
        if (!apiForm.id || !apiForm.name || !apiForm.base_url) {
            alert('请填写必填字段：服务ID、服务名称、Base URL');
            return;
        }

        // 验证API ID格式
        if (!/^[a-z][a-z0-9_]*$/.test(apiForm.id)) {
            alert('服务ID格式错误：只能包含小写字母、数字和下划线，且必须以字母开头');
            return;
        }

        // 验证端点
        for (const ep of apiForm.endpoints) {
            if (!ep.name || !ep.path) {
                alert('每个工具必须填写名称和路径');
                return;
            }
        }

        try {
            // 构建端点数据
            const endpoints = {};
            for (const ep of apiForm.endpoints) {
                const params_mapping = {};
                const required_params = [];
                const default_params = {};

                for (const param of (ep.params || [])) {
                    if (param.name) {
                        params_mapping[param.name] = param.name;
                        if (param.required) {
                            required_params.push(param.name);
                        }
                        if (param.default_value) {
                            default_params[param.name] = param.default_value;
                        }
                    }
                }

                endpoints[ep.name] = {
                    path: ep.path,
                    method: ep.method,
                    description: ep.description,
                    params_mapping: params_mapping,
                    required_params: required_params,
                    default_params: default_params,
                    response_data_path: ep.response_data_path || null,
                    response_field_mapping: ep.response_field_mapping || {}
                };
            }

            // 构建认证数据 - 保存所有认证字段，以便切换类型时保留
            const auth = {
                type: apiForm.auth_type,
                api_key_header: apiForm.api_key_header || 'X-API-Key',
                api_key_value: apiForm.api_key_value || null,
                bearer_token: apiForm.bearer_token || null,
                username: apiForm.username || null,
                password: apiForm.password || null,
                custom_headers: {}
            };
            // 添加自定义headers
            for (const h of apiForm.custom_headers) {
                if (h.key) {
                    auth.custom_headers[h.key] = h.value;
                }
            }

            const data = {
                config_id: apiForm.id,
                name: apiForm.name,
                description: apiForm.description,
                base_url: apiForm.base_url,
                auth: auth,
                endpoints: endpoints,
                timeout: apiForm.timeout || 30,
                retry_count: apiForm.retry_count || 3
            };

            if (showEditApiModal.value) {
                await api.updateSystemApi(selectedApi.value.id, data);
            } else {
                await api.createSystemApi(data);
            }

            closeApiModal();
            await loadApis();
        } catch (err) {
            console.error('Failed to save API:', err);
            alert('保存失败: ' + (err.response?.data?.detail || err.message || '未知错误'));
        }
    };

    const confirmDeleteApi = (apiItem) => {
        apiToDelete.value = apiItem;
        showDeleteConfirmModal.value = true;
    };

    const deleteApi = async () => {
        try {
            await api.deleteSystemApi(apiToDelete.value.id);
            await loadApis();
        } catch (err) {
            console.error('Failed to delete API:', err);
            alert('删除失败: ' + (err.response?.data?.detail || err.message || '未知错误'));
        } finally {
            showDeleteConfirmModal.value = false;
            apiToDelete.value = null;
            deleteMode.value = false;
        }
    };

    const createCategoryFromApisView = async () => {
        if (!newCategoryForm.name.trim()) {
            alert('请输入类名');
            return;
        }
        try {
            await api.createApiCategory({
                name: newCategoryForm.name.trim(),
                description: newCategoryForm.description.trim(),
                parent_id: null
            });
            newCategoryForm.name = '';
            newCategoryForm.description = '';
            showAddCategoryModal.value = false;
            await loadApis();
        } catch (err) {
            alert('创建分类失败: ' + (err.response?.data?.detail || err.message));
        }
    };

    const moveApiToUncategorized = async (apiId) => {
        try {
            const res = await api.batchCategorizeApis([apiId], null);
            if (!res.success) {
                alert('移出分类失败: ' + (res.message || '未知错误'));
                return;
            }
            await loadApis();
        } catch (err) {
            alert('移出分类失败: ' + (err.response?.data?.detail || err.message));
        }
    };

    const moveApiToCategory = async (apiId) => {
        const categoryId = Number(categorySelectionByApi[apiId]);
        if (!categoryId) {
            alert('请先选择分类');
            return;
        }
        try {
            const res = await api.batchCategorizeApis([apiId], categoryId);
            if (!res.success) {
                alert('加入分类失败: ' + (res.message || '未知错误'));
                return;
            }
            delete categorySelectionByApi[apiId];
            await loadApis();
        } catch (err) {
            alert('加入分类失败: ' + (err.response?.data?.detail || err.message));
        }
    };

    return {
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
    };
};
