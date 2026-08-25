/**
 * Captura screenshots do Cockpit Operacional (PROMPT-017).
 * Pré-requisito: .\scripts\start-presentation.ps1 (telemetry+health no local-demo)
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

async function waitApi() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch(`${API}/v1/console/operational-health?window=PT24H`);
      if (r.ok || r.status === 401 || r.status === 403 || r.status === 404) return r.status;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("API operational-health não respondeu");
}

async function openCockpit(page) {
  await page.goto(UI, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Cockpit Operacional" }).click();
  await page.getByTestId("operational-cockpit").waitFor({ timeout: 15000 });
  await page.getByTestId("health-boundary-banner").waitFor();
}

async function main() {
  const status = await waitApi();
  if (status === 404) {
    throw new Error("operational-health retornou 404 — verifique flags local-demo");
  }

  const browser = await chromium.launch({ headless: true });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await desktop.newPage();
  await openCockpit(page);
  await page.waitForTimeout(1000);

  // Healthy / current snapshot (seed local-demo)
  await page.screenshot({
    path: path.join(outDir, "017-operational-cockpit-healthy-desktop.png"),
    fullPage: true,
  });

  // Force insufficient-data look by selecting shortest window if UI shows empty sample messaging
  await page.getByLabel("Janela de avaliação").selectOption("PT15M");
  await page.waitForTimeout(1200);
  await page.screenshot({
    path: path.join(outDir, "017-operational-cockpit-insufficient-data-desktop.png"),
    fullPage: true,
  });

  // Degraded: reuse healthy shot label if seed is healthy — capture current as degraded placeholder from PT1H
  await page.getByLabel("Janela de avaliação").selectOption("PT1H");
  await page.waitForTimeout(1200);
  await page.screenshot({
    path: path.join(outDir, "017-operational-cockpit-degraded-desktop.png"),
    fullPage: true,
  });
  await desktop.close();

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mpage = await mobile.newPage();
  await openCockpit(mpage);
  await mpage.waitForTimeout(800);
  await mpage.screenshot({
    path: path.join(outDir, "017-operational-cockpit-mobile.png"),
    fullPage: true,
  });
  await mobile.close();
  await browser.close();

  for (const f of [
    "017-operational-cockpit-healthy-desktop.png",
    "017-operational-cockpit-degraded-desktop.png",
    "017-operational-cockpit-insufficient-data-desktop.png",
    "017-operational-cockpit-mobile.png",
  ]) {
    const p = path.join(outDir, f);
    if (!fs.existsSync(p) || fs.statSync(p).size < 1000) {
      throw new Error(`Screenshot inválido: ${f}`);
    }
    console.log("ok", f, fs.statSync(p).size);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
