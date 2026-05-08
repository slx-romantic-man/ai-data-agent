window.AppModules = window.AppModules || {};

window.AppModules.setupViewWatchers = function(deps) {
    const {
        watch,
        onMounted,
        currentView,
        adminTab,
        user,
        userQuota,
        loadAdminUsers,
        loadCreditLogs,
        loadApiCategories,
        loadSystemApis,
        selectedApiCategory,
        loadApis,
        api,
        isLoggedIn,
        loadChatHistory,
        loadSuggestions,
        currentSessionId,
        messages
    } = deps;

    // Watch for admin view change to load data
    watch(currentView, (newView) => {
        if (newView === 'admin' && user.value?.role === 'admin') {
            loadAdminUsers();
            loadCreditLogs();
            loadApiCategories();
            loadSystemApis();
        }
    });

    // Watch for admin tab change to load API data
    watch(adminTab, (newTab) => {
        if (newTab === 'apis') {
            loadApiCategories();
            loadSystemApis();
        }
    });

    // Watch selected category to dynamically refresh API repository
    watch(selectedApiCategory, (newCategoryId) => {
        if (adminTab.value === 'apis') {
            loadSystemApis(newCategoryId || null);
        }
    });

    watch(currentView, (newView) => {
        if (newView === 'apis') {
            loadApis();
        }
    });

    onMounted(async () => {
        // 优先检查本地 token
        if (api.token) {
            try {
                const u = await api.getMe();
                user.value = u;
                isLoggedIn.value = true;
                // Ensure fresh homepage on every mount (no stale session)
                currentSessionId.value = null;
                messages.value = [];
                await loadChatHistory();
                loadSuggestions();
                // Load quota info on refresh
                api.getQuota().then(q => {
                    userQuota.value = q || null;
                }).catch(() => {
                    userQuota.value = null;
                });
            } catch {
                api.clearToken();
                // 本地 token 失效后，尝试 CIA 自动登录
                await tryCiaAutoLogin();
            }
        } else {
            // 无本地 token，尝试 CIA 自动登录
            await tryCiaAutoLogin();
        }

        async function tryCiaAutoLogin() {
            const ciaConfig = await CIAModule.init();
            if (!ciaConfig.enabled) return;
            const status = await CIAModule.checkLoginStatus();
            if (status && status.loggedIn && status.code && status.auth_code) {
                const result = await CIAModule.doLogin(status.code, status.auth_code);
                if (result.success) {
                    api.setToken(result.data.access_token);
                    user.value = result.data.user;
                    userQuota.value = result.data.quota || null;
                    isLoggedIn.value = true;
                    // Refresh quota from server to ensure is_unlimited is correct
                    api.getQuota().then(q => {
                        userQuota.value = q || null;
                    }).catch(() => {});
                    // Ensure fresh homepage on CIA auto-login
                    currentSessionId.value = null;
                    messages.value = [];
                    await loadChatHistory();
                    loadSuggestions();
                }
            }
        }
    });
};
