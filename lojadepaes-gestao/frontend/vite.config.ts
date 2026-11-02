import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  envDir: frontendRoot,
  plugins: [react()],
  server: {
    port: 5185,
    host: "127.0.0.1",
    fs: { allow: [frontendRoot] },
    proxy: {
      "/api": "http://127.0.0.1:8090",
    },
  },
  preview: {
    port: 5185,
    host: "127.0.0.1",
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test-setup.ts",
  },
});
