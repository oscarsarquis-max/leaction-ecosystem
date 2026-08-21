/**
 * Captura screenshots reais do console contra frontend+API locais.
 * Uso (a partir de frontend/): node scripts/capture-presentation-screenshots.mjs
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
      const r = await fetch("http://127.0.0.1:8080/v1/console/implementation");
      if (r.ok) return;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("API console/implementation não respondeu");
}

async function main() {
  await waitApi();
  const browser = await chromium.launch({ headless: true });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await desktop.newPage();
  await page.goto(UI, { waitUntil: "networkidle" });

  await page.getByRole("button", { name: "Implementação" }).click();
  await page.getByText("Cockpit da implementação").waitFor();
  await page.screenshot({
    path: path.join(outDir, "015-implementation-cockpit-desktop.png"),
    fullPage: true,
  });

  await page.getByRole("button", { name: "Apresentação" }).click();
  await page.getByText("Modo Apresentação").waitFor();
  await page.screenshot({
    path: path.join(outDir, "015-presentation-readiness-desktop.png"),
    fullPage: true,
  });

  await page.getByRole("button", { name: "Execuções" }).click();
  await page.waitForTimeout(800);
  const rows = page.locator("table tbody tr");
  if ((await rows.count()) === 0) {
    throw new Error("Nenhuma execução na lista — seed local-demo ausente");
  }
  await rows.first().locator("button.linkish").click();
  await page.getByText("Journey map").waitFor({ timeout: 10000 });
  await page.screenshot({
    path: path.join(outDir, "015-live-execution-desktop.png"),
    fullPage: true,
  });

  await desktop.close();

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mpage = await mobile.newPage();
  await mpage.goto(UI, { waitUntil: "networkidle" });
  await mpage.getByRole("button", { name: "Implementação" }).click();
  await mpage.getByText("Cockpit da implementação").waitFor();
  await mpage.screenshot({
    path: path.join(outDir, "015-implementation-cockpit-mobile.png"),
    fullPage: true,
  });
  await mobile.close();
  await browser.close();

  for (const f of [
    "015-implementation-cockpit-desktop.png",
    "015-presentation-readiness-desktop.png",
    "015-live-execution-desktop.png",
    "015-implementation-cockpit-mobile.png",
  ]) {
    const p = path.join(outDir, f);
    if (!fs.existsSync(p) || fs.statSync(p).size < 1000) {
      throw new Error(`Screenshot inválido: ${f}`);
    }
    console.log("OK", f, fs.statSync(p).size);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
