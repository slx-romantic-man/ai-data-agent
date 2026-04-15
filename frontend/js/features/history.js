window.AppModules = window.AppModules || {};

window.AppModules.createHistoryFeature = function(deps) {
    const {
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
        onSelectConversation
    } = deps;

    const SESSION_KEY_SELECTED = 'ai_data_agent_selected_conv_id';
    const SESSION_KEY_SCROLL = 'ai_data_agent_history_scroll_top';

    const saveHistoryScrollState = (scrollTop, selectedId) => {
        try {
            if (selectedId) sessionStorage.setItem(SESSION_KEY_SELECTED, selectedId);
            sessionStorage.setItem(SESSION_KEY_SCROLL, String(scrollTop));
        } catch (e) { /* sessionStorage unavailable */ }
    };

    const restoreHistoryScrollState = () => {
        try {
            return {
                selectedId: sessionStorage.getItem(SESSION_KEY_SELECTED) || null,
                scrollTop: parseInt(sessionStorage.getItem(SESSION_KEY_SCROLL) || '0', 10)
            };
        } catch (e) {
            return { selectedId: null, scrollTop: 0 };
        }
    };

    const clearHistoryScrollState = () => {
        try {
            sessionStorage.removeItem(SESSION_KEY_SELECTED);
            sessionStorage.removeItem(SESSION_KEY_SCROLL);
        } catch (e) { /* ignore */ }
    };

    const getMessagePairs = () => {
        const pairs = [];
        for (let i = 0; i < messages.value.length; i += 2) {
            const userMsg = messages.value[i];
            const assistantMsg = messages.value[i + 1];
            if (userMsg && userMsg.role === 'user') {
                pairs.push({
                    user: userMsg.content,
                    assistant: assistantMsg?.content || '',
                    userData: userMsg.data,
                    assistantData: assistantMsg?.data,
                    index: i
                });
            }
        }
        return pairs;
    };

    const showHistoryDetail = (conv, scrollTop) => {
        // Save scroll state before opening modal
        saveHistoryScrollState(scrollTop || 0, conv?.id);
        if (onSelectConversation) onSelectConversation(conv?.id);
        selectedHistory.value = conv;
        showHistoryModal.value = true;
    };

    const continueHistoryChat = async () => {
        if (!historyChatInput.value.trim()) return;

        const question = historyChatInput.value.trim();
        historyChatInput.value = '';

        if (selectedHistory.value && selectedHistory.value.messages) {
            messages.value = JSON.parse(JSON.stringify(selectedHistory.value.messages));
            currentSessionId.value = selectedHistory.value.id;
        }

        showHistoryModal.value = false;
        currentView.value = 'chat';

        chatInput.value = question;
        await nextTick();
        sendMessage();
    };

    return {
        getMessagePairs,
        showHistoryDetail,
        continueHistoryChat,
        saveHistoryScrollState,
        restoreHistoryScrollState,
        clearHistoryScrollState,
        exportToExcel
    };
};
