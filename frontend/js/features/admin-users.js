window.AppModules = window.AppModules || {};

window.AppModules.createAdminUsersFeature = function(deps) {
    const {
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
        adminLogsLoading,
        loadAdminUsersRef
    } = deps;

    const loadAdminUsers = async () => {
        adminUsersLoading.value = true;
        try {
            const res = await api.getAdminUsers();
            adminUsers.value = res.users || [];
        } catch (err) {
            console.error('Failed to load admin users:', err);
        } finally {
            adminUsersLoading.value = false;
        }
    };

    const adjustUserQuota = async (userId, amount) => {
        try {
            await api.adjustUserQuota(userId, amount);
            await loadAdminUsers();
        } catch (err) {
            console.error('Failed to adjust quota:', err);
            alert('调整积分失败: ' + (err.response?.data?.detail || err.message));
        }
    };

    const adjustUserQuotaPrompt = async (userId) => {
        const input = prompt('请输入要调整的积分值（正数为增加，负数为减少）：');
        if (input === null || input === '') return;
        const amount = parseInt(input, 10);
        if (isNaN(amount)) {
            alert('请输入有效的数字');
            return;
        }
        await adjustUserQuota(userId, amount);
    };

    const searchAllConversations = async () => {
        if (!adminConvSearch.value.trim()) return;
        adminConvLoading.value = true;
        try {
            const res = await api.searchAllConversations(adminConvSearch.value);
            adminConvResults.value = res.results || [];
        } catch (err) {
            console.error('Failed to search conversations:', err);
        } finally {
            adminConvLoading.value = false;
        }
    };

    const selectUserFilter = (username) => {
        adminConvUsernameFilter.value = username;
        showUserDropdown.value = false;
    };

    const applyConvFilters = async () => {
        if (!adminConvSearch.value.trim() && !adminConvUsernameFilter.value && !adminConvStartDate.value && !adminConvEndDate.value) {
            return;
        }
        adminConvLoading.value = true;
        try {
            const params = new URLSearchParams();
            if (adminConvSearch.value.trim()) {
                params.append('keyword', adminConvSearch.value.trim());
            }
            if (adminConvUsernameFilter.value) {
                params.append('username', adminConvUsernameFilter.value);
            }
            if (adminConvStartDate.value) {
                params.append('start_date', adminConvStartDate.value);
            }
            if (adminConvEndDate.value) {
                params.append('end_date', adminConvEndDate.value);
            }
            const res = await api.searchConversationsWithFilters(params.toString());
            adminConvResults.value = res.results || [];
        } catch (err) {
            console.error('Filter error:', err);
        } finally {
            adminConvLoading.value = false;
        }
    };

    const clearConvFilters = () => {
        adminConvSearch.value = '';
        adminConvUsernameFilter.value = '';
        adminConvStartDate.value = '';
        adminConvEndDate.value = '';
        adminConvResults.value = [];
    };

    const loadAdminConversationDetail = async (userId, sessionId) => {
        try {
            const res = await api.getAnyAdminConversation(userId, sessionId);
            selectedHistory.value = res;
            showHistoryModal.value = true;
        } catch (err) {
            console.error('Failed to load conversation detail:', err);
            alert('加载对话详情失败: ' + (err.response?.data?.detail || err.message));
        }
    };

    const loadCreditLogs = async () => {
        adminLogsLoading.value = true;
        try {
            const res = await api.getCreditLogs();
            adminLogs.value = res.logs || [];
        } catch (err) {
            console.error('Failed to load credit logs:', err);
        } finally {
            adminLogsLoading.value = false;
        }
    };

    // User status & delete operations
    const toggleUserStatus = async (userId, isActive) => {
        try {
            await api.updateUserStatus(userId, isActive);
            await loadAdminUsers();
        } catch (err) {
            console.error('Failed to update user status:', err);
            alert('操作失败: ' + (err.response?.data?.detail || err.message));
        }
    };

    const deleteUser = async (userId) => {
        try {
            await api.deleteUser(userId);
            await loadAdminUsers();
        } catch (err) {
            console.error('Failed to delete user:', err);
            alert('删除失败: ' + (err.response?.data?.detail || err.message));
        }
    };

    const batchDisableUsers = async (userIds) => {
        try {
            const res = await api.batchDisableUsers(userIds);
            await loadAdminUsers();
            return res;
        } catch (err) {
            console.error('Failed to batch disable users:', err);
            alert('批量禁用失败: ' + (err.response?.data?.detail || err.message));
            return null;
        }
    };

    const batchDeleteUsers = async (userIds) => {
        try {
            const res = await api.batchDeleteUsers(userIds);
            await loadAdminUsers();
            return res;
        } catch (err) {
            console.error('Failed to batch delete users:', err);
            alert('批量删除失败: ' + (err.response?.data?.detail || err.message));
            return null;
        }
    };

    return {
        loadAdminUsers,
        adjustUserQuota,
        adjustUserQuotaPrompt,
        searchAllConversations,
        selectUserFilter,
        applyConvFilters,
        clearConvFilters,
        loadAdminConversationDetail,
        loadCreditLogs,
        toggleUserStatus,
        deleteUser,
        batchDisableUsers,
        batchDeleteUsers
    };
};
