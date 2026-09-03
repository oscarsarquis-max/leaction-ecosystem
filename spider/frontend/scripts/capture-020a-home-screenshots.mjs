/**
 * Capturas 020A da Home operacional contra UI+API locais.
 * Uso (a partir de frontend/): node scripts/capture-020a-home-screenshots.mjs
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..", "..");
const outDir = path.join(root, "docs", "technical", "screenshots");
fs.mkdirSync(outDir, { recursive: true });

const UI = process.env.SPIDER_UI_URL || "http://127.0.0.1:5180";

async function waitApi() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch("http://127.0.0.1:8080/v1/canonical/executions", {
        headers: { "X-Spider-Credential-Ref": "local-demo-console" },
      });
      if (r.ok) return;
    } catch {
      /* retry */
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error("GET /v1/canonical/executions não respondeu 2xx com credencial local-demo");
}

async function main() {
  await waitApi();
  const browser = await chromium.launch({ headless: true });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await desktop.newPage();
  await page.goto(UI, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Home operacional" }).waitFor();
  await page.getByText("Spider 0.20.0").waitFor();
  await page.getByRole("heading", { name: "Últimas execuções" }).waitFor();

  await page.screenshot({
    path: path.join(outDir, "020A-home-operacional.png"),
    fullPage: true,
  });

  const recent = page.locator("article").filter({ has: page.getByRole("heading", { name: "Últimas execuções" }) });
  await recent.screenshot({ path: path.join(outDir, "020A-home-execucoes.png") });

  const status = page.locator("article.home-status");
  await status.screenshot({ path: path.join(outDir, "020A-home-status.png") });

  await browser.close();
  console.log("020A screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
