import { copyFileSync, createReadStream, existsSync, mkdirSync, readdirSync, statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";

const frontendRoot = path.dirname(fileURLToPath(import.meta.url));
const imagesDir = path.resolve(frontendRoot, "images");
const OFFICIAL_LOGO_FILE = "lojadepaeslogo.png";

// Variáveis VITE_* do processo hospedeiro não podem substituir o .env desta app.
delete process.env.VITE_API_BASE_URL;
delete process.env.VITE_DEV_PORT;

function isServedImage(filename: string): boolean {
  if (filename === OFFICIAL_LOGO_FILE) {
    return true;
  }
  return filename.startsWith("internal") && filename.toLowerCase().endsWith(".png");
}

function localImages(): Plugin {
  return {
    name: "lojadepaes-images",
    configureServer(server) {
      server.middlewares.use("/images", (req, res, next) => {
        const relative = decodeURIComponent((req.url ?? "").split("?")[0] ?? "").replace(/^\/+/, "");
        if (relative.includes("..") || !isServedImage(relative)) {
          next();
          return;
        }
        const file = path.resolve(imagesDir, relative);
        if (!file.startsWith(imagesDir) || !existsSync(file) || statSync(file).isDirectory()) {
          next();
          return;
        }
        res.setHeader("Content-Type", "image/png");
        createReadStream(file).pipe(res);
      });
    },
    writeBundle(options) {
      const destDir = path.resolve(options.dir ?? path.join(frontendRoot, "dist"), "images");
      mkdirSync(destDir, { recursive: true });
      for (const filename of readdirSync(imagesDir)) {
        if (!isServedImage(filename)) {
          continue;
        }
        copyFileSync(path.join(imagesDir, filename), path.join(destDir, filename));
      }
    },
  };
}

export default defineConfig({
  envDir: frontendRoot,
  plugins: [react(), localImages()],
  server: {
    port: 5175,
    host: "127.0.0.1",
    proxy: {
      "/api": "http://127.0.0.1:5075",
    },
  },
  preview: {
    port: 5175,
    host: "127.0.0.1",
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test-setup.ts",
  },
});
