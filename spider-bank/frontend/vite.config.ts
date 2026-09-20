import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: Number(process.env['VITE_DEV_PORT'] ?? 5190),
    strictPort: true,
    proxy: {
      '/api': {
        target: process.env['SPIDERBANK_BFF_URL'] ?? 'http://127.0.0.1:8090',
        changeOrigin: false,
      },
    },
  },
  preview: {
    host: '127.0.0.1',
    port: 4190,
    strictPort: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
