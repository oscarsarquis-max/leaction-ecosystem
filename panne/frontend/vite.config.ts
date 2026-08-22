import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  if (mode === "production" && env.VITE_AUTH_PROVIDER === "fake") {
    throw new Error("O provedor falso de autenticação não pode ser usado em produção.");
  }
  return {
    plugins: [react()],
    server: {
      port: 5180,
      host: "127.0.0.1",
      proxy: {
        "/health": "http://127.0.0.1:5080",
        "/ready": "http://127.0.0.1:5080",
        "/api": "http://127.0.0.1:5080",
        "/openapi.json": "http://127.0.0.1:5080",
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: "./src/test-setup.ts",
    },
  };
});
