window.AppModules = window.AppModules || {};

window.AppModules.createChatFeature = function(deps) {
    const {
        api,
        nextTick,
        chatInput,
        chatLoading,
        messages,
        chatContainer,
        currentSessionId,
        conversations,
        currentView,
        userQuota,
        selectedTable,
        showTableModal,
        tableData,
        tableDataLoading,
        parseMarkdownTables
    } = deps;

    const sendMessage = async () => {
        if (!chatInput.value.trim() || chatLoading.value) return;

        const question = chatInput.value.trim();
        chatInput.value = '';
        messages.value.push({ role: 'user', content: question });
        chatLoading.value = true;

        const assistantMsg = {
            role: 'assistant',
            content: '',
            reasoningLog: { steps: [], total_steps: 0, is_complete: false },
            showThinking: true,
            isTyping: true
        };
        messages.value.push(assistantMsg);

        if (!currentSessionId.value) {
            currentSessionId.value = 'session-' + Date.now();
        }

        try {
            await api.streamChat(currentSessionId.value, question, (event) => {
                const type = event.type;
                const data = event.data;

                if (type === 'thought') {
                    const stepNum = (data.step !== undefined) ? data.step - 1 : assistantMsg.reasoningLog.steps.length;

                    // Ensure steps array has enough elements
                    while (assistantMsg.reasoningLog.steps.length <= stepNum) {
                        assistantMsg.reasoningLog.steps.push({
                            step_number: assistantMsg.reasoningLog.steps.length + 1,
                            thought: '',
                            action: null,
                            observation: null
                        });
                    }

                    const targetText = data.content || '';
                    const currentStep = assistantMsg.reasoningLog.steps[stepNum];

                    if (currentStep && currentStep.thought !== targetText) {
                        let currentIndex = currentStep.thought.length;

                        if (assistantMsg.typewriterInterval) clearInterval(assistantMsg.typewriterInterval);
                        assistantMsg.isTyping = true;

                        assistantMsg.typewriterInterval = setInterval(() => {
                            if (currentIndex < targetText.length) {
                                currentStep.thought += targetText[currentIndex];
                                currentIndex++;
                            } else {
                                clearInterval(assistantMsg.typewriterInterval);
                                assistantMsg.typewriterInterval = null;
                            }
                            nextTick(() => {
                                const container = document.querySelector('.flex-1.overflow-y-auto');
                                if (container) container.scrollTop = container.scrollHeight;
                            });
                        }, 20);
                    }

                    assistantMsg.reasoningLog.total_steps = assistantMsg.reasoningLog.steps.length;
                }
                else if (type === 'action') {
                    const stepNum = (data.step !== undefined) ? data.step - 1 : assistantMsg.reasoningLog.steps.length - 1;
                    if (stepNum >= 0 && assistantMsg.reasoningLog.steps[stepNum]) {
                        assistantMsg.reasoningLog.steps[stepNum].action = data.action;
                    }
                }
                else if (type === 'executing') {
                    const stepNum = (data.step !== undefined) ? data.step - 1 : assistantMsg.reasoningLog.steps.length - 1;
                    if (stepNum >= 0 && assistantMsg.reasoningLog.steps[stepNum]) {
                        assistantMsg.reasoningLog.steps[stepNum].observation = `正在尝试调用: ${data.tool}...`;
                    }
                }
                else if (type === 'observation') {
                    const stepNum = (data.step !== undefined) ? data.step - 1 : assistantMsg.reasoningLog.steps.length - 1;
                    if (stepNum >= 0 && assistantMsg.reasoningLog.steps[stepNum]) {
                        assistantMsg.reasoningLog.steps[stepNum].observation = data.content;
                    }
                }
                else if (type === 'answer') {
                    assistantMsg.content = data.content;
                    if (data.reasoning_log && data.reasoning_log.steps) {
                        data.reasoning_log.steps.forEach((newStep, i) => {
                            if (!assistantMsg.reasoningLog.steps[i]) {
                                assistantMsg.reasoningLog.steps.push(newStep);
                            } else {
                                const oldStep = assistantMsg.reasoningLog.steps[i];
                                if (!assistantMsg.typewriterInterval || i < (data.reasoning_log.steps.length - 1)) {
                                    oldStep.thought = newStep.thought;
                                }
                                oldStep.action = newStep.action;
                                oldStep.observation = newStep.observation;
                            }
                        });
                        assistantMsg.reasoningLog.total_steps = data.reasoning_log.total_steps;
                    }
                }
                else if (type === 'data') {
                    // F-10: Progressive streaming of analysis text
                    assistantMsg.data = {
                        columns: data.columns,
                        rows: data.rows,
                        total: data.total
                    };
                    assistantMsg.sql = data.sql;
                }
                else if (type === 'streaming_text') {
                    // F-10: Append streaming analysis text progressively
                    assistantMsg.content += (data.content || '');
                }
                else if (type === 'approval_required') {
                    assistantMsg.approval = {
                        thread_id: data.thread_id,
                        plan: data.plan,
                        current_step: data.current_step,
                        status: 'pending'
                    };
                }
                else if (type === 'done') {
                    if (assistantMsg.typewriterInterval) clearInterval(assistantMsg.typewriterInterval);
                    assistantMsg.isTyping = false;
                    assistantMsg.reasoningLog.is_complete = true;
                    chatLoading.value = false;
                    saveChatHistory();
                }
                else if (type === 'quota') {
                    if (userQuota.value && !userQuota.value.is_unlimited) {
                        userQuota.value.current_balance = data.balance_after;
                    }
                }
                else if (type === 'error') {
                    if (assistantMsg.typewriterInterval) clearInterval(assistantMsg.typewriterInterval);
                    if (data.quota) {
                        assistantMsg.content = '积分不足，请等待每日重置或联系管理员充值。\n当前积分: ' + data.quota.current_balance + '/' + data.quota.daily_limit;
                    } else {
                        assistantMsg.content = '抱歉，处理请求时出错：' + (data.message || '未知错误');
                    }
                    assistantMsg.isTyping = false;
                    chatLoading.value = false;
                }

                nextTick(() => {
                    if (chatContainer.value) {
                        chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
                    }
                });
            });
        } catch (err) {
            assistantMsg.content = '抱歉，处理您的请求时出现错误：' + (err.message || '未知错误');
            assistantMsg.isTyping = false;
            chatLoading.value = false;
            saveChatHistory();
        }
    };

    const startNewConversation = () => {
        if (messages.value.length > 0 && currentSessionId.value) {
            saveCurrentConversation();
        }
        messages.value = [];
        currentSessionId.value = 'session-' + Date.now();
    };

    const saveCurrentConversation = () => {
        if (messages.value.length === 0) return;

        const convId = currentSessionId.value || 'session-' + Date.now();
        const existingIdx = conversations.value.findIndex(c => c.id === convId);

        const conv = {
            id: convId,
            title: messages.value.find(m => m.role === 'user')?.content?.slice(0, 50) || '新对话',
            messages: JSON.parse(JSON.stringify(messages.value)),
            updatedAt: new Date().toISOString()
        };

        if (existingIdx >= 0) {
            conversations.value[existingIdx] = conv;
        } else {
            conv.createdAt = new Date().toISOString();
            conversations.value.unshift(conv);
        }
    };

    const saveChatHistory = () => {
        saveCurrentConversation();
    };

    const loadChatHistory = async () => {
        try {
            const res = await api.getHistory();
            conversations.value = res.conversations || [];
            if (conversations.value.length > 0) {
                const latest = conversations.value[0];
                messages.value = latest.messages || [];
                currentSessionId.value = latest.id;
            }
        } catch (e) {
            console.error('Failed to load chat history:', e);
            conversations.value = [];
            messages.value = [];
        }
    };

    const loadConversation = (conv) => {
        if (messages.value.length > 0) {
            saveCurrentConversation();
        }
        messages.value = conv.messages || [];
        currentSessionId.value = conv.id;
        currentView.value = 'chat';
    };

    const askQuestion = (q) => {
        chatInput.value = q;
        sendMessage();
    };

    const showTableData = async (tableName) => {
        selectedTable.value = tableName;
        showTableModal.value = true;
        tableDataLoading.value = true;
        try {
            tableData.value = await api.getTableData(tableName);
        } catch (err) {
            console.error('Failed to load table data:', err);
        } finally {
            tableDataLoading.value = false;
        }
    };

    const exportToExcel = async (msg) => {
        if (!msg) return;

        try {
            let exportData = null;

            if (msg.data) {
                const data = msg.data;
                if (data.rows && Array.isArray(data.rows) && data.rows.length > 0) {
                    exportData = data;
                } else if (data.data && Array.isArray(data.data) && data.data.length > 0) {
                    exportData = { rows: data.data };
                } else if (Array.isArray(data) && data.length > 0) {
                    exportData = { rows: data };
                }
            }

            if (!exportData && msg.content) {
                const tables = parseMarkdownTables(msg.content);
                if (tables.length > 0) {
                    const table = tables[0];
                    const rows = table.rows.map(row => {
                        const obj = {};
                        table.headers.forEach((header, idx) => {
                            obj[header] = row[idx] || '';
                        });
                        return obj;
                    });
                    exportData = {
                        columns: table.headers,
                        rows: rows
                    };
                }
            }

            if (!exportData) {
                alert('没有可导出的数据');
                return;
            }

            alert('正在准备导出文件，请稍候...');
            const res = await api.createExport(exportData);
            if (res.status === 'success' && res.download_url) {
                const link = document.createElement('a');
                const baseURL = api.getBaseURL();
                link.href = baseURL.replace('/api/v1', '') + res.download_url;
                link.download = res.filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                alert('导出失败: ' + (res.message || '未知错误'));
            }
        } catch (err) {
            console.error('Export error:', err);
            alert('导出出错: ' + (err.message || '网络请求失败'));
        }
    };

    const handleApproval = async (msg, action) => {
        if (!msg.approval || !msg.approval.thread_id) return;

        try {
            msg.approval.status = 'processing';
            const endpoint = action === 'approve'
                ? `/approval/${msg.approval.thread_id}/approve`
                : `/approval/${msg.approval.thread_id}/reject`;

            const res = await api.post(endpoint);
            msg.approval.status = action === 'approve' ? 'approved' : 'rejected';

            if (action === 'approve') {
                chatLoading.value = true;
                await api.streamChat(currentSessionId.value, '', (event) => {
                    const type = event.type;
                    const data = event.data;

                    if (type === 'answer') {
                        msg.content = data.content;
                    } else if (type === 'data') {
                        msg.data = {
                            columns: data.columns,
                            rows: data.rows,
                            total: data.total
                        };
                        msg.sql = data.sql;
                    } else if (type === 'done') {
                        chatLoading.value = false;
                    }
                });
            }
        } catch (err) {
            msg.approval.status = 'error';
            alert('操作失败: ' + (err.message || '未知错误'));
        }
    };

    return {
        sendMessage,
        startNewConversation,
        saveCurrentConversation,
        saveChatHistory,
        loadChatHistory,
        loadConversation,
        askQuestion,
        showTableData,
        exportToExcel,
        handleApproval
    };
};
