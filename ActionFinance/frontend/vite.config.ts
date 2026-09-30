import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const backend = process.env.ACTIONFINANCE_BACKEND_ORIGIN ?? "http://127.0.0.1:8091";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: Number(process.env.ACTIONFINANCE_FRONTEND_PORT ?? 5179),
    strictPort: true,
    proxy: {
      "/api": backend,
    },
  },
  preview: {
    host: "127.0.0.1",
    port: 4179,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
    exclude: ["node_modules/**", "node_modules.broken*/**", "dist/**"],
  },
});
