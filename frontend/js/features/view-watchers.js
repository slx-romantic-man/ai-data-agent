window.AppModules = window.AppModules || {};

window.AppModules.setupViewWatchers = function(deps) {
    const {
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

    onMounted(() => {
        if (api.token) {
            api.getMe().then(u => {
                user.value = u;
                isLoggedIn.value = true;
                // Load chat history after successful auth check
                loadChatHistory();
            }).catch(() => {
                api.clearToken();
            });
        }
    });
};
