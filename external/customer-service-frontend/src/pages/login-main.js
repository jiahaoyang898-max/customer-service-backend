// 登录 / 注册页入口
// 独立的多页面入口，不改动原有 index.html 与 App.vue
import { createApp } from 'vue'
import LoginApp from './LoginApp.vue'

createApp(LoginApp).mount('#app')
