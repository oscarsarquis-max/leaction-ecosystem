import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

function campoAbertoStaticPage() {
  return {
    name: "campoaberto-static-page",
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const url = (req.url || "").split("?")[0];
        if (url === "/partner/agro-hoje" || url === "/partner/agro-hoje/") {
          req.url = "/partner/agro-hoje/index.html";
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), campoAbertoStaticPage()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
  },
  server: {
    host: "127.0.0.1",
    port: 5180,
    proxy: {
      "/v1": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
      },
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
      },
      "/actuator": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
      },
      "/originador": {
        target: "http://127.0.0.1:8081",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/originador/, ""),
      },
    },
  },
});
