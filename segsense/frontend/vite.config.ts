import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  envDir: path.resolve(frontendRoot, '..'),
  appType: 'spa',
  server: {
    host: '127.0.0.1',
    port: Number(process.env['VITE_DEV_PORT'] ?? 5178),
    strictPort: true,
  },
  preview: {
    host: '127.0.0.1',
    port: 4178,
    strictPort: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
});
