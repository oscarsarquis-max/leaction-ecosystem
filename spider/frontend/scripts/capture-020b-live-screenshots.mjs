/**
 * Aceite visual 020B: Executar demonstração na Home → jornada automática.
 * Uso (frontend/): node scripts/capture-020b-live-screenshots.mjs
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
const API = "http://127.0.0.1:8080";

async function waitApi() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`${API}/actuator/health`);
      if (r.ok) return;
    } catch {
      /* retry */
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error("API local-demo indisponível em :8080");
}

async function main() {
  await waitApi();
  const browser = await chromium.launch({ headless: true });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await desktop.newPage();
  await page.goto(UI, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Home operacional" }).waitFor();
  await page.getByRole("button", { name: "Executar demonstração" }).click();

  const current = page.getByTestId("home-current-execution");
  await current.waitFor({ timeout: 15000 });
  const jsonDump = await page.getByText("Submetido. Resposta:").count();
  if (jsonDump > 0) {
    throw new Error("JSON bruto ainda é o feedback principal da Home");
  }
  await page.screenshot({
    path: path.join(outDir, "020B-live-execution-start.png"),
    fullPage: true,
  });

  const journey = page.getByTestId("execution-journey");
  await journey.waitFor({ timeout: 15000 });
  await page.getByText("Interaction #1").waitFor({ timeout: 15000 });
  await page.getByText("Retry").waitFor({ timeout: 15000 });
  await page.getByText("Interaction #2").waitFor({ timeout: 15000 });
  await page.locator('[data-testid="execution-journey"]').screenshot({
    path: path.join(outDir, "020B-live-execution-retry.png"),
  });

  await page
    .locator('[data-testid="journey-stage-completion"][data-state="SUCCEEDED"]')
    .waitFor({ timeout: 15000 });
  const failed = page.locator('[data-testid^="journey-stage-interaction-"][data-state="FAILED"]');
  await failed.first().waitFor();
  await page.screenshot({
    path: path.join(outDir, "020B-live-execution-complete.png"),
    fullPage: true,
  });

  const bodyText = await page.locator(".home-operational").innerText();
  if (!/Interaction #1/i.test(bodyText) || !/Retry/i.test(bodyText) || !/Interaction #2/i.test(bodyText)) {
    throw new Error("Jornada completa de retry não visível na Home");
  }
  if (!/SUCCEEDED/i.test(bodyText)) {
    throw new Error("Conclusão SUCCEEDED não visível na Home");
  }

  await browser.close();
  console.log("020B live screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
