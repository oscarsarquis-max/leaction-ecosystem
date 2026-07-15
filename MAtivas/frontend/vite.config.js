import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  css: {
    postcss: './postcss.config.js',
  },
  server: {
    // 5173 fica com o Chamelleon neste host; MAtivas usa 5174.
    port: 5174,
    strictPort: true,
    host: true,
  },
})
