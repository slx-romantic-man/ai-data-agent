window.AppModules = window.AppModules || {};

window.AppModules.createAdminPermissionsFeature = function(deps) {
    const {
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
    } = deps;

    const loadApiCategories = async () => {
        try {
            const res = await api.get('/api-permission/categories/tree');
            let categories = res.categories || [];

            // Fallback: if backend does not return api_count, compute from system APIs.
            const hasNonZeroCount = categories.some(c => Number(c.api_count || 0) > 0);
            if (!hasNonZeroCount && categories.length > 0) {
                try {
                    const apisRes = await api.get('/api-permission/system-apis');
                    const counts = {};
                    (apisRes.apis || []).forEach(apiItem => {
                        if (apiItem.category_id !== null && apiItem.category_id !== undefined) {
                            counts[apiItem.category_id] = (counts[apiItem.category_id] || 0) + 1;
                        }
                    });
                    categories = categories.map(cat => ({
                        ...cat,
                        api_count: counts[cat.id] || 0
                    }));
                } catch (countErr) {
                    console.error('Failed to build fallback category counts:', countErr);
                }
            }

            apiCategories.value = categories;
        } catch (err) {
            console.error('Failed to load categories:', err);
        }
    };

    const loadUncategorizedSystemApis = async () => {
        const allApisRes = await api.get('/api-permission/system-apis');
        uncategorizedSystemApis.value = (allApisRes.apis || []).filter(
            apiItem => apiItem.category_id === null || apiItem.category_id === undefined
        );
    };

    const loadSystemApis = async (categoryId = null) => {
        adminApisLoading.value = true;
        try {
            const targetCategoryId = categoryId !== null ? categoryId : (selectedApiCategory.value || null);
            const params = targetCategoryId ? { category_id: targetCategoryId } : {};
            const res = await api.get('/api-permission/system-apis', { params });
            const allApis = res.apis || [];

            if (targetCategoryId) {
                systemApis.value = allApis.filter(apiItem => Number(apiItem.category_id) === Number(targetCategoryId));
            } else {
                systemApis.value = allApis.filter(
                    apiItem => apiItem.category_id !== null && apiItem.category_id !== undefined
                );
            }

            selectedApiIds.value = selectedApiIds.value.filter(apiId =>
                systemApis.value.some(apiItem => apiItem.id === apiId)
            );

            await loadUncategorizedSystemApis();
            selectedUncategorizedApiIds.value = selectedUncategorizedApiIds.value.filter(apiId =>
                uncategorizedSystemApis.value.some(apiItem => apiItem.id === apiId)
            );

            await loadApiCategories();
        } catch (err) {
            console.error('Failed to load APIs:', err);
        } finally {
            adminApisLoading.value = false;
        }
    };

    const loadUserPermissions = async () => {
        if (!selectedPermUser.value) return;
        try {
            const res = await api.get(`/api-permission/permissions/user/${selectedPermUser.value}`);
            userPermissions.value = res.permissions || [];
        } catch (err) {
            console.error('Failed to load user permissions:', err);
        }
    };

    const loadUserPermissionOverview = async () => {
        if (!selectedPermUser.value) {
            userPermissionsOverview.value = null;
            return;
        }
        userPermissionsOverview.value = null;
        adminApisLoading.value = true;
        try {
            await loadUncategorizedSystemApis();
            const res = await api.getUserPermissionOverview(selectedPermUser.value);
            const mappedCategorized = (res.categorized || [])
                .map(category => ({
                    ...category,
                    apis: (category.apis || []).map(apiItem => ({
                        ...apiItem,
                        api_name: apiItem.api_name || apiItem.name,
                        api_description: apiItem.api_description || apiItem.description
                    }))
                }))
                .filter(category => (category.apis || []).length > 0);

            userPermissionsOverview.value = {
                user_id: res.user_id,
                username: res.username,
                role: res.role,
                total_permissions: res.total_permissions || 0,
                categorized: mappedCategorized,
                uncategorized: (res.uncategorized || []).map(apiItem => ({
                    ...apiItem,
                    api_name: apiItem.api_name || apiItem.name,
                    api_description: apiItem.api_description || apiItem.description
                }))
            };

            overviewExpandedCategories.value = new Set(
                mappedCategorized.map(category => category.category_id)
            );
        } catch (err) {
            console.error('Failed to load user permission overview:', err);
            overviewExpandedCategories.value = new Set();
            userPermissionsOverview.value = {
                user_id: selectedPermUser.value,
                username: selectedPermUserSearch.value || selectedPermUser.value,
                role: 'employee',
                total_permissions: 0,
                categorized: [],
                uncategorized: []
            };
        } finally {
            adminApisLoading.value = false;
        }
    };

    const filteredAdminUsers = computed(() => {
        const query = selectedPermUserSearch.value.trim().toLowerCase();
        const users = adminUsers.value || [];
        if (!query) return users.slice(0, 20);
        return users.filter(u =>
            (u.username || '').toLowerCase().includes(query) ||
            (u.user_id || '').toLowerCase().includes(query)
        ).slice(0, 20);
    });

    const filteredBatchUsers = computed(() => {
        const query = batchUserSearchQuery.value.trim().toLowerCase();
        const users = adminUsers.value || [];
        if (!query) return users.slice(0, 20);
        return users.filter(u =>
            (u.username || '').toLowerCase().includes(query) ||
            (u.user_id || '').toLowerCase().includes(query)
        ).slice(0, 20);
    });

    const openBatchUserDropdown = () => {
        showBatchUserDropdown.value = true;
    };

    const closeBatchUserDropdown = () => {
        setTimeout(() => {
            showBatchUserDropdown.value = false;
        }, 200);
    };

    const selectPermUser = async (userId) => {
        selectedPermUser.value = userId;
        const selectedUser = adminUsers.value.find(u => u.user_id === userId);
        selectedPermUserSearch.value = selectedUser?.username || userId;
        showPermUserDropdown.value = false;
        await loadUserPermissionOverview();
    };

    const revokePermission = async (userId, apiId) => {
        if (!confirm('确定要取消该用户的 API 授权吗？')) return;
        try {
            await api.post('/api-permission/permissions/revoke', {
                user_id: userId,
                api_config_ids: [apiId]
            });
            loadUserPermissions();
        } catch (err) {
            alert('取消授权失败: ' + (err.response?.data?.detail || err.message));
        }
    };

    const revokePermissionFromOverview = async (apiId) => {
        await revokePermission(selectedPermUser.value, apiId);
        await loadUserPermissionOverview();
    };

    const toggleOverviewCategory = (categoryId) => {
        if (overviewExpandedCategories.value.has(categoryId)) {
            overviewExpandedCategories.value.delete(categoryId);
        } else {
            overviewExpandedCategories.value.add(categoryId);
        }
    };

    const toggleSelectAllApis = (e) => {
        if (e.target.checked) {
            selectedApiIds.value = systemApis.value.map(api => api.id);
        } else {
            selectedApiIds.value = [];
        }
    };

    const toggleSelectAllUncategorizedApis = (e) => {
        if (e.target.checked) {
            selectedUncategorizedApiIds.value = uncategorizedSystemApis.value.map(api => api.id);
        } else {
            selectedUncategorizedApiIds.value = [];
        }
    };

    const searchBatchUsers = async () => {
        // 保留兼容旧调用，当前改为本地筛选 + 下拉
        showBatchUserDropdown.value = true;
    };

    const isUserSelected = (userId) => {
        return selectedBatchUsers.value.some(u => u.user_id === userId);
    };

    const removeBatchUser = (userId) => {
        selectedBatchUsers.value = selectedBatchUsers.value.filter(u => u.user_id !== userId);
    };

    const toggleBatchUser = (user) => {
        if (isUserSelected(user.user_id)) {
            removeBatchUser(user.user_id);
        } else {
            selectedBatchUsers.value.push(user);
        }
    };

    const openBatchGrantModal = (source = 'categorized') => {
        batchGrantSource.value = source;
        showBatchGrantModal.value = true;
    };

    const closeBatchGrantModal = () => {
        showBatchGrantModal.value = false;
    };

    const executeBatchGrantByApiIds = async (apiIds, closeModal) => {
        if (selectedBatchUsers.value.length === 0 || apiIds.length === 0) return;
        try {
            const userIds = selectedBatchUsers.value.map(u => u.user_id);
            const res = await api.batchGrantPermissions(apiIds, userIds);
            if (res.success) {
                alert(`批量授权成功！
成功: ${res.success_count}
失败: ${res.failed?.length || 0}`);
                closeModal();
                selectedBatchUsers.value = [];
                batchUserSearchQuery.value = '';
                showBatchUserDropdown.value = false;
            } else {
                alert('批量授权出现问题: ' + res.message);
            }
        } catch (err) {
            alert('批量授权失败: ' + (err.response?.data?.detail || err.message));
        }
    };

    const executeBatchGrant = async () => {
        const currentApiIds = batchGrantSource.value === 'uncategorized'
            ? selectedUncategorizedApiIds.value
            : selectedApiIds.value;

        await executeBatchGrantByApiIds(currentApiIds, () => {
            showBatchGrantModal.value = false;
            if (batchGrantSource.value === 'uncategorized') {
                selectedUncategorizedApiIds.value = [];
            } else {
                selectedApiIds.value = [];
            }
        });
    };

    const rebuildEmbeddings = async () => {
        if (!confirm('确定要重建所有 API 的向量索引吗？这可能需要一些时间。')) return;
        try {
            const res = await api.post('/api-permission/system-apis/rebuild-embeddings');
            alert(res.message || '重建完成');
        } catch (err) {
            alert('重建失败: ' + (err.response?.data?.detail || err.message));
        }
    };

    return {
        loadApiCategories,
        loadSystemApis,
        loadUncategorizedSystemApis,
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
    };
};
