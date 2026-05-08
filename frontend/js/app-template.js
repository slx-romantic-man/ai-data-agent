window.AppTemplate = `
        <div class="min-h-screen">
            <!-- Login Page -->
            <div v-if="!isLoggedIn" class="min-h-screen flex items-center justify-center p-4 bg-slate-50">
                <div class="bg-white rounded-xl shadow-card p-10 w-full max-w-md border border-zinc-200">
                    <div class="text-center mb-10">
                        <div class="w-14 h-14 bg-green-500 rounded-xl flex items-center justify-center mx-auto mb-6 shadow-lg shadow-green-200">
                            <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                            </svg>
                        </div>
                        <h1 class="text-2xl font-semibold tracking-tight text-zinc-950">AI智能体</h1>
                        <p class="text-zinc-500 mt-2 text-sm">智能数据分析平台</p>
                    </div>

                    <form @submit.prevent="handleLogin" class="space-y-6">
                        <div class="space-y-1.5">
                            <label class="block text-xs font-semibold text-zinc-900 uppercase tracking-wider">用户名</label>
                            <input v-model="loginForm.username" type="text" required
                                class="w-full px-3.5 py-2.5 bg-white border border-zinc-200 rounded-md text-sm transition-all-custom focus:ring-0 placeholder:text-zinc-400"
                                placeholder="请输入用户名">
                        </div>
                        <div class="space-y-1.5">
                            <label class="block text-xs font-semibold text-zinc-900 uppercase tracking-wider">密码</label>
                            <input v-model="loginForm.password" type="password" required
                                class="w-full px-3.5 py-2.5 bg-white border border-zinc-200 rounded-md text-sm transition-all-custom focus:ring-0 placeholder:text-zinc-400"
                                placeholder="请输入密码">
                        </div>
                        <div v-if="loginError" class="text-red-500 text-xs py-1 px-3 bg-red-50 rounded border border-red-100">{{ loginError }}</div>
                        <button type="submit" :disabled="loginLoading"
                            class="w-full py-2.5 bg-green-500 text-white rounded-md text-sm font-medium hover:bg-green-600 transition-all-custom disabled:opacity-50 disabled:cursor-not-allowed shadow-sm">
                            <span v-if="loginLoading" class="flex items-center justify-center space-x-2">
                                <div class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                <span>登录中...</span>
                            </span>
                            <span v-else>登 录</span>
                        </button>
                    </form>

                    <!-- CIA 统一认证登录 -->
                    <div v-if="ciaEnabled && ciaAuthMode !== 'local_only'" class="mt-6">
                        <div class="relative">
                            <div class="absolute inset-0 flex items-center">
                                <div class="w-full border-t border-zinc-200"></div>
                            </div>
                            <div class="relative flex justify-center text-xs">
                                <span class="px-3 bg-white text-zinc-400">或使用</span>
                            </div>
                        </div>
                        <button @click="handleCiaLogin" :disabled="ciaLoading"
                            class="mt-4 w-full py-2.5 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 transition-all-custom disabled:opacity-50 disabled:cursor-not-allowed shadow-sm flex items-center justify-center space-x-2">
                            <span v-if="ciaLoading" class="flex items-center justify-center space-x-2">
                                <div class="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                <span>CIA 登录中...</span>
                            </span>
                            <span v-else class="flex items-center space-x-2">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                                </svg>
                                <span>CIA 统一认证登录</span>
                            </span>
                        </button>
                        <div v-if="ciaError" class="mt-2 text-red-500 text-xs py-1 px-3 bg-red-50 rounded border border-red-100 text-center">{{ ciaError }}</div>
                    </div>

                    <div class="mt-8 pt-8 border-t border-zinc-100">
                        <p class="text-[11px] font-bold text-zinc-400 uppercase tracking-widest text-center mb-5">快速体验账号</p>
                        <div class="grid grid-cols-3 gap-3 text-xs">
                            <button @click="quickLogin('admin', 'admin123')" class="flex flex-col items-center p-3 border border-zinc-100 rounded-md hover:border-zinc-300 hover:bg-zinc-50 transition-all-custom">
                                <div class="font-semibold text-zinc-900">管理员</div>
                                <div class="text-[10px] text-zinc-400 font-mono mt-1">admin</div>
                            </button>
                            <button @click="quickLogin('manager1', 'manager123')" class="flex flex-col items-center p-3 border border-zinc-100 rounded-md hover:border-zinc-300 hover:bg-zinc-50 transition-all-custom">
                                <div class="font-semibold text-zinc-900">经理</div>
                                <div class="text-[10px] text-zinc-400 font-mono mt-1">manager1</div>
                            </button>
                            <button @click="quickLogin('user1', 'user123')" class="flex flex-col items-center p-3 border border-zinc-100 rounded-md hover:border-zinc-300 hover:bg-zinc-50 transition-all-custom">
                                <div class="font-semibold text-zinc-900">员工</div>
                                <div class="text-[10px] text-zinc-400 font-mono mt-1">user1</div>
                            </button>
                        </div>
                    </div>

                    <!-- Registration Section -->
                    <div class="mt-4">
                        <div v-if="showRegisterForm" class="p-6 bg-zinc-50 rounded-lg border border-zinc-100 mt-4 chat-bubble">
                            <h3 class="font-semibold text-zinc-900 mb-4 text-sm">注册新账号</h3>
                            <div class="space-y-4">
                                <div class="space-y-1">
                                    <input v-model="registerForm.login_id" type="text" required
                                        class="w-full px-3 py-2 border border-zinc-200 rounded-md text-sm focus:ring-0"
                                        placeholder="登录账号">
                                </div>
                                <div class="space-y-1">
                                    <input v-model="registerForm.username" type="text" required
                                        class="w-full px-3 py-2 border border-zinc-200 rounded-md text-sm focus:ring-0"
                                        placeholder="显示名称">
                                </div>
                                <div class="space-y-1">
                                    <input v-model="registerForm.password" type="password" required
                                        class="w-full px-3 py-2 border border-zinc-200 rounded-md text-sm focus:ring-0"
                                        placeholder="密码">
                                </div>
                                <div v-if="registerError" class="text-red-500 text-[10px]">{{ registerError }}</div>
                                <div class="flex space-x-3 pt-2">
                                    <button @click="handleRegister" :disabled="registerLoading"
                                        class="flex-1 py-1.5 bg-green-500 text-white rounded-md text-xs font-medium hover:bg-green-600 disabled:opacity-50 transition-all-custom">
                                        注册
                                    </button>
                                    <button @click="cancelRegister" class="flex-1 py-1.5 border border-zinc-200 text-zinc-600 rounded-md text-xs font-medium hover:bg-zinc-100 transition-all-custom">
                                        取消
                                    </button>
                                </div>
                            </div>
                        </div>
                        <button v-else @click="showRegisterForm = true"
                            class="w-full py-3 text-xs text-zinc-500 hover:text-zinc-950 font-medium transition-all-custom">
                            还没有账号？ <span class="text-zinc-950 underline underline-offset-4">即刻注册</span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Main App -->
            <div v-else class="flex h-screen">
                <!-- Sidebar -->
                <div class="w-60 bg-white border-r border-zinc-200 flex flex-col h-screen overflow-hidden shadow-[1px_0_0_0_rgba(0,0,0,0.02)]">
                    <div class="p-3">
                        <div class="flex items-center space-x-2">
                            <div class="w-7 h-7 bg-green-500 rounded-lg flex items-center justify-center shadow-sm">
                                <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                                </svg>
                            </div>
                            <div class="overflow-hidden flex-1">
                                <h1 class="font-bold text-zinc-950 text-[13px] tracking-tight">AI智能体</h1>
                            </div>
                        </div>
                    </div>

                    <!-- Navigation -->
                    <nav class="flex-1 px-2 space-y-0.5 overflow-y-auto">
                        <button @click="currentView = 'chat'"
                            :class="['w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all-custom', currentView === 'chat' ? 'bg-green-50 text-green-600' : 'text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700']">
                            <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                            </svg>
                            <span>智能对话</span>
                        </button>
                        <button @click="currentView = 'apis'"
                            :class="['w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all-custom', currentView === 'apis' ? 'bg-green-50 text-green-600' : 'text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700']">
                            <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                            </svg>
                            <span>查看API</span>
                        </button>
                        <button @click="currentView = 'history'"
                            :class="['w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all-custom', currentView === 'history' ? 'bg-green-50 text-green-600' : 'text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700']">
                            <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                            <span>历史记录</span>
                        </button>
                        <!-- Admin Panel -->
                        <button v-if="user && user.role === 'admin'" @click="currentView = 'admin'"
                            :class="['w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all-custom', currentView === 'admin' ? 'bg-green-50 text-green-600' : 'text-zinc-500 hover:bg-zinc-50 hover:text-zinc-700']">
                            <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                            </svg>
                            <span>管理后台</span>
                        </button>
                    </nav>

                    <!-- User Info -->
                    <div class="p-3 border-t border-zinc-100 bg-zinc-50/50">
                        <div class="flex items-center justify-between group">
                            <div class="flex items-center space-x-2 min-w-0">
                                <div class="w-7 h-7 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                                    <span class="text-white font-bold text-[10px]">{{ user?.username?.charAt(0) }}</span>
                                </div>
                                <div class="overflow-hidden min-w-0">
                                    <div class="text-[11px] font-bold text-zinc-900 truncate" :title="user?.username">{{ user?.username }}</div>
                                    <div class="text-[10px] text-zinc-400 font-medium">{{ getRoleName(user?.role) }}</div>
                                </div>
                            </div>
                            <button @click="handleLogout" class="p-1 text-zinc-400 hover:text-zinc-950 transition-all-custom rounded-md hover:bg-zinc-200/50 flex-shrink-0">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path>
                                </svg>
                            </button>
                        </div>
                        <!-- Quota Display -->
                        <div v-if="userQuota && !userQuota.is_unlimited" class="mt-4 p-3 bg-white border border-zinc-100 rounded-lg shadow-sm">
                            <div class="flex justify-between items-center text-[10px] mb-2 font-bold uppercase tracking-wider">
                                <span class="text-zinc-400">积分</span>
                                <span class="text-zinc-900">{{ userQuota.current_balance }} / {{ userQuota.daily_limit }}</span>
                            </div>
                            <div class="h-1 bg-zinc-100 rounded-full overflow-hidden">
                                <div class="h-full bg-green-500 rounded-full transition-all duration-500" :style="{ width: (userQuota.current_balance / userQuota.daily_limit * 100) + '%' }"></div>
                            </div>
                        </div>
                        <div v-else-if="userQuota && userQuota.is_unlimited" class="mt-4 p-2 bg-green-500 rounded-lg text-[10px] font-bold text-white text-center uppercase tracking-widest">
                            无限权限
                        </div>
                    </div>
                </div>

                <!-- Main Content -->
                <div class="flex-1 flex flex-col h-screen overflow-hidden">
                    <!-- Chat View -->
                    <div v-if="currentView === 'chat'" class="flex-1 flex flex-col min-h-0">
                        <!-- Chat Header -->
                        <div class="bg-white/80 backdrop-blur-md border-b border-zinc-200 px-8 py-4 flex-shrink-0 flex justify-between items-center z-10 sticky top-0">
                            <div class="flex items-center space-x-3">
                                <div class="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(34,197,94,0.5)]"></div>
                                <div>
                                    <h2 class="text-sm font-bold text-zinc-900 tracking-tight">智能数据分析</h2>
                                    <p class="text-[10px] text-zinc-400 font-medium uppercase tracking-widest">自然语言驱动数据洞察</p>
                                </div>
                            </div>
                            <button v-if="messages.length > 0" @click="startNewConversation"
                                class="px-4 py-1.5 bg-green-500 text-white rounded-md hover:bg-green-600 transition-all-custom flex items-center space-x-2 text-xs font-bold shadow-sm">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                                </svg>
                                <span>新对话</span>
                            </button>
                        </div>

                        <!-- Chat Messages -->
                        <div id="chatContainer" ref="chatContainer" class="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin bg-gray-50" style="min-height: 0;">
                            <!-- Welcome Message -->
                            <div v-if="messages.length === 0" class="max-w-2xl mx-auto py-24 text-center">
                                <div class="inline-flex items-center justify-center p-4 bg-green-50 rounded-2xl mb-8 shadow-inner">
                                    <svg class="w-10 h-10 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                                    </svg>
                                </div>
                                <h3 class="text-2xl font-bold text-zinc-950 mb-3 tracking-tight">你好，{{ user?.username }}</h3>
                                <p class="text-zinc-500 mb-10 text-sm max-w-sm mx-auto">你可以通过自然语言直接向我提问，我会自动整理并分析系统内的数据。</p>
                                <div class="flex flex-wrap justify-center gap-3">
                                    <button v-for="(q, qi) in sampleQuestions" :key="q" @click="askQuestion(q)"
                                        class="px-4 py-2 bg-white border border-zinc-200 rounded-full text-xs font-semibold text-zinc-600 hover:border-green-400 hover:text-green-600 transition-all-custom shadow-sm flex items-center space-x-2">
                                        <span class="w-1.5 h-1.5 rounded-full flex-shrink-0"
                                            :class="['bg-green-500','bg-blue-500','bg-purple-500','bg-orange-500','bg-pink-500','bg-cyan-500'][qi % 6]"></span>
                                        <span>{{ q }}</span>
                                    </button>
                                </div>
                            </div>

                            <!-- Messages -->
                            <div v-for="(msg, idx) in messages" :key="idx" class="chat-bubble">
                                <!-- User Message -->
                                <div v-if="msg.role === 'user'" class="flex justify-end mb-4">
                                    <div class="max-w-[70%] bg-green-500 text-white rounded-2xl px-5 py-3.5 text-sm font-medium shadow-md">
                                        {{ msg.content }}
                                    </div>
                                </div>

                                <!-- Assistant Message -->
                                <div v-else class="flex justify-start mb-6">
                                    <div class="max-w-[85%] bg-white rounded-2xl px-6 py-4 shadow-card border border-zinc-100" :class="{'hide-md-table': msg.data && msg.data.rows && msg.data.rows.length > 0}">
                                        <!-- Thinking Process (Collapsible) -->
                                        <div v-if="msg.thinking || (msg.reasoningLog && msg.reasoningLog.steps && msg.reasoningLog.steps.length > 0)" class="mb-4 border border-zinc-100 rounded-lg overflow-hidden bg-zinc-50/80 backdrop-blur-sm">
                                            <button @click="msg.showThinking = !msg.showThinking"
                                                class="w-full px-4 py-2.5 flex items-center justify-between text-left hover:bg-zinc-100 transition-all-custom">
                                                <div class="flex items-center space-x-2.5">
                                                    <div class="w-5 h-5 bg-white border border-zinc-200 rounded flex items-center justify-center shadow-xs">
                                                        <svg class="w-3.5 h-3.5 text-zinc-950" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                                                        </svg>
                                                    </div>
                                                    <span class="text-xs font-bold text-zinc-900 uppercase tracking-widest">推理过程</span>
                                                    <span v-if="msg.reasoningLog" class="text-[10px] text-zinc-400 font-mono">({{ msg.reasoningLog.total_steps || 0 }} 步)</span>
                                                    <span v-if="msg.isThinking" class="text-[10px] text-zinc-400 animate-pulse italic">思考中...</span>
                                                    <span v-else-if="msg.isAnswerTyping" class="text-[10px] text-zinc-400 animate-pulse italic">回答中...</span>
                                                </div>
                                                <svg :class="['w-3.5 h-3.5 text-zinc-400 transition-transform duration-300', (msg.showThinking || msg.isThinking) ? 'rotate-180' : '']" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                                </svg>
                                            </button>
                                            <div v-if="msg.showThinking || msg.isThinking" class="px-3 py-2 bg-purple-50 border-t border-gray-200">
                                                <!-- ReAct Steps -->
                                                <div v-if="msg.reasoningLog && msg.reasoningLog.steps && msg.reasoningLog.steps.length > 0" class="space-y-3">
                                                    <div v-for="(step, stepIdx) in msg.reasoningLog.steps" :key="stepIdx" class="border-l-2 border-purple-300 pl-3">
                                                        <div class="text-xs font-medium text-purple-700 mb-1">步骤 {{ step.step_number || stepIdx + 1 }}</div>
                                                        <!-- Thought -->
                                                        <div v-show="step.thought" class="mb-2">
                                                            <div class="flex items-center space-x-1 text-xs font-medium text-blue-600">
                                                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                                                                </svg>
                                                                <span>思考：</span>
                                                            </div>
                                                            <div class="text-xs text-gray-600 bg-blue-50 p-2 rounded mt-1 thought-typing-target whitespace-pre-wrap">{{ step.thought }}<span v-if="msg.isThinking && step === msg.reasoningLog.steps[msg.reasoningLog.steps.length - 1] && !step.action && !step.observation" class="typewriter-cursor"></span></div>
                                                        </div>
                                                        <!-- Action -->
                                                        <div v-if="step.action" class="mb-2">
                                                            <div class="flex items-center space-x-1 text-xs font-medium text-green-600">
                                                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                                                </svg>
                                                                <span>动作：</span>
                                                            </div>
                                                            <div class="text-xs text-gray-600 bg-green-50 p-2 rounded mt-1 font-mono">
                                                                {{ step.action.tool || step.action.name || 'unknown' }}
                                                                <span v-if="step.action.parameters" class="text-gray-400">{{ JSON.stringify(step.action.parameters) }}</span>
                                                            </div>
                                                        </div>
                                                        <!-- Observation -->
                                                        <div v-if="step.observation" class="mb-2">
                                                            <div class="flex items-center space-x-1 text-xs font-medium text-orange-600">
                                                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                                                </svg>
                                                                <span>观察：</span>
                                                            </div>
                                                            <div class="text-xs text-gray-600 bg-orange-50 p-2 rounded mt-1">{{ step.observation }}</div>
                                                        </div>
                                                    </div>
                                                    <!-- Final Answer indicator -->
                                                    <div v-if="msg.reasoningLog.is_complete" class="text-xs text-green-600 font-medium flex items-center space-x-1">
                                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                                        </svg>
                                                        <span>推理完成</span>
                                                    </div>
                                                </div>
                                                <!-- Legacy thinking display for backward compatibility -->
                                                <div v-else-if="msg.thinking" class="text-xs space-y-2">
                                                    <div v-if="msg.thinking?.intent">
                                                        <span class="font-medium text-purple-700">意图识别:</span>
                                                        <span class="text-gray-600 ml-1">{{ msg.thinking.intent }}</span>
                                                    </div>
                                                    <div v-if="msg.thinking?.api">
                                                        <span class="font-medium text-purple-700">选择API:</span>
                                                        <span class="text-gray-600 ml-1">{{ msg.thinking.api }}</span>
                                                    </div>
                                                    <div v-if="msg.thinking?.endpoint">
                                                        <span class="font-medium text-purple-700">调用端点:</span>
                                                        <span class="text-gray-600 ml-1">{{ msg.thinking.endpoint }}</span>
                                                    </div>
                                                    <div v-if="msg.thinking?.entities">
                                                        <span class="font-medium text-purple-700">提取实体:</span>
                                                        <span class="text-gray-600 ml-1">{{ JSON.stringify(msg.thinking.entities) }}</span>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <div class="text-gray-800 markdown-content">
                                            <div v-show="msg.content" class="markdown-body" v-html="renderSafeMarkdown(msg.content)"></div>
                                            <div v-if="!msg.content && msg.isThinking && msg.waitingText" class="text-sm text-zinc-400 animate-pulse py-2 flex items-center space-x-2">
                                                <span>{{ msg.waitingEmoji }}</span>
                                                <span>{{ msg.waitingText }}</span>
                                            </div>
                                            <span v-if="msg.isAnswerTyping" class="typewriter-cursor mt-1"></span>
                                        </div>

                                        <!-- Data Table -->
                                        <div v-if="msg.data && msg.data.rows && msg.data.rows.length > 0" class="mt-4">
                                            <div class="overflow-x-auto rounded-lg border border-gray-200">
                                                <table class="min-w-full divide-y divide-gray-200">
                                                    <thead class="bg-gray-50">
                                                        <tr>
                                                            <th v-for="col in msg.data.columns" :key="col"
                                                                class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                                                {{ col }}
                                                            </th>
                                                        </tr>
                                                    </thead>
                                                    <tbody class="bg-white divide-y divide-gray-200">
                                                        <tr v-for="(row, rowIdx) in msg.data.rows.slice(0, 10)" :key="rowIdx">
                                                            <td v-for="col in msg.data.columns" :key="col" class="px-4 py-3 text-sm text-gray-600">
                                                                {{ row[col] }}
                                                            </td>
                                                        </tr>
                                                    </tbody>
                                                </table>
                                            </div>
                                            <div v-if="msg.data.rows.length > 10" class="text-xs text-gray-500 mt-2">
                                                共 {{ msg.data.rows.length }} 条数据，展示前 10 条，导出可获取完整数据
                                            </div>
                                        </div>

                                        <!-- SQL -->
                                        <div v-if="msg.sql" class="mt-4">
                                            <div class="text-xs text-gray-500 mb-1">API调用信息:</div>
                                            <pre class="text-xs bg-gray-50 p-3 rounded-lg text-gray-700 overflow-x-auto">{{ msg.sql }}</pre>
                                        </div>

                                        <!-- Approval Card -->
                                        <div v-if="msg.approval" class="mt-4 border border-yellow-300 bg-yellow-50 rounded-lg p-4">
                                            <div class="flex items-center space-x-2 mb-3">
                                                <svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                                                </svg>
                                                <span class="font-semibold text-yellow-800">需要人工审批</span>
                                            </div>
                                            <div class="text-sm text-gray-700 mb-3">
                                                <div class="font-medium mb-1">执行计划:</div>
                                                <ul class="list-disc list-inside space-y-1">
                                                    <li v-for="(step, idx) in msg.approval.plan" :key="idx">{{ step }}</li>
                                                </ul>
                                            </div>
                                            <div v-if="msg.approval.status === 'pending'" class="flex space-x-3">
                                                <button @click="handleApproval(msg, 'approve')"
                                                    class="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition text-sm font-medium">
                                                    批准执行
                                                </button>
                                                <button @click="handleApproval(msg, 'reject')"
                                                    class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition text-sm font-medium">
                                                    拒绝执行
                                                </button>
                                            </div>
                                            <div v-else-if="msg.approval.status === 'approved'" class="text-green-600 font-medium">
                                                ✓ 已批准
                                            </div>
                                            <div v-else-if="msg.approval.status === 'rejected'" class="text-red-600 font-medium">
                                                ✗ 已拒绝
                                            </div>
                                            <div v-else-if="msg.approval.status === 'processing'" class="text-blue-600 font-medium">
                                                处理中...
                                            </div>
                                        </div>

                                        <!-- Export Button -->
                                        <div v-if="hasExportableData(msg)" class="mt-4 flex items-center space-x-4">
                                            <button @click="exportToExcel(msg)"
                                                class="text-sm text-blue-500 hover:text-blue-600 flex items-center space-x-1 px-3 py-1.5 bg-blue-50 rounded-lg hover:bg-blue-100 transition">
                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                                </svg>
                                                <span>导出为Excel</span>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Chat Input -->
                        <div class="bg-white border-t border-zinc-200 p-6 flex-shrink-0">
                            <div class="max-w-4xl mx-auto flex space-x-4">
                                <div class="relative flex-1 group">
                                    <input v-model="chatInput" type="text"
                                        @keyup.enter="sendMessage"
                                        class="w-full px-5 py-3.5 bg-zinc-50 border border-zinc-200 rounded-xl transition-all-custom focus:bg-white focus:border-zinc-950 shadow-inner placeholder:text-zinc-400 text-sm"
                                        :placeholder="sampleQuestions.length > 0 ? '例如：' + sampleQuestions[0] : '请输入您的问题'"
                                        :disabled="chatLoading">
                                    <div class="absolute right-4 top-1/2 -translate-y-1/2 flex items-center space-x-2">
                                        <span class="text-[10px] text-zinc-400 font-bold hidden group-focus-within:block tracking-widest">按回车发送</span>
                                    </div>
                                </div>
                                <button @click="sendMessage" :disabled="chatLoading || !chatInput.trim()"
                                    class="px-8 py-3.5 bg-green-500 text-white rounded-xl font-bold text-sm hover:bg-green-600 transition-all-custom disabled:opacity-30 disabled:grayscale shadow-sm flex items-center space-x-2">
                                    <svg v-if="!chatLoading" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                    </svg>
                                    <div v-else class="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                                    <span>发送</span>
                                </button>
                            </div>
                            <p class="text-[10px] text-zinc-400 text-center mt-3 font-medium uppercase tracking-widest">由先进AI数据逻辑驱动</p>
                        </div>
                    </div>

                    <!-- API Management View -->
                    <div v-else-if="currentView === 'apis'" class="flex-1 overflow-y-auto p-10 bg-slate-50/50">
                        <div class="mb-10 flex justify-between items-end">
                            <div>
                                <h2 class="text-2xl font-bold text-zinc-950 tracking-tight">API管理</h2>
                                <p class="text-sm text-zinc-500 mt-1">{{ user?.role === 'admin' ? '配置和监控您的数据源' : '查看您有权限访问的API' }}</p>
                            </div>
                            <div v-if="user && user.role === 'admin'" class="flex space-x-3">
                                <button @click="showAddCategoryModal = true"
                                    class="px-5 py-2.5 bg-white border border-zinc-200 text-zinc-700 rounded-md text-sm font-bold hover:bg-zinc-50 transition-all-custom shadow-xs flex items-center space-x-2">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                                    </svg>
                                    <span>添加新类</span>
                                </button>
                                <button @click="showAddApiModal = true"
                                    class="px-5 py-2.5 bg-green-500 text-white rounded-md text-sm font-bold hover:bg-green-600 transition-all-custom shadow-sm flex items-center space-x-2">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                                    </svg>
                                    <span>添加新API</span>
                                </button>
                                <button @click="toggleDeleteMode"
                                    :class="['px-5 py-2.5 rounded-md text-sm font-bold transition-all-custom border flex items-center space-x-2', deleteMode ? 'bg-red-50 border-red-200 text-red-600 shadow-inner' : 'bg-white border-zinc-200 text-zinc-600 hover:bg-zinc-50 shadow-xs']">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-4v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                    </svg>
                                    <span>{{ deleteMode ? '退出删除模式' : '批量删除' }}</span>
                                </button>
                            </div>
                        </div>

                        <div v-if="apisLoading" class="text-center py-20">
                            <div class="animate-spin w-10 h-10 border-4 border-zinc-900 border-t-transparent rounded-full mx-auto"></div>
                            <p class="text-zinc-500 mt-4 text-xs font-bold uppercase tracking-widest">加载中...</p>
                        </div>

                        <div v-else-if="apiList.length === 0" class="bg-white border border-zinc-200 border-dashed rounded-xl p-20 text-center">
                            <div class="w-16 h-16 bg-zinc-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-zinc-100">
                                <svg class="w-8 h-8 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
                                </svg>
                            </div>
                            <h4 class="text-zinc-900 font-bold">暂无 API</h4>
                            <p class="text-zinc-500 text-sm mt-1">{{ user && user.role === 'admin' ? '点击右上角按钮添加您的第一个数据源' : '请联系管理员授予您权限' }}</p>
                        </div>

                        <div v-else class="space-y-6">
                            <!-- Categorized APIs -->
                            <div v-for="category in apiCategoriesWithApis" :key="category.id" class="bg-white rounded-xl border border-zinc-200 overflow-hidden shadow-sm">
                                <div @click="toggleCategory(category.id)"
                                     class="flex justify-between items-center p-4 bg-zinc-50 border-b border-zinc-200 cursor-pointer hover:bg-zinc-100 transition-colors">
                                    <div class="flex items-center space-x-3">
                                        <svg :class="{'rotate-90': expandedCategories.has(category.id)}"
                                             class="w-5 h-5 text-zinc-400 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                        </svg>
                                        <div>
                                            <h3 class="font-bold text-zinc-900">{{ category.name }}</h3>
                                            <p v-if="category.description" class="text-xs text-zinc-500 mt-0.5">{{ category.description }}</p>
                                        </div>
                                    </div>
                                    <span class="bg-zinc-200 text-zinc-700 text-xs font-bold px-2 py-1 rounded-full">
                                        {{ category.apis.length }} 个API
                                    </span>
                                </div>

                                <div v-show="expandedCategories.has(category.id)" class="p-5 bg-white">
                                    <div v-if="category.apis.length === 0" class="text-center py-6 text-zinc-500 text-sm">
                                        此分类下暂无API
                                    </div>
                                    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                                        <div v-for="api in category.apis" :key="api.id"
                                            class="group bg-white rounded-xl border border-zinc-200 p-5 hover:shadow-card-hover hover:border-zinc-300 transition-all-custom relative flex flex-col">
                                            <!-- Delete Button (Admin Only) -->
                                            <button v-if="deleteMode && user && user.role === 'admin' && !api.is_system" @click="confirmDeleteApi(api)"
                                                class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-all-custom shadow-md z-20">
                                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                                </svg>
                                            </button>

                                            <div class="w-10 h-10 bg-zinc-50 rounded-lg flex items-center justify-center border border-zinc-100 group-hover:bg-green-500 group-hover:text-white transition-all-custom mb-4">
                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                                                </svg>
                                            </div>
                                            <h3 class="font-bold text-zinc-950 mb-1 tracking-tight truncate" :title="api.name">{{ api.name }}</h3>
                                            <p class="text-zinc-500 text-xs line-clamp-2 h-8 leading-relaxed mb-6">{{ api.description || '暂无描述' }}</p>

                                            <div class="flex items-center justify-between pt-4 border-t border-zinc-50 mt-auto">
                                                <button @click="viewApiDetail(api)" class="text-xs font-bold text-zinc-900 hover:text-zinc-500 transition-all-custom flex items-center space-x-1">
                                                    <span>详情</span>
                                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                                    </svg>
                                                </button>
                                                <div v-if="user && user.role === 'admin'" class="flex space-x-2">
                                                    <button @click.stop="moveApiToUncategorized(api.id)" class="px-2 py-1 text-[10px] font-bold text-amber-700 bg-amber-50 border border-amber-200 rounded hover:bg-amber-100 transition-all-custom" title="移出当前分类">
                                                        移出分类
                                                    </button>
                                                    <button @click="editApi(api)" class="p-1.5 text-zinc-400 hover:text-zinc-950 transition-all-custom rounded hover:bg-zinc-100" title="编辑">
                                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                                        </svg>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Uncategorized APIs -->
                            <div v-if="uncategorizedApis.length > 0" class="bg-white rounded-xl border border-zinc-200 overflow-hidden shadow-sm">
                                <div class="flex justify-between items-center p-4 bg-zinc-50 border-b border-zinc-200">
                                    <div class="flex items-center space-x-3">
                                        <div class="w-5 h-5 flex items-center justify-center">
                                            <svg class="w-5 h-5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
                                            </svg>
                                        </div>
                                        <div>
                                            <h3 class="font-bold text-zinc-900">未分类 API</h3>
                                            <p class="text-xs text-zinc-500 mt-0.5">尚未归入任何类别的零散API</p>
                                        </div>
                                    </div>
                                    <span class="bg-zinc-200 text-zinc-700 text-xs font-bold px-2 py-1 rounded-full">
                                        {{ uncategorizedApis.length }} 个API
                                    </span>
                                </div>
                                <div class="p-5 bg-white">
                                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                                        <div v-for="api in uncategorizedApis" :key="api.id"
                                            class="group bg-white rounded-xl border border-zinc-200 p-5 hover:shadow-card-hover hover:border-zinc-300 transition-all-custom relative flex flex-col">
                                            <!-- Delete Button (Admin Only) -->
                                            <button v-if="deleteMode && user && user.role === 'admin' && !api.is_system" @click="confirmDeleteApi(api)"
                                                class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-all-custom shadow-md z-20">
                                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                                </svg>
                                            </button>

                                            <div class="w-10 h-10 bg-zinc-50 rounded-lg flex items-center justify-center border border-zinc-100 group-hover:bg-green-500 group-hover:text-white transition-all-custom mb-4">
                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                                                </svg>
                                            </div>
                                            <h3 class="font-bold text-zinc-950 mb-1 tracking-tight truncate" :title="api.name">{{ api.name }}</h3>
                                            <p class="text-zinc-500 text-xs line-clamp-2 h-8 leading-relaxed mb-6">{{ api.description || '暂无描述' }}</p>

                                            <div class="flex items-center justify-between pt-4 border-t border-zinc-50 mt-auto">
                                                <button @click="viewApiDetail(api)" class="text-xs font-bold text-zinc-900 hover:text-zinc-500 transition-all-custom flex items-center space-x-1">
                                                    <span>详情</span>
                                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                                    </svg>
                                                </button>
                                                <div v-if="user && user.role === 'admin'" class="flex items-center space-x-2">
                                                    <select v-model="categorySelectionByApi[api.id]" @click.stop class="px-2 py-1 text-[10px] border border-zinc-200 rounded bg-white text-zinc-700 focus:outline-none focus:ring-1 focus:ring-zinc-400">
                                                        <option value="">选择分类</option>
                                                        <option v-for="cat in availableCategories" :key="cat.id" :value="cat.id">{{ cat.name }}</option>
                                                    </select>
                                                    <button @click.stop="moveApiToCategory(api.id)" class="px-2 py-1 text-[10px] font-bold text-blue-700 bg-blue-50 border border-blue-200 rounded hover:bg-blue-100 transition-all-custom" title="加入选中的分类">
                                                        加入分类
                                                    </button>
                                                    <button @click="editApi(api)" class="p-1.5 text-zinc-400 hover:text-zinc-950 transition-all-custom rounded hover:bg-zinc-100" title="编辑">
                                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                                        </svg>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Add Category Modal -->
                        <div v-if="showAddCategoryModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="showAddCategoryModal = false">
                            <div class="bg-white rounded-lg shadow-xl w-full max-w-md overflow-hidden">
                                <div class="p-4 border-b border-gray-200 flex justify-between items-center">
                                    <h3 class="text-lg font-semibold text-gray-800">添加新类</h3>
                                    <button @click="showAddCategoryModal = false" class="text-gray-400 hover:text-gray-600">
                                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                        </svg>
                                    </button>
                                </div>
                                <div class="p-4 space-y-4">
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700 mb-1">类名 <span class="text-red-500">*</span></label>
                                        <input v-model="newCategoryForm.name" type="text"
                                            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            placeholder="例如：天气类">
                                    </div>
                                    <div>
                                        <label class="block text-sm font-medium text-gray-700 mb-1">基本描述</label>
                                        <textarea v-model="newCategoryForm.description" rows="3"
                                            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            placeholder="简要描述该类用途"></textarea>
                                    </div>
                                    <div class="flex justify-end space-x-2 pt-2">
                                        <button @click="showAddCategoryModal = false" class="px-4 py-2 border border-zinc-200 text-zinc-600 rounded-md text-sm font-medium hover:bg-zinc-50 transition-all-custom">
                                            取消
                                        </button>
                                        <button @click="createCategoryFromApisView" class="px-4 py-2 bg-green-500 text-white rounded-md text-sm font-medium hover:bg-green-600 transition-all-custom">
                                            创建
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- API Detail Modal -->
                        <div v-if="showApiDetailModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="showApiDetailModal = false">
                            <div class="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] overflow-hidden">
                                <div class="p-4 border-b border-gray-200 flex justify-between items-center">
                                    <h3 class="font-semibold text-gray-800">API详情: {{ selectedApi?.name }}</h3>
                                    <button @click="showApiDetailModal = false" class="text-gray-400 hover:text-gray-600">
                                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                        </svg>
                                    </button>
                                </div>
                                <div class="p-4 overflow-auto max-h-[60vh]">
                                    <div class="space-y-4">
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">API ID</label>
                                            <div class="mt-1 text-gray-900">{{ selectedApi?.id }}</div>
                                        </div>
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">名称</label>
                                            <div class="mt-1 text-gray-900">{{ selectedApi?.name }}</div>
                                        </div>
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">描述</label>
                                            <div class="mt-1 text-gray-900">{{ selectedApi?.description || '暂无描述' }}</div>
                                        </div>
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">基础地址</label>
                                            <div class="mt-1 text-gray-900 font-mono text-sm bg-gray-50 p-2 rounded">{{ selectedApi?.base_url }}</div>
                                        </div>
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700">认证类型</label>
                                            <div class="mt-1 text-gray-900">{{ selectedApi?.auth?.type || 'none' }}</div>
                                        </div>
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700 mb-2">端点列表</label>
                                            <div class="space-y-2">
                                                <div v-for="(endpoint, key) in selectedApi?.endpoints" :key="key"
                                                    class="bg-gray-50 p-3 rounded">
                                                    <div class="font-medium text-gray-800">{{ key }}</div>
                                                    <div class="text-sm text-gray-600">{{ endpoint.path }} ({{ endpoint.method }})</div>
                                                    <div class="text-xs text-gray-500">{{ endpoint.description }}</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Add/Edit API Modal - 类似阿里云MCP服务界面 -->
                        <div v-if="showAddApiModal || showEditApiModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="closeApiModal">
                            <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden">
                                <!-- Header -->
                                <div class="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                                    <h3 class="text-lg font-semibold text-gray-800">{{ showEditApiModal ? '修改API服务' : '创建API服务' }}</h3>
                                    <button @click="closeApiModal" class="text-gray-400 hover:text-gray-600">
                                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                        </svg>
                                    </button>
                                </div>

                                <div class="p-6 overflow-auto max-h-[calc(90vh-80px)]">
                                    <!-- 基本信息 Section -->
                                    <div class="mb-8">
                                        <h4 class="text-md font-semibold text-gray-700 mb-4 pb-2 border-b border-gray-200">基本信息</h4>
                                        <div class="grid grid-cols-2 gap-4">
                                            <div>
                                                <label class="block text-sm font-medium text-gray-700 mb-1">
                                                    服务名称 <span class="text-red-500">*</span>
                                                </label>
                                                <input v-model="apiForm.name" type="text" required
                                                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                    placeholder="例如: 库存API">
                                            </div>
                                            <div>
                                                <label class="block text-sm font-medium text-gray-700 mb-1">
                                                    服务ID <span class="text-red-500">*</span>
                                                    <span class="text-xs text-gray-400 font-normal ml-1">(唯一标识，创建后不可修改)</span>
                                                </label>
                                                <input v-model="apiForm.id" type="text" required :disabled="showEditApiModal"
                                                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100"
                                                    placeholder="例如: inventory（仅小写字母、数字、下划线）">
                                            </div>
                                        </div>
                                        <div class="mt-4">
                                            <label class="block text-sm font-medium text-gray-700 mb-1">服务描述</label>
                                            <textarea v-model="apiForm.description" rows="2"
                                                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                placeholder="描述此API的功能和用途"></textarea>
                                        </div>
                                        <div class="mt-4">
                                            <label class="block text-sm font-medium text-gray-700 mb-1">
                                                Base URL <span class="text-red-500">*</span>
                                                <span class="text-xs text-gray-400 font-normal ml-1">(API的基础地址)</span>
                                            </label>
                                            <input v-model="apiForm.base_url" type="text" required
                                                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                placeholder="例如: https://api.example.com">
                                        </div>
                                        <div class="mt-4 grid grid-cols-2 gap-4">
                                            <div>
                                                <label class="block text-sm font-medium text-gray-700 mb-1">
                                                    超时时间（秒）
                                                </label>
                                                <input v-model.number="apiForm.timeout" type="number" min="1" max="300"
                                                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                    placeholder="30">
                                                <p class="text-xs text-gray-500 mt-1">API请求超时时间，默认30秒</p>
                                            </div>
                                            <div>
                                                <label class="block text-sm font-medium text-gray-700 mb-1">
                                                    重试次数
                                                </label>
                                                <input v-model.number="apiForm.retry_count" type="number" min="0" max="10"
                                                    class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                    placeholder="3">
                                                <p class="text-xs text-gray-500 mt-1">请求失败后的重试次数，默认3次</p>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- 认证配置 Section -->
                                    <div class="mb-8">
                                        <h4 class="text-md font-semibold text-gray-700 mb-4 pb-2 border-b border-gray-200">认证配置</h4>
                                        <div>
                                            <label class="block text-sm font-medium text-gray-700 mb-2">认证类型</label>
                                            <div class="grid grid-cols-5 gap-2">
                                                <button type="button" @click="apiForm.auth_type = 'none'"
                                                    :class="['px-4 py-2 rounded-lg border text-sm transition', apiForm.auth_type === 'none' ? 'bg-blue-50 border-blue-500 text-blue-700' : 'border-gray-300 text-gray-600 hover:border-gray-400']">
                                                    无认证
                                                </button>
                                                <button type="button" @click="apiForm.auth_type = 'api_key'"
                                                    :class="['px-4 py-2 rounded-lg border text-sm transition', apiForm.auth_type === 'api_key' ? 'bg-blue-50 border-blue-500 text-blue-700' : 'border-gray-300 text-gray-600 hover:border-gray-400']">
                                                    API Key
                                                </button>
                                                <button type="button" @click="apiForm.auth_type = 'bearer'"
                                                    :class="['px-4 py-2 rounded-lg border text-sm transition', apiForm.auth_type === 'bearer' ? 'bg-blue-50 border-blue-500 text-blue-700' : 'border-gray-300 text-gray-600 hover:border-gray-400']">
                                                    Bearer Token
                                                </button>
                                                <button type="button" @click="apiForm.auth_type = 'basic'"
                                                    :class="['px-4 py-2 rounded-lg border text-sm transition', apiForm.auth_type === 'basic' ? 'bg-blue-50 border-blue-500 text-blue-700' : 'border-gray-300 text-gray-600 hover:border-gray-400']">
                                                    Basic Auth
                                                </button>
                                                <button type="button" @click="apiForm.auth_type = 'custom'"
                                                    :class="['px-4 py-2 rounded-lg border text-sm transition', apiForm.auth_type === 'custom' ? 'bg-blue-50 border-blue-500 text-blue-700' : 'border-gray-300 text-gray-600 hover:border-gray-400']">
                                                    自定义
                                                </button>
                                            </div>
                                        </div>

                                        <!-- API Key 配置 -->
                                        <div v-if="apiForm.auth_type === 'api_key'" class="mt-4 p-4 bg-gray-50 rounded-lg">
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">Header名称</label>
                                                    <input v-model="apiForm.api_key_header" type="text"
                                                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                        placeholder="X-API-Key">
                                                    <p class="text-xs text-gray-500 mt-1">API Key将放在此请求头中发送</p>
                                                </div>
                                                <div>
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">API Key值</label>
                                                    <input v-model="apiForm.api_key_value" type="password"
                                                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                        placeholder="your-api-key">
                                                </div>
                                            </div>
                                        </div>

                                        <!-- Bearer Token 配置 -->
                                        <div v-if="apiForm.auth_type === 'bearer'" class="mt-4 p-4 bg-gray-50 rounded-lg">
                                            <label class="block text-sm font-medium text-gray-700 mb-1">Bearer Token</label>
                                            <input v-model="apiForm.bearer_token" type="password"
                                                class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                placeholder="your-bearer-token">
                                            <p class="text-xs text-gray-500 mt-1">将自动添加 Authorization: Bearer {token} 请求头</p>
                                        </div>

                                        <!-- Basic Auth 配置 -->
                                        <div v-if="apiForm.auth_type === 'basic'" class="mt-4 p-4 bg-gray-50 rounded-lg">
                                            <div class="grid grid-cols-2 gap-4">
                                                <div>
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
                                                    <input v-model="apiForm.username" type="text"
                                                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                        placeholder="username">
                                                </div>
                                                <div>
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
                                                    <input v-model="apiForm.password" type="password"
                                                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                        placeholder="password">
                                                </div>
                                            </div>
                                        </div>

                                        <!-- 自定义Headers 配置 -->
                                        <div v-if="apiForm.auth_type === 'custom'" class="mt-4 p-4 bg-gray-50 rounded-lg">
                                            <div class="flex justify-between items-center mb-2">
                                                <label class="block text-sm font-medium text-gray-700">自定义Headers</label>
                                                <button type="button" @click="addCustomHeader"
                                                    class="text-sm text-blue-600 hover:text-blue-700">
                                                    + 添加Header
                                                </button>
                                            </div>
                                            <div v-for="(header, index) in apiForm.custom_headers" :key="index" class="flex gap-2 mb-2">
                                                <input v-model="header.key" type="text"
                                                    class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                    placeholder="Header名称">
                                                <input v-model="header.value" type="text"
                                                    class="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                    placeholder="Header值">
                                                <button type="button" @click="removeCustomHeader(index)"
                                                    class="px-2 py-2 text-red-500 hover:text-red-700">
                                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                                    </svg>
                                                </button>
                                            </div>
                                            <div v-if="apiForm.custom_headers.length === 0" class="text-sm text-gray-500">
                                                暂无自定义Headers，点击上方按钮添加
                                            </div>
                                        </div>
                                    </div>

                                    <!-- 工具列表(端点) Section -->
                                    <div class="mb-6">
                                        <div class="flex justify-between items-center mb-4 pb-2 border-b border-gray-200">
                                            <h4 class="text-md font-semibold text-gray-700">工具列表 <span class="text-sm text-gray-500 font-normal">(端点配置)</span></h4>
                                            <button type="button" @click="addEndpoint"
                                                class="px-3 py-1.5 bg-blue-500 text-white rounded-lg text-sm hover:bg-blue-600 transition flex items-center space-x-1">
                                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                                                </svg>
                                                <span>添加工具</span>
                                            </button>
                                        </div>

                                        <div v-if="apiForm.endpoints.length === 0" class="text-center py-8 bg-gray-50 rounded-lg">
                                            <svg class="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                                            </svg>
                                            <p class="text-gray-500">暂无工具配置，点击"添加工具"按钮创建</p>
                                        </div>

                                        <div v-else class="space-y-4">
                                            <div v-for="(endpoint, epIndex) in apiForm.endpoints" :key="epIndex"
                                                class="border border-gray-200 rounded-lg p-4 bg-gray-50">
                                                <div class="flex justify-between items-center mb-4">
                                                    <span class="text-sm font-medium text-gray-700">工具 {{ epIndex + 1 }}</span>
                                                    <button type="button" @click="removeEndpoint(epIndex)"
                                                        class="text-red-500 hover:text-red-700 text-sm">
                                                        删除
                                                    </button>
                                                </div>

                                                <div class="grid grid-cols-3 gap-4 mb-4">
                                                    <div>
                                                        <label class="block text-sm font-medium text-gray-700 mb-1">
                                                            工具名称 <span class="text-red-500">*</span>
                                                        </label>
                                                        <input v-model="endpoint.name" type="text"
                                                            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                            placeholder="例如: query">
                                                        <p class="text-xs text-gray-500 mt-1">调用时使用的端点名</p>
                                                    </div>
                                                    <div>
                                                        <label class="block text-sm font-medium text-gray-700 mb-1">
                                                            工具路径 <span class="text-red-500">*</span>
                                                        </label>
                                                        <input v-model="endpoint.path" type="text"
                                                            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                            placeholder="例如: /api/query">
                                                        <p class="text-xs text-gray-500 mt-1">相对路径，拼接到Base URL</p>
                                                    </div>
                                                    <div>
                                                        <label class="block text-sm font-medium text-gray-700 mb-1">请求方法</label>
                                                        <select v-model="endpoint.method"
                                                            class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                                                            <option value="GET">GET</option>
                                                            <option value="POST">POST</option>
                                                            <option value="PUT">PUT</option>
                                                            <option value="DELETE">DELETE</option>
                                                            <option value="PATCH">PATCH</option>
                                                        </select>
                                                    </div>
                                                </div>

                                                <div class="mb-4">
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">工具描述</label>
                                                    <input v-model="endpoint.description" type="text"
                                                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                        placeholder="描述此端点的功能">
                                                </div>

                                                <div class="mb-4">
                                                    <label class="block text-sm font-medium text-gray-700 mb-1">响应数据路径</label>
                                                    <input v-model="endpoint.response_data_path" type="text"
                                                        class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                                        placeholder="例如: data.items">
                                                    <p class="text-xs text-gray-500 mt-1">从响应JSON中提取数据的路径，如 data.items</p>
                                                </div>

                                                <!-- 参数配置 -->
                                                <div class="border-t border-gray-200 pt-4 mt-4">
                                                    <div class="flex justify-between items-center mb-3">
                                                        <label class="block text-sm font-medium text-gray-700">配置输入参数</label>
                                                        <button type="button" @click="addParamToEndpoint(epIndex)"
                                                            class="text-sm text-blue-600 hover:text-blue-700">
                                                            + 添加参数
                                                        </button>
                                                    </div>

                                                    <div v-if="endpoint.params && endpoint.params.length > 0" class="overflow-x-auto">
                                                        <table class="w-full text-sm">
                                                            <thead>
                                                                <tr class="bg-gray-100">
                                                                    <th class="px-3 py-2 text-left font-medium text-gray-700">参数名称</th>
                                                                    <th class="px-3 py-2 text-left font-medium text-gray-700">参数描述</th>
                                                                    <th class="px-3 py-2 text-left font-medium text-gray-700">是否必填</th>
                                                                    <th class="px-3 py-2 text-left font-medium text-gray-700">默认值</th>
                                                                    <th class="px-3 py-2 text-left font-medium text-gray-700">操作</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                <tr v-for="(param, pIndex) in endpoint.params" :key="pIndex" class="border-b border-gray-200">
                                                                    <td class="px-3 py-2">
                                                                        <input v-model="param.name" type="text"
                                                                            class="w-full px-2 py-1 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                                                                            placeholder="参数名">
                                                                    </td>
                                                                    <td class="px-3 py-2">
                                                                        <input v-model="param.description" type="text"
                                                                            class="w-full px-2 py-1 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                                                                            placeholder="参数说明">
                                                                    </td>
                                                                    <td class="px-3 py-2 text-center">
                                                                        <input v-model="param.required" type="checkbox"
                                                                            class="w-4 h-4 text-blue-600 rounded focus:ring-blue-500">
                                                                    </td>
                                                                    <td class="px-3 py-2">
                                                                        <input v-model="param.default_value" type="text"
                                                                            class="w-full px-2 py-1 border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                                                                            placeholder="默认值">
                                                                    </td>
                                                                    <td class="px-3 py-2">
                                                                        <button type="button" @click="removeParamFromEndpoint(epIndex, pIndex)"
                                                                            class="text-red-500 hover:text-red-700">
                                                                            删除
                                                                        </button>
                                                                    </td>
                                                                </tr>
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                    <div v-else class="text-sm text-gray-500 py-2">
                                                        暂无参数配置
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Footer -->
                                    <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                                        <button type="button" @click="closeApiModal"
                                            class="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition">
                                            取消
                                        </button>
                                        <button type="button" @click="saveApi"
                                            class="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition">
                                            保存
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Delete Confirm Modal -->
                        <div v-if="showDeleteConfirmModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                            <div class="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
                                <h3 class="text-lg font-semibold text-gray-800 mb-4">确认删除</h3>
                                <p class="text-gray-600 mb-6">确定要删除API "{{ apiToDelete?.name }}" 吗？此操作不可恢复。</p>
                                <div class="flex justify-end space-x-3">
                                    <button @click="showDeleteConfirmModal = false"
                                        class="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition">
                                        取消
                                    </button>
                                    <button @click="deleteApi"
                                        class="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition">
                                        确认删除
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- History View -->
                    <div v-else-if="currentView === 'history'" class="flex-1 overflow-y-auto p-10 bg-slate-50/50"
                        ref="historyListViewRef"
                        @scroll="onHistoryScroll($event.target.scrollTop)">
                        <div class="mb-10">
                            <h2 class="text-2xl font-bold text-zinc-950 tracking-tight">对话历史</h2>
                            <p class="text-sm text-zinc-500 mt-1">回顾您的历史对话记录</p>
                        </div>

                        <div v-if="conversations.length === 0" class="bg-white border border-zinc-200 border-dashed rounded-xl p-20 text-center">
                            <div class="w-16 h-16 bg-zinc-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-zinc-100">
                                <svg class="w-8 h-8 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                            </div>
                            <h4 class="text-zinc-900 font-bold">暂无历史记录</h4>
                            <p class="text-zinc-500 text-sm mt-1">开启一段新的对话来存储历史</p>
                        </div>

                        <div v-else class="space-y-3 max-w-4xl mx-auto">
                            <div v-for="(conv, idx) in conversations" :key="conv.id"
                                class="group bg-white rounded-xl border p-5 hover:border-zinc-950 hover:shadow-card transition-all-custom cursor-pointer flex items-center justify-between"
                                :class="conv.id === historySelectedConvId ? 'border-blue-500 shadow-blue-100' : 'border-zinc-200'">
                                <div class="flex items-center space-x-5 flex-1" @click="onHistoryConvClick(conv.id); loadConversation(conv)">
                                    <div class="w-12 h-12 bg-zinc-50 rounded-xl flex items-center justify-center border border-zinc-100 group-hover:bg-green-500 group-hover:text-white transition-all-custom shadow-xs">
                                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                                        </svg>
                                    </div>
                                    <div>
                                        <h4 class="font-bold text-zinc-900 group-hover:text-zinc-950 transition-colors">{{ conv.title || '未命名对话' }}</h4>
                                        <div class="flex items-center space-x-3 mt-1">
                                            <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{{ conv.messages?.length || 0 }} 条消息</span>
                                            <span class="w-1 h-1 bg-zinc-200 rounded-full"></span>
                                            <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{{ (conv.updated_at || conv.updatedAt || conv.createdAt) ? new Date(conv.updated_at || conv.updatedAt || conv.createdAt).toLocaleString('zh-CN') : '' }}</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="flex items-center space-x-2">
                                    <div v-if="conv.id === historySelectedConvId" class="px-3 py-1 bg-blue-50 text-blue-600 text-[10px] font-bold rounded-lg border border-blue-200">
                                        当前选中
                                    </div>
                                    <button class="px-4 py-2 bg-zinc-50 text-zinc-400 text-[10px] font-bold uppercase rounded-lg border border-zinc-100 group-hover:bg-green-500 group-hover:border-green-500 group-hover:text-white transition-all-custom opacity-0 group-hover:opacity-100 translate-x-4 group-hover:translate-x-0"
                                        @click.stop="showHistoryDetail(conv, historyListViewRef ? historyListViewRef.scrollTop : 0)">
                                        查看详情
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
  <!-- 关闭 History View -->

                    <!-- Admin Panel View -->
                    <div v-else-if="currentView === 'admin'" class="flex-1 overflow-y-auto p-10 bg-slate-50/50">
                        <div class="mb-10 flex justify-between items-end">
                            <div>
                                <h2 class="text-2xl font-bold text-zinc-950 tracking-tight">管理操作</h2>
                                <p class="text-sm text-zinc-500 mt-1">管理用户、积分和系统审计日志</p>
                            </div>
                        </div>

                        <!-- Admin Tabs -->
                        <div class="flex items-center space-x-1 p-1 bg-zinc-100 rounded-xl w-fit mb-8 border border-zinc-200 shadow-sm">
                            <button @click="adminTab = 'users'"
                                :class="['px-6 py-2 text-sm font-bold rounded-lg transition-all-custom', adminTab === 'users' ? 'bg-white text-zinc-950 shadow-sm' : 'text-zinc-500 hover:text-zinc-700']">
                                用户管理
                            </button>
                            <button @click="adminTab = 'apis'"
                                :class="['px-6 py-2 text-sm font-bold rounded-lg transition-all-custom', adminTab === 'apis' ? 'bg-white text-zinc-950 shadow-sm' : 'text-zinc-500 hover:text-zinc-700']">
                                API管理
                            </button>
                            <button @click="adminTab = 'user-permissions'"
                                :class="['px-6 py-2 text-sm font-bold rounded-lg transition-all-custom', adminTab === 'user-permissions' ? 'bg-white text-zinc-950 shadow-sm' : 'text-zinc-500 hover:text-zinc-700']">
                                权限概览
                            </button>
                            <button @click="adminTab = 'conversations'"
                                :class="['px-6 py-2 text-sm font-bold rounded-lg transition-all-custom', adminTab === 'conversations' ? 'bg-white text-zinc-950 shadow-sm' : 'text-zinc-500 hover:text-zinc-700']">
                                对话记录
                            </button>
                            <button @click="adminTab = 'logs'"
                                :class="['px-6 py-2 text-sm font-bold rounded-lg transition-all-custom', adminTab === 'logs' ? 'bg-white text-zinc-950 shadow-sm' : 'text-zinc-500 hover:text-zinc-700']">
                                积分日志
                            </button>
                        </div>

                            <!-- Users Tab -->
                            <div v-if="adminTab === 'users'">
                                <div v-if="adminUsersLoading" class="text-center py-20">
                                    <div class="animate-spin w-10 h-10 border-4 border-green-500 border-t-transparent rounded-full mx-auto"></div>
                                </div>
                                <div v-else>
                                    <!-- Batch Actions Bar -->
                                    <div v-if="selectedUserIds.length > 0" class="mb-4 flex items-center space-x-3 p-3 bg-green-50 border border-green-200 rounded-xl">
                                        <span class="text-xs font-bold text-green-700">已选择 {{ selectedUserIds.length }} 个用户</span>
                                        <button @click="batchDisableUsers(selectedUserIds); selectedUserIds = []" class="px-3 py-1.5 bg-amber-500 text-white rounded-md text-xs font-bold hover:bg-amber-600 transition-all-custom">批量禁用</button>
                                        <button @click="batchDeleteUsers(selectedUserIds); selectedUserIds = []" class="px-3 py-1.5 bg-red-500 text-white rounded-md text-xs font-bold hover:bg-red-600 transition-all-custom">批量删除</button>
                                        <button @click="selectedUserIds = []" class="px-3 py-1.5 text-zinc-500 hover:text-zinc-900 text-xs font-bold transition-all-custom">取消</button>
                                    </div>
                                    <div class="bg-white rounded-xl border border-zinc-200 shadow-card overflow-hidden">
                                        <table class="min-w-full divide-y divide-zinc-200">
                                            <thead class="bg-zinc-50">
                                                <tr>
                                                    <th class="px-4 py-4 text-left">
                                                        <input type="checkbox" @change="$event.target.checked ? selectedUserIds = adminUsers.filter(u => u.role !== 'admin').map(u => u.user_id) : selectedUserIds = []" class="form-checkbox h-4 w-4 text-green-500 border-zinc-300 rounded focus:ring-green-500">
                                                    </th>
                                                    <th class="px-6 py-4 text-left text-[10px] font-bold text-zinc-400 uppercase tracking-widest">用户名</th>
                                                    <th class="px-6 py-4 text-left text-[10px] font-bold text-zinc-400 uppercase tracking-widest">角色</th>
                                                    <th class="px-6 py-4 text-left text-[10px] font-bold text-zinc-400 uppercase tracking-widest">状态</th>
                                                    <th class="px-6 py-4 text-left text-[10px] font-bold text-zinc-400 uppercase tracking-widest">部门</th>
                                                    <th class="px-6 py-4 text-left text-[10px] font-bold text-zinc-400 uppercase tracking-widest">积分余额</th>
                                                    <th class="px-6 py-4 text-left text-[10px] font-bold text-zinc-400 uppercase tracking-widest">操作</th>
                                                </tr>
                                            </thead>
                                            <tbody class="bg-white divide-y divide-zinc-100">
                                                <tr v-for="u in adminUsers" :key="u.user_id" :class="['transition-colors', u.is_active === false ? 'bg-zinc-50/60' : 'hover:bg-zinc-50']">
                                                    <td class="px-4 py-4 whitespace-nowrap">
                                                        <input v-if="u.role !== 'admin'" type="checkbox" :value="u.user_id" v-model="selectedUserIds" class="form-checkbox h-4 w-4 text-green-500 border-zinc-300 rounded focus:ring-green-500">
                                                    </td>
                                                    <td class="px-6 py-4 whitespace-nowrap">
                                                        <div class="flex items-center space-x-3">
                                                            <div :class="['w-8 h-8 text-white rounded-lg flex items-center justify-center text-xs font-bold ring-2 ring-white shadow-sm', u.is_active === false ? 'bg-zinc-300' : 'bg-green-500']">
                                                                {{ u.username?.charAt(0).toUpperCase() }}
                                                            </div>
                                                            <span :class="['font-bold', u.is_active === false ? 'text-zinc-400 line-through' : 'text-zinc-900']">{{ u.username }}</span>
                                                        </div>
                                                    </td>
                                                    <td class="px-6 py-4 whitespace-nowrap">
                                                        <span class="px-2 py-0.5 bg-zinc-100 text-zinc-600 border border-zinc-200 rounded text-[10px] font-bold uppercase tracking-wider">
                                                            {{ getRoleName(u.role) }}
                                                        </span>
                                                    </td>
                                                    <td class="px-6 py-4 whitespace-nowrap">
                                                        <span v-if="u.is_active !== false" class="px-1.5 py-0.5 bg-green-100 text-green-700 text-[10px] font-bold rounded">启用</span>
                                                        <span v-else class="px-1.5 py-0.5 bg-zinc-100 text-zinc-500 text-[10px] font-bold rounded">已禁用</span>
                                                    </td>
                                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-zinc-500">{{ u.department || '-' }}</td>
                                                    <td class="px-6 py-4 whitespace-nowrap">
                                                        <div v-if="u.quota.is_unlimited" class="flex items-center space-x-1.5 text-indigo-600">
                                                            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-11c0-.55.45-1 1-1s1 .45 1 1v4c0 .55-.45 1-1 1s-1-.45-1-1v-4z"></path></svg>
                                                            <span class="font-bold text-xs uppercase tracking-widest">无限权限</span>
                                                        </div>
                                                        <div v-else class="flex items-center space-x-2">
                                                            <div class="w-24 h-1.5 bg-zinc-100 rounded-full overflow-hidden">
                                                                <div :class="['h-full rounded-full transition-all duration-500', u.quota.current_balance > 20 ? 'bg-green-500' : 'bg-red-500']" :style="{ width: Math.min((u.quota.current_balance / u.quota.daily_limit) * 100, 100) + '%' }"></div>
                                                            </div>
                                                            <span :class="['text-xs font-bold leading-none', u.quota.current_balance > 20 ? 'text-zinc-950' : 'text-red-600']">
                                                                {{ u.quota.current_balance }}
                                                            </span>
                                                        </div>
                                                    </td>
                                                    <td class="px-6 py-4 whitespace-nowrap">
                                                        <div class="flex items-center space-x-2">
                                                            <button @click="adjustUserQuotaPrompt(u.user_id)" class="text-xs font-bold text-zinc-400 hover:text-zinc-950 transition-all-custom flex items-center space-x-1">
                                                                <span>调整积分</span>
                                                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path></svg>
                                                            </button>
                                                            <button v-if="u.role !== 'admin'" @click="userToDisable = u; showDisableUserModal = true" :class="['text-xs font-bold rounded px-2 py-1 transition', u.is_active === false ? 'bg-green-100 text-green-700 hover:bg-green-200' : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200']">
                                                                {{ u.is_active === false ? '启用' : '禁用' }}
                                                            </button>
                                                            <button v-if="u.role !== 'admin'" @click="userToDelete = u; showDeleteUserModal = true" class="text-xs font-bold text-red-500 hover:text-red-600 transition px-2 py-1 rounded hover:bg-red-50">
                                                                删除
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>

                            <!-- API Management Tab -->
                            <div v-if="adminTab === 'apis'">
                                <div class="flex gap-6">
                                    <!-- Left Panel: Categories -->
                                    <div class="w-72 flex-shrink-0">
                                        <div class="bg-white rounded-xl border border-zinc-200 shadow-card overflow-hidden">
                                            <div class="px-4 py-3 border-b border-zinc-100 flex justify-between items-center">
                                                <h3 class="text-sm font-bold text-zinc-900">API 分类</h3>
                                            </div>
                                            <div class="divide-y divide-zinc-100">
                                                <div v-for="cat in apiCategories" :key="cat.id"
                                                    @click="selectedApiCategory = cat.id"
                                                    :class="['px-4 py-3 cursor-pointer transition-all-custom flex justify-between items-center', selectedApiCategory === cat.id ? 'bg-green-500 text-white' : 'hover:bg-zinc-50']">
                                                    <span class="text-sm font-medium">{{ cat.name }}</span>
                                                    <span :class="['text-xs', selectedApiCategory === cat.id ? 'text-zinc-400' : 'text-zinc-400']">{{ cat.api_count || 0 }}</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Right Panel: APIs and Permissions -->
                                    <div class="flex-1 space-y-6">
                                        <!-- API Repository -->
                                        <div class="bg-white rounded-xl border border-zinc-200 shadow-card overflow-hidden">
                                            <div class="px-4 py-3 border-b border-zinc-100 flex justify-between items-center">
                                                <h3 class="text-sm font-bold text-zinc-900">API 仓库</h3>
                                                <div class="flex items-center space-x-2">
                                                    <label class="flex items-center space-x-2 cursor-pointer mr-2">
                                                        <input type="checkbox" :checked="selectedApiIds.length === systemApis.length && systemApis.length > 0"
                                                               @change="toggleSelectAllApis" class="form-checkbox h-4 w-4 text-zinc-900 border-zinc-300 rounded focus:ring-zinc-500">
                                                        <span class="text-xs text-zinc-600">全选</span>
                                                    </label>
                                                    <button v-if="selectedApiIds.length > 0" @click="openBatchGrantModal('categorized')" class="px-3 py-1.5 bg-blue-600 text-white text-xs font-bold rounded-md hover:bg-blue-700 transition-all-custom flex items-center space-x-1">
                                                        <span>批量授权 ({{ selectedApiIds.length }})</span>
                                                    </button>
                                                    <button @click="loadSystemApis()" class="px-3 py-1.5 text-xs font-bold text-zinc-500 hover:text-zinc-950 transition-all-custom">
                                                        刷新
                                                    </button>
                                                </div>
                                            </div>
                                            <div v-if="adminApisLoading" class="text-center py-10">
                                                <div class="animate-spin w-6 h-6 border-2 border-zinc-950 border-t-transparent rounded-full mx-auto"></div>
                                            </div>
                                            <div v-else-if="systemApis.length === 0" class="p-10 text-center text-zinc-400 text-sm">
                                                暂无已分类 API
                                            </div>
                                            <div v-else class="divide-y divide-zinc-100">
                                                <div v-for="api in systemApis" :key="api.id" class="px-4 py-3 hover:bg-zinc-50 transition-all-custom">
                                                    <div class="flex justify-between items-start">
                                                        <div class="flex-1 flex items-start space-x-3">
                                                            <input type="checkbox" :value="api.id" v-model="selectedApiIds" class="mt-1 form-checkbox h-4 w-4 text-zinc-900 border-zinc-300 rounded focus:ring-zinc-500">
                                                            <div>
                                                                <div class="flex items-center space-x-2">
                                                                <h4 class="font-bold text-zinc-900 text-sm">{{ api.name }}</h4>
                                                                <span v-if="api.is_active" class="px-1.5 py-0.5 bg-green-100 text-green-700 text-[10px] font-bold rounded">启用</span>
                                                                <span v-else class="px-1.5 py-0.5 bg-zinc-100 text-zinc-500 text-[10px] font-bold rounded">禁用</span>
                                                            </div>
                                                            <p class="text-xs text-zinc-500 mt-1">{{ api.description || '暂无描述' }}</p>
                                                            <div class="flex items-center space-x-4 mt-2 text-[10px] text-zinc-400">
                                                                <span>分类: {{ api.category_path || '未分类' }}</span>
                                                                <span>端点: {{ Object.keys(api.endpoints || {}).length }} 个</span>
                                                            </div>
                                                        </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- Uncategorized APIs -->
                                        <div class="bg-white rounded-xl border border-zinc-200 shadow-card overflow-hidden">
                                            <div class="px-4 py-3 border-b border-zinc-100 flex justify-between items-center">
                                                <h3 class="text-sm font-bold text-zinc-900">未加入分组的 API</h3>
                                                <div class="flex items-center space-x-2">
                                                    <label class="flex items-center space-x-2 cursor-pointer mr-2">
                                                        <input type="checkbox" :checked="selectedUncategorizedApiIds.length === uncategorizedSystemApis.length && uncategorizedSystemApis.length > 0"
                                                               @change="toggleSelectAllUncategorizedApis" class="form-checkbox h-4 w-4 text-zinc-900 border-zinc-300 rounded focus:ring-zinc-500">
                                                        <span class="text-xs text-zinc-600">全选</span>
                                                    </label>
                                                    <button v-if="selectedUncategorizedApiIds.length > 0" @click="openBatchGrantModal('uncategorized')" class="px-3 py-1.5 bg-blue-600 text-white text-xs font-bold rounded-md hover:bg-blue-700 transition-all-custom flex items-center space-x-1">
                                                        <span>批量授权 ({{ selectedUncategorizedApiIds.length }})</span>
                                                    </button>
                                                    <button @click="loadSystemApis()" class="px-3 py-1.5 text-xs font-bold text-zinc-500 hover:text-zinc-950 transition-all-custom">
                                                        刷新
                                                    </button>
                                                </div>
                                            </div>
                                            <div v-if="adminApisLoading" class="text-center py-10">
                                                <div class="animate-spin w-6 h-6 border-2 border-zinc-950 border-t-transparent rounded-full mx-auto"></div>
                                            </div>
                                            <div v-else-if="uncategorizedSystemApis.length === 0" class="p-10 text-center text-zinc-400 text-sm">
                                                暂无未分组 API
                                            </div>
                                            <div v-else class="divide-y divide-zinc-100">
                                                <div v-for="api in uncategorizedSystemApis" :key="api.id" class="px-4 py-3 hover:bg-zinc-50 transition-all-custom">
                                                    <div class="flex justify-between items-start">
                                                        <div class="flex-1 flex items-start space-x-3">
                                                            <input type="checkbox" :value="api.id" v-model="selectedUncategorizedApiIds" class="mt-1 form-checkbox h-4 w-4 text-zinc-900 border-zinc-300 rounded focus:ring-zinc-500">
                                                            <div>
                                                                <div class="flex items-center space-x-2">
                                                                    <h4 class="font-bold text-zinc-900 text-sm">{{ api.name }}</h4>
                                                                    <span v-if="api.is_active" class="px-1.5 py-0.5 bg-green-100 text-green-700 text-[10px] font-bold rounded">启用</span>
                                                                    <span v-else class="px-1.5 py-0.5 bg-zinc-100 text-zinc-500 text-[10px] font-bold rounded">禁用</span>
                                                                </div>
                                                                <p class="text-xs text-zinc-500 mt-1">{{ api.description || '暂无描述' }}</p>
                                                                <div class="flex items-center space-x-4 mt-2 text-[10px] text-zinc-400">
                                                                    <span>分类: 未分组</span>
                                                                    <span>端点: {{ Object.keys(api.endpoints || {}).length }} 个</span>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- User Permissions Overview Tab -->
                            <div v-if="adminTab === 'user-permissions'">
                                <div class="bg-white rounded-xl border border-zinc-200 shadow-card overflow-hidden">
                                    <div class="px-4 py-3 border-b border-zinc-100 flex justify-between items-center">
                                        <h3 class="text-sm font-bold text-zinc-900">用户权限概览</h3>
                                        <div class="space-y-2 w-64">
                                            <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest pl-1">员工筛选</label>
                                            <div class="relative">
                                                <input v-model="selectedPermUserSearch"
                                                    @focus="showPermUserDropdown = true"
                                                    @blur="setTimeout(() => showPermUserDropdown = false, 200)"
                                                    type="text" placeholder="选择用户..."
                                                    class="w-full px-4 py-3 bg-white border border-zinc-200 rounded-xl text-sm text-zinc-900 focus:ring-2 focus:ring-green-500 focus:border-green-500 focus:outline-none transition-all-custom placeholder:text-zinc-400">
                                                <div v-if="showPermUserDropdown"
                                                     class="absolute z-30 mt-2 w-full bg-white border border-zinc-200 rounded-xl shadow-2xl max-h-48 overflow-y-auto">
                                                    <div v-for="u in filteredAdminUsers" :key="u.user_id"
                                                         @click="selectPermUser(u.user_id)"
                                                         class="px-4 py-3 hover:bg-green-50 cursor-pointer text-sm text-zinc-700 border-b border-zinc-100 last:border-b-0 transition-colors">
                                                        {{ u.username }}
                                                    </div>
                                                    <div v-if="filteredAdminUsers.length === 0" class="px-4 py-3 text-sm text-zinc-400 text-center">无匹配用户</div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div v-if="selectedPermUser && userPermissionsOverview" class="p-6">
                                        <div class="mb-6 flex items-center space-x-4 border-b border-zinc-100 pb-4">
                                            <div class="w-12 h-12 bg-green-500 text-white rounded-xl flex items-center justify-center shadow-lg ring-4 ring-green-50 font-bold text-lg">
                                                {{ userPermissionsOverview.username?.charAt(0).toUpperCase() }}
                                            </div>
                                            <div>
                                                <h2 class="text-xl font-bold text-zinc-900">{{ userPermissionsOverview.username }}</h2>
                                                <div class="flex space-x-3 mt-1">
                                                    <span class="text-xs text-zinc-500 uppercase tracking-wider font-medium">{{ getRoleName(userPermissionsOverview.role) }}</span>
                                                    <span class="text-xs text-zinc-500">•</span>
                                                    <span class="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">{{ userPermissionsOverview.total_permissions }} 个授权API</span>
                                                </div>
                                            </div>
                                        </div>

                                        <div class="space-y-6">
                                            <div v-if="userPermissionsOverview.total_permissions === 0" class="bg-white border border-zinc-200 border-dashed rounded-xl p-12 text-center">
                                                <h4 class="text-zinc-900 font-bold">该用户暂无授权 API</h4>
                                                <p class="text-zinc-500 text-sm mt-1">请在 API 管理 中为该用户分配权限</p>
                                            </div>

                                            <div v-for="category in userPermissionsOverview.categorized" :key="category.category_id" class="bg-white rounded-xl border border-zinc-200 overflow-hidden shadow-sm">
                                                <div @click="toggleOverviewCategory(category.category_id)"
                                                     class="flex justify-between items-center p-4 bg-zinc-50 border-b border-zinc-200 cursor-pointer hover:bg-zinc-100 transition-colors">
                                                    <div class="flex items-center space-x-3">
                                                        <svg :class="{'rotate-90': overviewExpandedCategories.has(category.category_id)}"
                                                             class="w-5 h-5 text-zinc-400 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                                        </svg>
                                                        <h3 class="font-bold text-zinc-900">{{ category.category_name }}</h3>
                                                    </div>
                                                    <span class="bg-zinc-200 text-zinc-700 text-xs font-bold px-2 py-1 rounded-full">
                                                        {{ category.apis.length }} 个API
                                                    </span>
                                                </div>

                                                <div v-show="overviewExpandedCategories.has(category.category_id)" class="p-5 bg-white">
                                                    <div v-if="category.apis.length === 0" class="text-center py-6 text-zinc-500 text-sm">
                                                        此分类下暂无授权API
                                                    </div>
                                                    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                                                        <div v-for="api in category.apis" :key="api.api_id"
                                                            class="group bg-white rounded-xl border border-zinc-200 p-5 hover:shadow-card-hover hover:border-zinc-300 transition-all-custom relative flex flex-col">
                                                            <div class="w-10 h-10 bg-zinc-50 rounded-lg flex items-center justify-center border border-zinc-100 group-hover:bg-green-500 group-hover:text-white transition-all-custom mb-4">
                                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                                                                </svg>
                                                            </div>
                                                            <h3 class="font-bold text-zinc-950 mb-1 tracking-tight truncate" :title="api.api_name">{{ api.api_name }}</h3>
                                                            <p class="text-zinc-500 text-xs line-clamp-2 h-8 leading-relaxed mb-3">{{ api.api_description || '暂无描述' }}</p>
                                                            <p class="text-[10px] text-zinc-400 mb-6">授权时间: {{ api.granted_at ? new Date(api.granted_at).toLocaleString('zh-CN') : '未知' }}</p>
                                                            <div class="pt-4 border-t border-zinc-50 mt-auto">
                                                                <button @click="revokePermissionFromOverview(api.api_id)" class="w-full text-xs font-bold text-red-500 hover:text-red-700 bg-red-50 hover:bg-red-100 px-3 py-2 rounded transition-colors">
                                                                    取消授权
                                                                </button>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>

                                            <div v-if="userPermissionsOverview.uncategorized && userPermissionsOverview.uncategorized.length > 0" class="bg-white rounded-xl border border-zinc-200 overflow-hidden shadow-sm">
                                                <div class="flex justify-between items-center p-4 bg-zinc-50 border-b border-zinc-200">
                                                    <div class="flex items-center space-x-3">
                                                        <div class="w-5 h-5 flex items-center justify-center">
                                                            <svg class="w-5 h-5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path>
                                                            </svg>
                                                        </div>
                                                        <div>
                                                            <h3 class="font-bold text-zinc-900">未分类 API</h3>
                                                            <p class="text-xs text-zinc-500 mt-0.5">尚未归入任何类别的授权API</p>
                                                        </div>
                                                    </div>
                                                    <span class="bg-zinc-200 text-zinc-700 text-xs font-bold px-2 py-1 rounded-full">
                                                        {{ userPermissionsOverview.uncategorized.length }} 个API
                                                    </span>
                                                </div>
                                                <div class="p-5 bg-white">
                                                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                                                        <div v-for="api in userPermissionsOverview.uncategorized" :key="api.api_id"
                                                            class="group bg-white rounded-xl border border-zinc-200 p-5 hover:shadow-card-hover hover:border-zinc-300 transition-all-custom relative flex flex-col">
                                                            <div class="w-10 h-10 bg-zinc-50 rounded-lg flex items-center justify-center border border-zinc-100 group-hover:bg-green-500 group-hover:text-white transition-all-custom mb-4">
                                                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
                                                                </svg>
                                                            </div>
                                                            <h3 class="font-bold text-zinc-950 mb-1 tracking-tight truncate" :title="api.api_name">{{ api.api_name }}</h3>
                                                            <p class="text-zinc-500 text-xs line-clamp-2 h-8 leading-relaxed mb-3">{{ api.api_description || '暂无描述' }}</p>
                                                            <p class="text-[10px] text-zinc-400 mb-6">授权时间: {{ api.granted_at ? new Date(api.granted_at).toLocaleString('zh-CN') : '未知' }}</p>
                                                            <div class="pt-4 border-t border-zinc-50 mt-auto">
                                                                <button @click="revokePermissionFromOverview(api.api_id)" class="w-full text-xs font-bold text-red-500 hover:text-red-700 bg-red-50 hover:bg-red-100 px-3 py-2 rounded transition-colors">
                                                                    取消授权
                                                                </button>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div v-else-if="selectedPermUser" class="p-20 text-center">
                                        <div class="animate-spin w-8 h-8 border-2 border-zinc-950 border-t-transparent rounded-full mx-auto"></div>
                                    </div>
                                    <div v-else class="p-20 text-center">
                                        <div class="w-16 h-16 bg-zinc-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-zinc-100">
                                            <svg class="w-8 h-8 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
                                            </svg>
                                        </div>
                                        <h4 class="text-zinc-900 font-bold">查看用户权限</h4>
                                        <p class="text-zinc-500 text-sm mt-1">请在上方搜索并选择一位用户</p>
                                    </div>
                                </div>
                            </div>

                            <!-- Batch Grant Modal -->
                            <div v-if="showBatchGrantModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-zinc-950/40 backdrop-blur-sm">
                                <div class="bg-white rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-fade-in-up">
                                    <div class="px-6 py-4 border-b border-zinc-100 flex justify-between items-center">
                                        <h3 class="text-lg font-bold text-zinc-900">批量授权</h3>
                                        <button @click="closeBatchGrantModal" class="text-zinc-400 hover:text-zinc-950 transition-colors">
                                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                                        </button>
                                    </div>
                                    <div class="p-6 space-y-6">
                                        <div class="text-sm text-zinc-600 mb-2">
                                            正在为 <span class="font-bold text-zinc-900">{{ batchGrantSource === 'uncategorized' ? selectedUncategorizedApiIds.length : selectedApiIds.length }}</span> 个API授权：
                                        </div>

                                        <div class="space-y-2">
                                            <label class="block text-sm font-bold text-zinc-900">选择用户</label>
                                            <div class="relative">
                                                <input v-model="batchUserSearchQuery"
                                                    @focus="openBatchUserDropdown"
                                                    @blur="closeBatchUserDropdown"
                                                    @input="searchBatchUsers"
                                                    type="text" placeholder="选择用户..."
                                                    class="w-full px-4 py-3 bg-zinc-50 border border-zinc-200 rounded-xl text-sm focus:ring-2 focus:ring-zinc-900 focus:outline-none transition-all-custom placeholder:text-zinc-400">

                                                <div v-if="showBatchUserDropdown"
                                                     class="absolute z-50 mt-2 w-full bg-white border border-zinc-200 rounded-xl shadow-xl max-h-60 overflow-y-auto">
                                                    <div v-for="user in filteredBatchUsers" :key="user.user_id"
                                                         @click="toggleBatchUser(user)"
                                                         class="px-4 py-3 hover:bg-zinc-50 cursor-pointer flex items-center space-x-3 border-b border-zinc-100 last:border-0 transition-colors">
                                                        <div class="w-4 h-4 border rounded flex items-center justify-center" :class="isUserSelected(user.user_id) ? 'bg-green-500 border-green-500 text-white' : 'border-zinc-300'">
                                                            <svg v-if="isUserSelected(user.user_id)" class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                                                        </div>
                                                        <div class="flex flex-col">
                                                            <span class="text-sm font-medium text-zinc-900">{{ user.username }}</span>
                                                            <span class="text-[10px] text-zinc-500">{{ getRoleName(user.role) }}</span>
                                                        </div>
                                                    </div>
                                                    <div v-if="filteredBatchUsers.length === 0" class="px-4 py-3 text-sm text-zinc-400 text-center">无匹配用户</div>
                                                </div>
                                            </div>

                                            <!-- Selected Users Tags -->
                                            <div class="flex flex-wrap gap-2 mt-3">
                                                <div v-for="user in selectedBatchUsers" :key="user.user_id"
                                                     class="inline-flex items-center px-2 py-1 rounded bg-zinc-100 border border-zinc-200 text-xs font-medium text-zinc-800">
                                                    {{ user.username }}
                                                    <button @click="removeBatchUser(user.user_id)" class="ml-1.5 text-zinc-400 hover:text-red-500">
                                                        <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                                                    </button>
                                                </div>
                                                <div v-if="selectedBatchUsers.length === 0" class="text-xs text-zinc-400 italic py-1">
                                                    尚未选择用户
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="px-6 py-4 border-t border-zinc-100 bg-zinc-50 flex justify-end space-x-3">
                                        <button @click="closeBatchGrantModal" class="px-4 py-2 text-sm font-bold text-zinc-600 hover:text-zinc-900 transition-colors">取消</button>
                                        <button @click="executeBatchGrant" :disabled="selectedBatchUsers.length === 0"
                                            class="px-4 py-2 bg-green-500 text-white text-sm font-bold rounded-lg hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed">
                                            确认授权
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Delete User Confirm Modal -->
                            <div v-if="showDeleteUserModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-zinc-950/40 backdrop-blur-sm">
                                <div class="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden animate-fade-in-up">
                                    <div class="px-6 py-4 border-b border-zinc-100">
                                        <h3 class="text-lg font-bold text-zinc-900">确认删除用户</h3>
                                    </div>
                                    <div class="p-6">
                                        <p class="text-sm text-zinc-600 mb-2">确定要删除用户 <span class="font-bold text-zinc-900">"{{ userToDelete?.username }}"</span> 吗？</p>
                                        <p class="text-xs text-zinc-400">该用户的对话记录、积分日志等数据将保留，但账号将被永久删除。下次 CIA 登录会自动重新注册。</p>
                                    </div>
                                    <div class="px-6 py-4 border-t border-zinc-100 bg-zinc-50 flex justify-end space-x-3">
                                        <button @click="showDeleteUserModal = false; userToDelete = null" class="px-4 py-2 text-sm font-bold text-zinc-600 hover:text-zinc-900 transition-colors">取消</button>
                                        <button @click="deleteUser(userToDelete.user_id); showDeleteUserModal = false; userToDelete = null" class="px-4 py-2 bg-red-500 text-white text-sm font-bold rounded-lg hover:bg-red-600 transition-colors">确认删除</button>
                                    </div>
                                </div>
                            </div>

                            <!-- Disable/Enable User Confirm Modal -->
                            <div v-if="showDisableUserModal" class="fixed inset-0 z-[100] flex items-center justify-center bg-zinc-950/40 backdrop-blur-sm">
                                <div class="bg-white rounded-2xl w-full max-w-md shadow-2xl overflow-hidden animate-fade-in-up">
                                    <div class="px-6 py-4 border-b border-zinc-100">
                                        <h3 class="text-lg font-bold text-zinc-900">确认{{ userToDisable?.is_active === false ? '启用' : '禁用' }}用户</h3>
                                    </div>
                                    <div class="p-6">
                                        <p class="text-sm text-zinc-600">确定要{{ userToDisable?.is_active === false ? '启用' : '禁用' }}用户 <span class="font-bold text-zinc-900">"{{ userToDisable?.username }}"</span> 吗？</p>
                                        <p v-if="userToDisable?.is_active !== false" class="text-xs text-zinc-400 mt-2">禁用后该用户将无法登录，已有 token 也会被拒绝。</p>
                                    </div>
                                    <div class="px-6 py-4 border-t border-zinc-100 bg-zinc-50 flex justify-end space-x-3">
                                        <button @click="showDisableUserModal = false; userToDisable = null" class="px-4 py-2 text-sm font-bold text-zinc-600 hover:text-zinc-900 transition-colors">取消</button>
                                        <button @click="toggleUserStatus(userToDisable.user_id, userToDisable.is_active === false); showDisableUserModal = false; userToDisable = null" :class="['px-4 py-2 text-white text-sm font-bold rounded-lg transition-colors', userToDisable?.is_active === false ? 'bg-green-500 hover:bg-green-600' : 'bg-amber-500 hover:bg-amber-600']">确认{{ userToDisable?.is_active === false ? '启用' : '禁用' }}</button>
                                    </div>
                                </div>
                            </div>

                            <!-- Conversations Tab -->
                            <div v-if="adminTab === 'conversations'">
                                <!-- 筛选区域 -->
                                <div class="mb-8 p-8 bg-white rounded-2xl shadow-card border border-zinc-200">
                                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                                        <!-- 员工筛选 -->
                                        <div class="space-y-2">
                                            <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest pl-1">员工筛选</label>
                                            <div class="relative">
                                                <input v-model="adminConvUsernameFilter"
                                                       @focus="showUserDropdown = true"
                                                       @blur="setTimeout(() => showUserDropdown = false, 200)"
                                                       type="text" placeholder="选择用户..."
                                                       class="w-full px-4 py-3 bg-white border border-zinc-200 rounded-xl text-sm text-zinc-900 focus:ring-2 focus:ring-green-500 focus:border-green-500 focus:outline-none transition-all-custom placeholder:text-zinc-400">
                                                <!-- 下拉列表 -->
                                                <div v-if="showUserDropdown && adminUsers.length > 0"
                                                     class="absolute z-30 mt-2 w-full bg-white border border-zinc-200 rounded-xl shadow-2xl max-h-48 overflow-y-auto">
                                                    <div v-for="user in adminUsers" :key="user.user_id"
                                                         @click="selectUserFilter(user.username)"
                                                         class="px-4 py-3 hover:bg-green-50 cursor-pointer text-sm text-zinc-700 border-b border-zinc-100 last:border-b-0 transition-colors">
                                                        {{ user.username }}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- 日期筛选 -->
                                        <div class="space-y-2">
                                            <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest pl-1">日期范围</label>
                                            <div class="flex items-center bg-white border border-zinc-200 rounded-xl overflow-hidden">
                                                <input v-model="adminConvStartDate" type="date"
                                                       class="flex-1 px-3 py-3 bg-white text-sm text-zinc-900 focus:outline-none [color-scheme:light]">
                                                <span class="text-zinc-300 px-1">—</span>
                                                <input v-model="adminConvEndDate" type="date"
                                                       class="flex-1 px-3 py-3 bg-white text-sm text-zinc-900 focus:outline-none [color-scheme:light]">
                                            </div>
                                        </div>

                                        <!-- 关键词搜索 -->
                                        <div class="space-y-2">
                                            <label class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest pl-1">内容搜索</label>
                                            <input v-model="adminConvSearch" type="text" placeholder="输入搜索关键词..."
                                                   class="w-full px-4 py-3 bg-white border border-zinc-200 rounded-xl text-sm text-zinc-900 focus:ring-2 focus:ring-green-500 focus:border-green-500 focus:outline-none transition-all-custom placeholder:text-zinc-400">
                                        </div>
                                    </div>

                                    <!-- 操作按钮 -->
                                    <div class="flex space-x-3 mt-8">
                                        <button @click="applyConvFilters"
                                                class="flex-1 py-3 bg-green-500 text-white font-bold rounded-xl text-sm hover:bg-green-600 transition-all-custom shadow-sm active:scale-[0.98]">
                                            执行筛选
                                        </button>
                                        <button @click="clearConvFilters"
                                                class="px-6 py-3 bg-white border border-zinc-200 text-zinc-500 font-bold rounded-xl text-sm hover:text-zinc-900 hover:border-zinc-300 transition-all-custom">
                                            重置
                                        </button>
                                    </div>
                                </div>

                                <div v-if="adminConvLoading" class="text-center py-20">
                                    <div class="animate-spin w-10 h-10 border-4 border-zinc-950 border-t-transparent rounded-full mx-auto"></div>
                                </div>
                                <div v-else-if="adminConvResults.length === 0" class="bg-white border border-zinc-200 border-dashed rounded-xl p-20 text-center">
                                    <div class="w-16 h-16 bg-zinc-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-zinc-100">
                                        <svg class="w-8 h-8 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                        </svg>
                                    </div>
                                    <h4 class="text-zinc-900 font-bold">无符合条件的记录</h4>
                                    <p class="text-zinc-500 text-sm mt-1">请尝试调整筛选条件或搜索关键词</p>
                                </div>
                                <div v-else class="space-y-4">
                                    <div v-for="conv in adminConvResults" :key="conv.conversation_id + conv.user_id"
                                        class="group bg-white rounded-2xl border border-zinc-200 p-6 hover:border-zinc-950 transition-all-custom cursor-pointer relative"
                                        @click="loadAdminConversationDetail(conv.user_id, conv.session_id || conv.conversation_id)">
                                        <div class="flex items-center justify-between mb-4">
                                            <div class="flex items-center space-x-3">
                                                <div class="px-2 py-1 bg-green-500 text-white text-[10px] font-bold uppercase tracking-widest rounded shadow-sm">
                                                    {{ conv.username }}
                                                </div>
                                                <h4 class="font-bold text-zinc-900 group-hover:text-zinc-950">{{ conv.title || '对话详情' }}</h4>
                                            </div>
                                            <span class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{{ conv.timestamp ? new Date(conv.timestamp).toLocaleString('zh-CN') : '' }}</span>
                                        </div>
                                        <div class="bg-zinc-50 border border-zinc-100 p-4 rounded-xl text-sm text-zinc-600 italic line-clamp-2">
                                            "{{ conv.matched_message }}"
                                        </div>
                                        <div class="absolute bottom-4 right-4 text-zinc-300 opacity-0 group-hover:opacity-100 translate-x-2 group-hover:translate-x-0 transition-all-custom">
                                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Logs Tab -->
                            <div v-if="adminTab === 'logs'">
                                <div v-if="adminLogsLoading" class="text-center py-20">
                                    <div class="animate-spin w-10 h-10 border-4 border-zinc-950 border-t-transparent rounded-full mx-auto"></div>
                                </div>
                                <div v-else-if="userLogsData.length === 0" class="bg-white border border-zinc-200 border-dashed rounded-xl p-20 text-center">
                                    <div class="w-16 h-16 bg-zinc-50 rounded-full flex items-center justify-center mx-auto mb-4 border border-zinc-100">
                                        <svg class="w-8 h-8 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2a2 2 0 00-2-2H5a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2zm0-5V7a2 2 0 012-2h2a2 2 0 012 2v5m-6 0h6m-6 0H3m18 0h-3M3 12h18"></path>
                                        </svg>
                                    </div>
                                    <h4 class="text-zinc-900 font-bold">暂无审计日志</h4>
                                    <p class="text-zinc-500 text-sm mt-1">系统尚未产生积分消耗相关的审计记录</p>
                                </div>
                                <div v-else class="space-y-4 max-w-5xl mx-auto">
                                    <div v-for="userData in userLogsData" :key="userData.user_id"
                                        class="bg-white rounded-2xl border border-zinc-200 shadow-sm overflow-hidden hover:border-zinc-300 transition-all-custom">
                                        <!-- 卡片头部 - 点击展开/收起 -->
                                        <div class="p-6 cursor-pointer hover:bg-zinc-50 transition flex items-center justify-between"
                                            @click="toggleUserLogs(userData.user_id)">
                                            <div class="flex items-center space-x-5">
                                                <div class="w-12 h-12 bg-green-500 text-white rounded-xl flex items-center justify-center shadow-lg ring-4 ring-green-50">
                                                    <span class="font-bold">{{ userData.username?.charAt(0).toUpperCase() }}</span>
                                                </div>
                                                <div>
                                                    <div class="font-bold text-zinc-900 group-hover:text-zinc-950">{{ userData.username }}</div>
                                                    <div class="text-[10px] font-bold text-zinc-400 mt-0.5 uppercase tracking-widest">{{ userData.department || '默认部门' }}</div>
                                                </div>
                                            </div>
                                            <div class="flex items-center space-x-8">
                                                <div class="text-right">
                                                    <div class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-0.5">消耗</div>
                                                    <div class="text-zinc-950 font-bold leading-none">-{{ userData.totalCredits }} 积分</div>
                                                </div>
                                                <div class="w-8 h-8 flex items-center justify-center rounded-full bg-zinc-100 text-zinc-400 group-hover:bg-green-500 group-hover:text-white transition-all-custom" :class="{ 'bg-green-500 text-white': userLogsExpanded[userData.user_id] }">
                                                    <svg class="w-5 h-5 transition-transform"
                                                        :class="{ 'rotate-180': userLogsExpanded[userData.user_id] }"
                                                        fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                                    </svg>
                                                </div>
                                            </div>
                                        </div>

                                        <!-- 展开的详细记录 -->
                                        <div v-if="userLogsExpanded[userData.user_id]" class="border-t border-zinc-100 bg-zinc-50/50 p-6">
                                            <div class="text-[10px] font-bold text-zinc-400 uppercase tracking-widest mb-4">详细审计记录 ({{ userData.logs.length }} 条)</div>
                                            <div class="space-y-3 max-h-96 overflow-y-auto pr-2 scrollbar-zinc">
                                                <div v-for="log in userData.logs" :key="log.timestamp"
                                                    class="bg-white rounded-xl p-4 border border-zinc-100 shadow-xs flex justify-between items-center group hover:border-zinc-300 transition-all-custom">
                                                    <div class="flex-1 min-w-0">
                                                        <div class="text-sm font-bold text-zinc-800 truncate pr-4">"{{ log.query }}"</div>
                                                        <div class="flex items-center space-x-3 mt-1.5 text-[10px] font-bold text-zinc-400 uppercase tracking-widest">
                                                            <span>{{ new Date(log.timestamp).toLocaleString('zh-CN') }}</span>
                                                            <span class="w-1 h-1 bg-zinc-200 rounded-full"></span>
                                                            <span>{{ log.total_tokens }} 令牌</span>
                                                        </div>
                                                    </div>
                                                    <div class="text-right shrink-0">
                                                        <div class="px-3 py-1 bg-green-500 text-white text-xs font-bold rounded-lg shadow-sm group-hover:bg-red-600 transition-colors">
                                                            -{{ log.credits_deducted }}
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- History Detail Modal -->
                        <div v-if="showHistoryModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="showHistoryModal = false">
                            <div class="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
                                <div class="p-4 border-b border-gray-200 flex justify-between items-center flex-shrink-0">
                                    <h3 class="font-semibold text-gray-800">对话详情</h3>
                                    <button @click="showHistoryModal = false" class="text-gray-400 hover:text-gray-600">
                                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                                        </svg>
                                    </button>
                                </div>
                                <div class="flex-1 overflow-y-auto p-4 space-y-4">
                                    <template v-if="selectedHistory && selectedHistory.messages">
                                        <div v-for="(msg, msgIdx) in selectedHistory.messages" :key="msgIdx">
                                            <div v-if="msg.role === 'user'" class="flex justify-end mb-3">
                                                <div class="max-w-2xl bg-blue-500 text-white rounded-2xl rounded-tr-sm px-4 py-3">
                                                    {{ msg.content }}
                                                </div>
                                            </div>
                                            <div v-else class="flex flex-col justify-start mb-3">
                                                <!-- Agent thinking toggle (F-23) -->
                                                <!-- Support both msg.reasoningLog.steps (live) and msg.thought (from history) -->
                                                <div v-if="(msg.reasoningLog && msg.reasoningLog.steps && msg.reasoningLog.steps.length > 0) || (msg.thought && msg.thought.length > 0)" class="mb-2">
                                                    <button class="text-xs text-zinc-400 hover:text-zinc-600 flex items-center gap-1" @click="msg._thoughtExpanded = !msg._thoughtExpanded">
                                                        <svg class="w-3 h-3 transition-transform" :class="msg._thoughtExpanded ? 'rotate-90' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path>
                                                        </svg>
                                                        Agent 思考过程 ({{ (msg.reasoningLog && msg.reasoningLog.steps) ? msg.reasoningLog.steps.length : (msg.thought ? msg.thought.length : 0) }} 步)
                                                    </button>
                                                    <div v-if="msg._thoughtExpanded" class="mt-2 bg-zinc-50 rounded-lg border border-zinc-200 p-3 text-xs text-zinc-600 space-y-2">
                                                        <div v-for="(step, sIdx) in (msg.reasoningLog && msg.reasoningLog.steps) || msg.thought || []" :key="sIdx" class="border-l-2 border-zinc-300 pl-3">
                                                            <div class="font-medium text-zinc-700">步骤 {{ step.step_number || step.step || sIdx + 1 }}</div>
                                                            <div v-if="step.thought">{{ step.thought }}</div>
                                                            <div v-else-if="step.content">{{ step.content }}</div>
                                                            <div v-if="step.action" class="text-purple-600">动作: {{ step.action }}</div>
                                                            <div v-if="step.observation" class="text-green-600">观察: {{ step.observation }}</div>
                                                        </div>
                                                    </div>
                                                </div>
                                                <!-- Assistant message content -->
                                                <div class="max-w-3xl bg-gray-100 rounded-2xl rounded-tl-sm px-4 py-3">
                                                    <div class="text-gray-800 markdown-content" v-html="renderMarkdown(msg.content)" :data-vkey="msg._v || 0"></div>
                                                </div>
                                                <!-- Export button for data messages (F-23) -->
                                                <div v-if="msg.data && msg.data.rows && msg.data.rows.length > 0" class="mt-2 flex justify-start">
                                                    <button class="text-xs text-blue-600 hover:text-blue-700 flex items-center gap-1 border border-blue-200 rounded-lg px-3 py-1.5 bg-blue-50 hover:bg-blue-100 transition-colors"
                                                        @click="exportToExcel(msg)">
                                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                                        </svg>
                                                        导出数据 ({{ msg.data.rows.length }} 行)
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </template>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;
