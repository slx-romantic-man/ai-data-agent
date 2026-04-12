const { createApp } = Vue;

const App = {
    template: window.AppTemplate,
    setup: window.AppSetup()
};

createApp(App).mount('#app');
