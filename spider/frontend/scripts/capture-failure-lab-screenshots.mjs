/**
 * Captura screenshots do Failure Lab (PROMPT-018).
 * Pré-requisito: .\scripts\start-presentation.ps1 com o perfil local-demo
 * (spider.failure-lab.enabled + spider.failure-lab.http.enabled).
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
const SCENARIO = process.env.SPIDER_FAILURE_LAB_SCENARIO || "RETRY_THEN_SUCCESS";

const FILES = [
  "018-failure-lab-catalog-desktop.png",
  "018-failure-lab-running-desktop.png",
  "018-failure-lab-verified-desktop.png",
  "018-failure-lab-runbook-evidence-desktop.png",
  "018-failure-lab-mobile.png",
];

async function waitApi() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch(`${API}/v1/console/failure-lab/scenarios`);
      if (r.ok || r.status === 401 || r.status === 403 || r.status === 404) return r.status;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("API failure-lab/scenarios não respondeu");
}

async function openLab(page) {
  await page.goto(UI, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Failure Lab" }).click();
  await page.getByTestId("failure-lab").waitFor({ timeout: 15000 });
  await page.getByTestId("failure-lab-boundary-banner").waitFor();
}

async function shot(page, file) {
  await page.screenshot({ path: path.join(outDir, file), fullPage: true });
}

async function main() {
  const status = await waitApi();
  if (status === 404) {
    throw new Error("failure-lab retornou 404 — verifique as flags local-demo");
  }

  const browser = await chromium.launch({ headless: true });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await desktop.newPage();
  await openLab(page);
  await page.getByTestId(`failure-lab-scenario-${SCENARIO}`).waitFor({ timeout: 15000 });
  await page.waitForTimeout(600);
  await shot(page, FILES[0]);

  await page.getByTestId(`failure-lab-select-${SCENARIO}`).click();
  await page.getByTestId("failure-lab-confirmation").waitFor();
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Executar cenário" }).click();

  const runStatus = page.getByTestId("failure-lab-run-status");
  await runStatus.waitFor({ timeout: 30000 });
  const early = (await runStatus.textContent()) || "";
  if (/REQUESTED|RUNNING|OBSERVING/.test(early)) {
    await shot(page, FILES[1]);
  }

  await page.waitForFunction(
    () => {
      const node = document.querySelector('[data-testid="failure-lab-run-status"]');
      return node ? /VERIFIED|FAILED|TIMED_OUT|INCONCLUSIVE/.test(node.textContent || "") : false;
    },
    undefined,
    { timeout: 180000 },
  );
  await page.waitForTimeout(800);
  await shot(page, FILES[2]);

  // Fallback: sem janela observável de execução, o estado terminal documenta o passo "running".
  if (!fs.existsSync(path.join(outDir, FILES[1]))) {
    await shot(page, FILES[1]);
  }

  await page.getByTestId("failure-lab-runbook").waitFor({ timeout: 15000 });
  await page
    .getByTestId("failure-lab-evidence")
    .waitFor({ timeout: 20000 })
    .catch(() => console.warn("evidência não exibida — capturando apenas runbook"));
  await page.getByTestId("failure-lab-runbook").scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  await shot(page, FILES[3]);
  await desktop.close();

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mpage = await mobile.newPage();
  await openLab(mpage);
  await mpage.waitForTimeout(800);
  await shot(mpage, FILES[4]);
  await mobile.close();
  await browser.close();

  for (const f of FILES) {
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
