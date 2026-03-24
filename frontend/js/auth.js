/**
 * Authentication Module
 * Handles login, register, logout, and token management
 */

// Auth state factories (to be called in Vue setup)
const createAuthState = (Vue) => {
    const { ref, reactive } = Vue;
    return {
        isLoggedIn: ref(false),
        user: ref(null),
        userQuota: ref(null),
        loginForm: reactive({ username: '', password: '' }),
        loginLoading: ref(false),
        loginError: ref(''),
        showRegisterForm: ref(false),
        registerForm: reactive({ login_id: '', username: '', password: '' }),
        registerLoading: ref(false),
        registerError: ref(''),
    };
};

// Auth methods
const createAuthMethods = (state, Vue, api) => {
    const { nextTick } = Vue;
    const {
        isLoggedIn, user, userQuota,
        loginForm, loginLoading, loginError,
        showRegisterForm, registerForm, registerLoading, registerError,
        messages, conversations, currentSessionId, chatInput,
        sampleQuestions, historySearch, showHistoryModal, selectedHistory,
        historyChatInput, adminTab, adminUsers, adminConvSearch,
        adminConvResults, adminLogs, userLogsExpanded,
        adminConvUsernameFilter, adminConvStartDate, adminConvEndDate,
        showUserDropdown, schema, currentView, loadChatHistory, loadSuggestions
    } = state;

    const handleLogin = async () => {
        loginLoading.value = true;
        loginError.value = '';
        try {
            const res = await api.login(loginForm.username, loginForm.password);
            api.setToken(res.access_token);
            user.value = res.user;
            userQuota.value = res.quota || null;
            isLoggedIn.value = true;
            // Load chat history after login
            if (loadChatHistory) loadChatHistory();
            // Load smart suggestions based on user's APIs
            if (loadSuggestions) loadSuggestions();
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
        if (messages) messages.value = [];
        if (conversations) conversations.value = [];
        if (currentSessionId) currentSessionId.value = null;
        if (chatInput) chatInput.value = '';
        if (sampleQuestions) sampleQuestions.value = [];

        // Clear history state
        if (historySearch) historySearch.value = '';
        if (showHistoryModal) showHistoryModal.value = false;
        if (selectedHistory) selectedHistory.value = null;
        if (historyChatInput) historyChatInput.value = '';

        // Clear admin panel state
        if (adminTab) adminTab.value = 'users';
        if (adminUsers) adminUsers.value = [];
        if (adminConvSearch) adminConvSearch.value = '';
        if (adminConvResults) adminConvResults.value = [];
        if (adminLogs) adminLogs.value = [];
        if (userLogsExpanded) userLogsExpanded.value = {};
        if (adminConvUsernameFilter) adminConvUsernameFilter.value = '';
        if (adminConvStartDate) adminConvStartDate.value = '';
        if (adminConvEndDate) adminConvEndDate.value = '';
        if (showUserDropdown) showUserDropdown.value = false;

        // Clear other state
        if (schema) schema.value = null;
        if (currentView) currentView.value = 'chat';

        // Clear forms
        loginForm.username = '';
        loginForm.password = '';
    };

    const getRoleName = (role) => {
        const roleMap = {
            'admin': '管理员',
            'manager': '经理',
            'employee': '员工',
            'user': '用户'
        };
        return roleMap[role] || role;
    };

    return {
        handleLogin,
        quickLogin,
        handleRegister,
        cancelRegister,
        handleLogout,
        getRoleName,
    };
};

// Export for module usage
window.AuthModule = {
    createAuthState,
    createAuthMethods
};