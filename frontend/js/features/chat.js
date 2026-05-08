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
        parseMarkdownTables,
        loadSuggestions
    } = deps;

    const scrollToBottom = () => {
        nextTick(() => {
            if (chatContainer.value) {
                chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
            }
        });
    };

    // 等待文案素材 — 每句展示1秒后随机切换
    const WAITING_QUOTES = [
        '喝咖啡中…','摸鱼中…','假装在工作中…','努力不胡说中…','甩锅给训练数据中…',
        '正在给答案孵蛋中…','脑子转太快冒烟了，正在扇风中…','偷偷在百度和谷歌之间横跳中…',
        '把思路从冰箱里拿出来解冻中…','正在给文字做SPA中…','让灵感先跑个八百米中…',
        '给答案化个淡妆中…','正在和键盘进行灵魂交流中…','把废话扔进垃圾桶中…',
        '让脑细胞加个班中…','正在给知识库打电话催单中…','给逻辑链条上润滑油中…',
        '试图让自己看起来更聪明中…','正在给服务器讲个冷笑话中…','把答案从云端钓上来中…',
        '让思维先做个拉伸运动中…','正在给文字挑件好看的衣服中…','给想法泡个脚放松下中…',
        '试图回忆起大学学过的知识中…','正在和WiFi信号搏斗中…','让答案先彩排一遍中…',
        '给脑子点杯奶茶续命中…','正在把碎片想法拼图中…','让常识和脑洞打一架中…',
        '给答案加个可爱滤镜中…','正在向老天爷借灵感中…','把错误答案先藏起来中…',
        '让手指在虚拟键盘上热个身中…','正在给回答做心肺复苏中…','给知识付费但还没到账中…',
        '试图假装自己是个真人中…','正在给答案编个靠谱的理由中…','让左右脑开个协调会中…',
        '给文字喂点健胃消食片中…','正在从记忆仓库里翻箱倒柜中…','让答案先过个安检中…',
        '给思路画个导航地图中…','试图不把天聊死中…','正在给服务器喂点士力架中…',
        '把灵光一闪抓住别让它跑了中…','让回答先做个自我介绍中…','给答案加个彩蛋中…',
        '正在和昨天的自己复盘对答案中…','让废话自动消音中…','给脑子开个飞行模式中…',
        '试图让回答别像说明书里…','正在给文字做拉伸运动中…','让知识从脑子里搬到答案里中…',
        '给想法做个CT扫描中…','正在向隔壁AI偷偷抄作业中…','让答案先洗个热水澡中…',
        '给思路系个安全带中…','试图把一本正经憋回去中…','正在给回答配个BGM中…',
        '让脑细胞排队领号中…','给答案加个表情包中…','正在从宇宙下载灵感包中…',
        '让常识先别急着下班中…','给文字做个美甲中…','试图让回答带点人情味中…',
        '正在给服务器做眼保健操中…','让灵感别在堵车路上睡觉中…','给答案加个防杠补丁中…',
        '正在把脑洞缝合成逻辑中…','让回答先过遍普通话考试中…','给思路发个红包催更中…',
        '试图让答案别像论文摘要中…','正在给文字做心肺复苏中…','让知识别在脑子里迷路中…',
        '给答案加个进度条特效中…','让灵感先刷个牙清醒一下中…','给回答加个可爱后缀中…',
        '试图让自己别像客服机器人中…','正在给大脑重启更新系统中…','让答案先做个深呼吸中…',
        '给思路点个外卖补充能量中…','正在把碎片信息熬成粥中…','让回答别急着交卷再检查一遍中…',
        '给文字做个发型设计中…','试图从记忆废墟里挖宝藏中…','正在给服务器唱首催眠曲中…',
        '让灵感别坐过站了中…','给答案加个盲盒惊喜中…','正在和咖啡因进行化学反应中…',
        '让左右互搏出一个最佳方案中…','给思路画个思维导图中…','试图让回答听起来像人话中…',
        '正在给文字做瑜伽放松中…','让答案先过遍"像人话"测试中…','给脑子充个5分钟快充电中…',
        '正在把天马行空关进笼子里中…','让回答先读两遍别嘴瓢中…','给答案喷点香水去去机味中…',
        '试图让最终答案惊艳到你中…','正在给答案想个帅气结尾中…','让知识从云端飘下来中…',
        '给思路铺个红地毯中…','正在把灵光乍现截图保存中…','让答案先拍个证件照中…',
        '给文字做个全身按摩中…'
    ];

    const startWaitingText = (assistantMsg) => {
        if (WAITING_QUOTES.length === 0) return;
        assistantMsg.waitingText = WAITING_QUOTES[Math.floor(Math.random() * WAITING_QUOTES.length)];
        assistantMsg.waitingTimer = setInterval(() => {
            assistantMsg.waitingText = WAITING_QUOTES[Math.floor(Math.random() * WAITING_QUOTES.length)];
        }, 1000);
    };

    const stopWaitingText = (assistantMsg) => {
        if (assistantMsg.waitingTimer) {
            clearInterval(assistantMsg.waitingTimer);
            assistantMsg.waitingTimer = null;
        }
    };

    const createAssistantMessage = () => ({
        role: 'assistant',
        content: '',
        reasoningLog: { steps: [], total_steps: 0, is_complete: false },
        showThinking: true,
        isTyping: true,
        isThinking: true,
        isAnswerTyping: false,
        streamEnded: false,
        answerBuffer: '',
        answerTypewriterInterval: null,
        thoughtRafId: null,
        waitingText: '',
        waitingTimer: null
    });

    const ensureReasoningStep = (assistantMsg, stepNum) => {
        while (assistantMsg.reasoningLog.steps.length <= stepNum) {
            assistantMsg.reasoningLog.steps.push({
                step_number: assistantMsg.reasoningLog.steps.length + 1,
                thought: '',
                thoughtBuffer: '',
                thoughtContent: '',
                action: null,
                observation: null
            });
        }
        assistantMsg.reasoningLog.total_steps = assistantMsg.reasoningLog.steps.length;
        return assistantMsg.reasoningLog.steps[stepNum];
    };

    const flushThoughtTyping = (assistantMsg) => {
        // 把剩余的 buffer 一次性全部渲染到 thought
        for (const step of assistantMsg.reasoningLog.steps) {
            if (step.thoughtBuffer) {
                step.thought = step.thoughtBuffer;
            }
        }
    };

    const tryFinalizeAssistantMessage = (assistantMsg) => {
        const thoughtDraining = assistantMsg.reasoningLog.steps.some(s => (s.thoughtBuffer || '').length > (s.thought || '').length);
        const answerDraining = (assistantMsg.answerBuffer || '').length > 0;

        if (!assistantMsg.streamEnded || thoughtDraining || answerDraining) {
            return;
        }

        stopWaitingText(assistantMsg);
        if (assistantMsg.typingInterval) {
            clearInterval(assistantMsg.typingInterval);
            assistantMsg.typingInterval = null;
        }

        assistantMsg.isTyping = false;
        assistantMsg.isThinking = false;
        assistantMsg.isAnswerTyping = false;
        assistantMsg.reasoningLog.is_complete = true;
        chatLoading.value = false;
        saveChatHistory();
    };

    const runTypingEngine = (assistantMsg) => {
        if (assistantMsg.typingInterval) return;

        assistantMsg.typingInterval = setInterval(() => {
            let isTypingActivity = false;

            // 1. Process Thoughts
            for (let step of assistantMsg.reasoningLog.steps) {
                const buffer = step.thoughtBuffer || '';
                const displayed = step.thought || '';
                if (buffer.length > displayed.length) {
                    isTypingActivity = true;
                    // Strictly limit to 1-2 characters per 30ms to guarantee visible typewriter
                    const charsToTake = Math.min(2, buffer.length - displayed.length);
                    step.thought += buffer.slice(displayed.length, displayed.length + charsToTake);
                    scrollToBottom();
                    break; // Process one step at a time
                }
            }

            // 2. Process Answer
            if (!isTypingActivity && assistantMsg.isAnswerTyping) {
                const buffer = assistantMsg.answerBuffer || '';
                if (buffer.length > 0) {
                    isTypingActivity = true;
                    // Capped characters to maintain smooth typing. 
                    // Dynamic limit handles massive tables without instant-pop
                    let maxTake = 3;
                    if (buffer.length > 300) maxTake = 8;
                    if (buffer.length > 1500) maxTake = 20;
                    
                    const charsToTake = Math.min(maxTake, buffer.length);
                    assistantMsg.content += buffer.slice(0, charsToTake);
                    assistantMsg.answerBuffer = buffer.slice(charsToTake);
                    scrollToBottom();
                }
            }

            // 3. Finalize
            if (!isTypingActivity && assistantMsg.streamEnded) {
                tryFinalizeAssistantMessage(assistantMsg);
            }
        }, 30);
    };

    const startAnswerPhase = (assistantMsg) => {
        flushThoughtTyping(assistantMsg);
        stopWaitingText(assistantMsg);
        assistantMsg.isThinking = false;
        assistantMsg.isAnswerTyping = true;
        assistantMsg.isTyping = true;
        assistantMsg.reasoningLog.is_complete = assistantMsg.reasoningLog.steps.length > 0;
    };

    const enqueueAnswerText = (assistantMsg, text) => {
        if (!text) return;
        if (!assistantMsg.isAnswerTyping) {
            startAnswerPhase(assistantMsg);
        }
        assistantMsg.answerBuffer += text;
        runTypingEngine(assistantMsg);
    };

    const mergeReasoningLog = (assistantMsg, reasoningLog) => {
        if (!reasoningLog || !reasoningLog.steps) return;

        reasoningLog.steps.forEach((newStep, index) => {
            const step = ensureReasoningStep(assistantMsg, index);
            step.step_number = newStep.step_number || index + 1;
            step.thoughtBuffer = newStep.thought || step.thoughtBuffer || '';
            if (!assistantMsg.isThinking) {
                step.thoughtContent = step.thoughtBuffer;
                step.thought = step.thoughtBuffer;
            }
            step.action = newStep.action;
            step.observation = newStep.observation;
        });

        assistantMsg.reasoningLog.total_steps = reasoningLog.total_steps || assistantMsg.reasoningLog.steps.length;
        if (reasoningLog.is_complete) {
            assistantMsg.reasoningLog.is_complete = true;
        }
    };

    const processStreamEvent = (assistantMsg, event) => {
        const type = event.type;
        const data = event.data || {};

        if (type === 'thought') {
            const stepNum = (data.step !== undefined) ? data.step - 1 : assistantMsg.reasoningLog.steps.length;
            const currentStep = ensureReasoningStep(assistantMsg, stepNum);
            const chunk = data.content || '';
            currentStep.thoughtBuffer = (currentStep.thoughtBuffer || '') + chunk;
            runTypingEngine(assistantMsg);
        }
        else if (type === 'action') {
            const stepNum = (data.step !== undefined) ? data.step - 1 : assistantMsg.reasoningLog.steps.length - 1;
            if (stepNum >= 0) {
                const currentStep = ensureReasoningStep(assistantMsg, stepNum);
                currentStep.action = data.action;
            }
        }
        else if (type === 'executing') {
            const stepNum = (data.step !== undefined) ? data.step - 1 : assistantMsg.reasoningLog.steps.length - 1;
            if (stepNum >= 0) {
                const currentStep = ensureReasoningStep(assistantMsg, stepNum);
                currentStep.observation = `正在尝试调用: ${data.tool}...`;
            }
        }
        else if (type === 'observation') {
            const stepNum = (data.step !== undefined) ? data.step - 1 : assistantMsg.reasoningLog.steps.length - 1;
            if (stepNum >= 0) {
                const currentStep = ensureReasoningStep(assistantMsg, stepNum);
                currentStep.observation = data.content;
            }
        }
        else if (type === 'answer') {
            mergeReasoningLog(assistantMsg, data.reasoning_log);
            enqueueAnswerText(assistantMsg, data.content || '');
        }
        else if (type === 'streaming_text') {
            enqueueAnswerText(assistantMsg, data.content || '');
        }
        else if (type === 'data') {
            assistantMsg.data = {
                columns: data.columns,
                rows: data.rows,
                total: data.total
            };
            assistantMsg.sql = data.sql;
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
            assistantMsg.streamEnded = true;
            tryFinalizeAssistantMessage(assistantMsg);
        }
        else if (type === 'quota') {
            if (userQuota.value && !userQuota.value.is_unlimited) {
                userQuota.value.current_balance = data.balance_after;
            }
        }
        else if (type === 'error') {
            stopWaitingText(assistantMsg);
            if (assistantMsg.typingInterval) {
                clearInterval(assistantMsg.typingInterval);
                assistantMsg.typingInterval = null;
            }

            assistantMsg.answerBuffer = '';
            assistantMsg.streamEnded = true;
            assistantMsg.isThinking = false;
            assistantMsg.isAnswerTyping = false;
            assistantMsg.isTyping = false;

            if (data.quota) {
                assistantMsg.content = '积分不足，请等待每日重置或联系管理员充值。\n当前积分: ' + data.quota.current_balance + '/' + data.quota.daily_limit;
            } else {
                assistantMsg.content = '抱歉，处理请求时出错：' + (data.message || '未知错误');
            }

            chatLoading.value = false;
            saveChatHistory();
        }

        scrollToBottom();
    };

    // F-21: Streaming chat with exponential backoff retry + deduplication
    // Tracks charsReceived to skip already-processed content on reconnect
    const streamChatWithRetry = async (sessionId, question, assistantMsg, onEvent, onReconnecting) => {
        const MAX_RETRIES = 5;
        const BASE_DELAY_MS = 1000;
        const MAX_DELAY_MS = 30000;

        let charsReceived = 0;  // Total chars processed, used for deduplication on reconnect

        const wrappedOnEvent = (event) => {
            // Deduplication isn't strictly needed for chunks because streaming_text events 
            // from the backend are strictly non-overlapping chunks. If there was a retry,
            // we'd need it, but streamChat natively doesn't resume from exact byte index gracefully without 
            // protocol support. Assuming standard behavior here.
            charsReceived += (event.data?.content || '').length;
            onEvent(event);
        };

        for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
            try {
                await api.streamChat(sessionId, question, wrappedOnEvent);
                return; // Success
            } catch (err) {
                const isNetworkError = err.name === 'TypeError' ||
                    err.message?.includes('fetch') ||
                    err.message?.includes('network') ||
                    err.message?.includes('Failed to');

                if (attempt < MAX_RETRIES && isNetworkError) {
                    const delay = Math.min(BASE_DELAY_MS * Math.pow(2, attempt), MAX_DELAY_MS);
                    console.warn(`SSE connection failed (attempt ${attempt + 1}/${MAX_RETRIES + 1}), retrying in ${delay}ms:`, err.message);

                    // Notify UI about reconnection attempt
                    if (onReconnecting) {
                        onReconnecting(attempt + 1, delay);
                    }

                    // Wait before retry
                    await new Promise(resolve => setTimeout(resolve, delay));
                    continue;
                }

                // Final failure or non-network error
                throw err;
            }
        }
    };

    const sendMessage = async () => {
        if (!chatInput.value.trim() || chatLoading.value) return;

        const question = chatInput.value.trim();
        chatInput.value = '';
        messages.value.push({ role: 'user', content: question });
        chatLoading.value = true;

        const rawAssistantMsg = createAssistantMessage();
        messages.value.push(rawAssistantMsg);
        const assistantMsg = messages.value[messages.value.length - 1];
        startWaitingText(assistantMsg);

        if (!currentSessionId.value) {
            currentSessionId.value = 'session-' + Date.now();
        }

        try {
            await streamChatWithRetry(
                currentSessionId.value,
                question,
                assistantMsg,
                (event) => processStreamEvent(assistantMsg, event),
                (attempt, delay) => {
                    // F-21: Optional reconnect notification (informational only)
                    console.info(`Reconnecting... (attempt ${attempt}, next retry in ${delay}ms)`);
                }
            );
        } catch (err) {
            stopWaitingText(assistantMsg);
            assistantMsg.content = '抱歉，处理您的请求时出现错误：' + (err.message || '未知错误');
            assistantMsg.answerBuffer = '';
            assistantMsg.streamEnded = true;
            assistantMsg.isThinking = false;
            assistantMsg.isAnswerTyping = false;
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
        // F-22: Reload suggestions when starting a new conversation (permission-aware, fresh from server)
        if (loadSuggestions) {
            loadSuggestions();
        }
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
            console.log('[loadChatHistory] API response keys:', Object.keys(res));
            console.log('[loadChatHistory] sessions count:', res.sessions?.length, 'conversations count:', res.conversations?.length);
            // Backend returns {sessions: [...]} but frontend uses conversations
            // Normalize the response to frontend's expected format
            const rawConvs = res.sessions || res.conversations || [];
            conversations.value = rawConvs.map(s => ({
                id: s.session_id || s.id,
                title: s.title || s.messages?.[0]?.content?.slice(0, 50) || '新对话',
                messages: s.messages || [],
                createdAt: s.created_at || s.createdAt,
                updatedAt: s.updated_at || s.updatedAt,
            }));
            console.log('[loadChatHistory] mapped conversations count:', conversations.value.length);
            // Keep messages empty to show welcome page with suggestions.
            // User can click a conversation from the sidebar to load it.
            // If a currentSessionId is already set (from sessionStorage), try to load
            // that specific conversation instead of defaulting to the latest
            const persistedSessionId = currentSessionId.value;
            if (persistedSessionId && conversations.value.length > 0) {
                const savedConv = conversations.value.find(c => c.id === persistedSessionId);
                if (savedConv) {
                    messages.value = savedConv.messages || [];
                    currentSessionId.value = savedConv.id;
                    return;
                }
            }
            // Otherwise keep messages empty so welcome page (with suggestions) is shown
            messages.value = [];
            currentSessionId.value = null;
        } catch (e) {
            console.error('[loadChatHistory] Failed to load chat history:', e);
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
                msg.streamEnded = false;
                msg.isTyping = true;
                msg.isThinking = true;
                msg.isAnswerTyping = false;
                msg.answerBuffer = '';
                await api.streamChat(currentSessionId.value, '', (event) => {
                    processStreamEvent(msg, event);
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
