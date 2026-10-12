import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],

  // 多页面入口：工作台首页(index.html) + 登录注册页(login.html)
  // 仅在构建配置中追加 login 入口，原有页面与业务代码不受影响
  build: {
    rollupOptions: {
      input: {
        index: 'index.html',
        login: 'login.html',
      },
    },
  },

  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:18082',
        changeOrigin: true,
      },
      '/commerce': {
        target: 'http://127.0.0.1:18081',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/commerce/, ''),
      },
      '/health': {
        target: 'http://127.0.0.1:18082',
        changeOrigin: true,
      },
    },
  },
})
