import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy alinhado ao backend local (FLASK_PORT no backend/.env — tipicamente 5011).
const apiTarget =
  process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:5011'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5174,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/inovador': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
