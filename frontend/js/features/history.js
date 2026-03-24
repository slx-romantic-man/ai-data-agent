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
        sendMessage
    } = deps;

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

    const showHistoryDetail = (conv) => {
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
        continueHistoryChat
    };
};
