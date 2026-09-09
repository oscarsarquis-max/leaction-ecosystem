/**
 * Evidências visuais SPIDER-DEMO-001 — Contextual Link.
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
const API = process.env.SPIDER_API_URL || "http://127.0.0.1:8080";

async function waitHealthy(url, attempts = 60) {
  for (let index = 0; index < attempts; index += 1) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      // stack ainda iniciando
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Serviço indisponível: ${url}`);
}

async function main() {
  await waitHealthy(`${API}/actuator/health`);
  await waitHealthy(`${API}/demo/partner/agro-hoje`);
  await waitHealthy(UI);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();

  await page.goto(`${API}/demo/partner/agro-hoje`, { waitUntil: "networkidle" });
  await page.getByTestId("partner-article").waitFor();
  await page.screenshot({
    path: path.join(outDir, "DEMO-001-partner-news-page.png"),
    fullPage: true,
  });

  await page.locator('[data-testid="demo-link-proof"] details').evaluate((el) => {
    el.open = true;
  });
  await page.screenshot({
    path: path.join(outDir, "DEMO-001-generic-link-proof.png"),
    fullPage: true,
  });

  await Promise.all([
    page.waitForURL(/\/spiderbank\/entry\?ctx=ctx-/),
    page.getByTestId("spiderbank-cta").click(),
  ]);
  await page.getByTestId("spiderbank-entry").waitFor();
  await page.getByTestId("context-id").waitFor();
  await page.screenshot({
    path: path.join(outDir, "DEMO-001-spiderbank-entry.png"),
    fullPage: true,
  });
  await page.screenshot({
    path: path.join(outDir, "DEMO-001-context-created.png"),
    fullPage: true,
  });

  await page.getByTestId("open-provenance").click();
  await page.getByTestId("provenance-panel").waitFor();
  await page.screenshot({
    path: path.join(outDir, "DEMO-001-context-provenance.png"),
    fullPage: true,
  });

  await page.goto(`${API}/demo/partner/agro-hoje`, { waitUntil: "networkidle" });
  await page.locator('[data-testid="demo-link-proof"] details').evaluate((el) => {
    el.open = true;
  });
  await Promise.all([
    page.waitForURL(/\/spiderbank\/entry\?ctx=ctx-/),
    page.getByTestId("cta-no-referrer").click(),
  ]);
  await page.getByTestId("context-status").waitFor();
  await page.screenshot({
    path: path.join(outDir, "DEMO-001-no-referrer-fallback.png"),
    fullPage: true,
  });

  await browser.close();
  console.log("DEMO-001 screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
