/// <reference types="vitest/config" />
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const apiTarget = process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8008";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(rootDir, "src"),
      "@qmind/api-client": path.resolve(rootDir, "../packages/api-client/src/index.ts"),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5178,
    strictPort: true,
    proxy: {
      "/api": { target: apiTarget, changeOrigin: true },
      "/health": { target: apiTarget, changeOrigin: true },
      "/ready": { target: apiTarget, changeOrigin: true },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: false,
  },
});
