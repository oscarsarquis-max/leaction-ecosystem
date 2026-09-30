/**
 * Validação visual do Monitor publicado no sandbox AWS.
 * node scripts/capture-sandbox-monitor-fix.mjs
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..", "..");
const outDir = path.join(root, "docs", "operations", "screenshots", "sandbox-monitor-fix-20260928");
fs.mkdirSync(outDir, { recursive: true });

const UI = process.env.SPIDER_UI_URL || "https://monitor.spider.actionhub.com.br";
const API = process.env.SPIDER_API_URL || "https://api.spider.actionhub.com.br";
const CREDENTIAL = "sandbox-operator";
const EXECUTION_ID = process.env.SPIDER_EXECUTION_ID || "exec-sandbox-demo-20260928-r3";

async function shot(page, name) {
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage: true });
  console.log("wrote", file);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(String(error)));

  await page.goto(`${UI}/?nocache=${Date.now()}`, { waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("heading", { name: "Monitor de transações" }).waitFor({ timeout: 30000 });
  await page.getByText(/Ao vivo/).waitFor({ timeout: 30000 });

  const row = page.getByTitle(EXECUTION_ID);
  await row.waitFor({ timeout: 30000 });
  await row.click();
  await page.getByRole("heading", { name: "Transação selecionada" }).waitFor({ timeout: 30000 });
  await page.getByRole("button", { name: /Etapa 1 · tentativa 1/ }).waitFor({ timeout: 30000 });

  const bodyText = await page.locator("body").innerText();
  if (/Unexpected orchestration error/i.test(bodyText)) {
    throw new Error("banner Unexpected orchestration error still visible");
  }
  if ((bodyText.match(/Interaction #1/g) || []).length >= 2) {
    throw new Error("duplicate Interaction #1 titles still visible");
  }
  if (!/Etapa 1 · tentativa 1/.test(bodyText) || !/Etapa 2 · tentativa 1/.test(bodyText)) {
    throw new Error("expected distinct step titles were not found");
  }

  await shot(page, "01-fluxo-transacao.png");
  await page.locator('[data-testid="execution-journey"]').screenshot({
    path: path.join(outDir, "02-percurso-completo.png"),
  });

  await page.getByRole("button", { name: /Etapa 1 · tentativa 1/ }).click();
  await page.getByTestId("journey-step-detail").getByText("step-1").waitFor();
  await shot(page, "03-passo-1-aberto.png");

  await page.getByRole("button", { name: /Etapa 2 · tentativa 1/ }).click();
  await page.getByTestId("journey-step-detail").getByText("step-2").waitFor();
  await shot(page, "04-passo-2-aberto.png");

  await page.getByText(/Eventos relacionados/).click();
  const relatedError = await page.locator('[data-testid="related-events-error"]').count();
  if (relatedError) {
    throw new Error("related events section showed an unexpected error");
  }
  await shot(page, "05-eventos-relacionados.png");

  await page.waitForTimeout(5000);
  const afterPoll = await page.locator("body").innerText();
  if (/Unexpected orchestration error/i.test(afterPoll)) {
    throw new Error("banner reappeared after polling");
  }
  await page.getByRole("button", { name: /Etapa 2 · tentativa 1/ }).waitFor();
  await shot(page, "06-apos-polling-sem-banner.png");

  await browser.close();

  const ctx = await fetch(`${API}/v1/context/executions/${encodeURIComponent(EXECUTION_ID)}`, {
    headers: { Accept: "application/json", "X-Spider-Credential-Ref": CREDENTIAL },
  });
  if (ctx.status !== 404) {
    throw new Error(`context lookup expected 404, got ${ctx.status}`);
  }
  const problem = await ctx.json();
  if (problem.title === "Unexpected orchestration error") {
    throw new Error("context lookup still returns orchestration error title");
  }

  if (pageErrors.length) {
    throw new Error("javascript errors: " + pageErrors.join(" | "));
  }
  console.log("visual validation passed", { executionId: EXECUTION_ID, outDir });
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
