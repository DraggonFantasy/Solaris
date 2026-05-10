import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const host = process.env.VITE_HOST || '127.0.0.1'
const port = Number(process.env.VITE_PORT || 5173)
const backendTarget = process.env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  server: {
    host,
    port,
    strictPort: true,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/admin': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/static': {
        target: backendTarget,
        changeOrigin: true,
      },
      '/media': {
        target: backendTarget,
        changeOrigin: true,
      },
    }
  }
})
