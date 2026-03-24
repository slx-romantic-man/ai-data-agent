/**
 * Global Application State
 * Used for sharing state between modules without Vuex
 */
window.__APP_STATE__ = {
    // Auth State
    isLoggedIn: null,
    user: null,
    userQuota: null,

    // UI State
    currentView: null,

    // Chat State
    messages: null,
    chatInput: null,
    chatLoading: null,
    chatContainer: null,
    currentSessionId: null,
    conversations: null,

    // Schema State
    schema: null,
    schemaLoading: null,

    // Table Modal State
    showTableModal: null,
    selectedTable: null,
    tableData: null,
    tableDataLoading: null,

    // History State
    showHistoryModal: null,
    selectedHistory: null,
    historyChatInput: null,
    historySearch: null,

    // API Management State
    apiList: null,
    apisLoading: null,
    deleteMode: null,
    showApiDetailModal: null,
    showAddApiModal: null,
    showEditApiModal: null,
    showDeleteConfirmModal: null,
    selectedApi: null,
    apiToDelete: null,

    // Admin State
    adminTab: null,
    adminUsers: null,
    adminUsersLoading: null,
    adminConvSearch: null,
    adminConvResults: null,
    adminConvLoading: null,
    adminLogs: null,
    adminLogsLoading: null,
    adminConvUsernameFilter: null,
    adminConvStartDate: null,
    adminConvEndDate: null,
    showUserDropdown: null,
    userLogsExpanded: null,

    // Suggestions
    sampleQuestions: null,
};

/**
 * Initialize state with Vue refs
 */
window.__initAppState__ = function(VueRefs) {
    const state = window.__APP_STATE__;
    for (const key in VueRefs) {
        if (state.hasOwnProperty(key)) {
            state[key] = VueRefs[key];
        }
    }
};