const CIAModule = {
    config: { enabled: false, client_id: '', auth_mode: 'local_only', cia_url: '' },
    initialized: false,
    _pollTimer: null,

    async loadConfig() {
        try {
            const res = await fetch('/api/v1/auth/cia/config');
            if (!res.ok) return this.config;
            this.config = await res.json();
            return this.config;
        } catch (e) {
            return this.config;
        }
    },

    async init() {
        if (this.initialized) return this.config;
        await this.loadConfig();
        this.initialized = true;
        return this.config;
    },

    async checkLoginStatus() {
        if (!this.config.enabled) return { error: 'CIA 登录未启用' };
        if (typeof CommonLoginUltra === 'undefined') return { error: 'CIA SDK 未加载' };
        try {
            const res = await CommonLoginUltra.checkLoginByClientId(this.config.client_id, 0);
            console.log('CIA checkLoginStatus raw:', res);
            if (res && res.code) {
                return { loggedIn: true, code: res.code, auth_code: '' };
            }
            return { loggedIn: false, auth_code: res && res.auth_code || '' };
        } catch (e) {
            return { error: 'CIA 状态检查异常: ' + (e.message || e) };
        }
    },

    async doLogin(code, auth_code) {
        try {
            const url = `/api/v1/auth/cia/login?code=${encodeURIComponent(code)}&auth_code=${encodeURIComponent(auth_code || '')}`;
            console.log('CIA doLogin:', url);
            const res = await fetch(url);
            const data = await res.json();
            console.log('CIA doLogin response:', data);
            if (data.code === 200 && data.data) {
                return { success: true, data: data.data };
            }
            return { success: false, error: data.message || data.detail || 'CIA 登录失败' };
        } catch (e) {
            return { success: false, error: e.message || '网络错误' };
        }
    },

    async codeLogin(code) {
        try {
            const url = `https://sso.example.com/auth?code=${encodeURIComponent(code)}`;
            console.log('CIA codeLogin:', url);
            const res = await fetch(url, { credentials: 'include', mode: 'cors' });
            const data = await res.json();
            console.log('CIA codeLogin response:', JSON.stringify(data));
            if (data.result && data.access_token) {
                return await this.exchangeToken(data.access_token);
            }
            return { success: false, error: data.errorMessage || 'codeLogin failed' };
        } catch (e) {
            return { success: false, error: e.message || '网络错误' };
        }
    },

    async exchangeToken(cia_access_token) {
        try {
            const url = `/api/v1/auth/cia/token?access_token=${encodeURIComponent(cia_access_token)}`;
            console.log('CIA exchangeToken:', url);
            const res = await fetch(url);
            const data = await res.json();
            console.log('CIA exchangeToken response:', data);
            if (data.code === 200 && data.data) {
                return { success: true, data: data.data };
            }
            return { success: false, error: data.message || data.detail || 'Token exchange failed' };
        } catch (e) {
            return { success: false, error: e.message || '网络错误' };
        }
    },

    startPolling(onLogin) {
        if (this._pollTimer) clearInterval(this._pollTimer);
        this._pollTimer = setInterval(async () => {
            try {
                const res = await CommonLoginUltra.checkLoginByClientId(this.config.client_id, 0);
                if (res && res.code) {
                    clearInterval(this._pollTimer);
                    this._pollTimer = null;
                    if (onLogin) onLogin(res.code, '');
                }
            } catch (e) {}
        }, 2000);
    },

    stopPolling() {
        if (this._pollTimer) {
            clearInterval(this._pollTimer);
            this._pollTimer = null;
        }
    },

    closeLoginBox() {
        try {
            const box = document.getElementById('fixed-login-ultra');
            if (box) box.style.display = 'none';
            document.querySelectorAll('.login-ultra-wrapper').forEach(el => el.style.display = 'none');
            document.body.style.overflow = '';
        } catch (e) {}
    },

    initLoginBox() {
        if (typeof CommonLoginUltra === 'undefined') return false;
        try {
            CommonLoginUltra.LoginSuccess = () => {
                console.log('CIA LoginSuccess callback fired');
                window.dispatchEvent(new CustomEvent('cia-login-success'));
            };

            // KEY FIX: $callHook passes (null, vueApp, userInfo) so we need the SECOND argument
            CommonLoginUltra.ReceivedUserInfo = (vueApp, userInfo) => {
                console.log('CIA ReceivedUserInfo app:', vueApp && vueApp.constructor && vueApp.constructor.name);
                console.log('CIA ReceivedUserInfo userInfo:', userInfo);
                
                const info = {};
                const src = userInfo || {};
                const keys = ['result','access_token','errorCode','errorMessage','code','name','email','mobile','phone','username','userId','user_id','bindId','headPicture','avatar','nickName','orgId','orgName'];
                for (const k of keys) {
                    if (src[k] !== undefined && (typeof src[k] === 'string' || typeof src[k] === 'number' || typeof src[k] === 'boolean')) {
                        info[k] = src[k];
                    }
                }
                // Also check nested value/data
                const nested = src.value || src.data || {};
                for (const k of keys) {
                    if (info[k] === undefined && nested[k] !== undefined && (typeof nested[k] === 'string' || typeof nested[k] === 'number' || typeof nested[k] === 'boolean')) {
                        info[k] = nested[k];
                    }
                }
                
                console.log('CIA ReceivedUserInfo extracted:', JSON.stringify(info));
                window.dispatchEvent(new CustomEvent('cia-received-user-info', { detail: info }));
            };

            new CommonLoginUltra({
                logoutBeforeInit: true,
                themeColorLogin: "linear-gradient(123deg, rgb(97, 73, 223) 0%, rgb(95, 26, 164) 100%)",
                loginTitle: "AI Data Agent",
                loginModule: ["mobile", "account", "wx", "qq", "workWx"],
                loginDefault: "account",
                fixed: true,
                closeIcon: true,
                needUserInfo: true,
            });
            return true;
        } catch (e) {
            console.error('CIA initLoginBox error:', e);
            return false;
        }
    },

    showLoginBox() {
        return this.initLoginBox();
    }
};

window.CIAModule = CIAModule;
