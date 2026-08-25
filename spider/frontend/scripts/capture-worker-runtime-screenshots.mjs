/**
 * Captura screenshots do Runtime de Workers (PROMPT-019).
 * Pré-requisito: .\scripts\start-presentation.ps1 com o perfil local-demo
 * (spider.worker-runtime.enabled + spider.worker-runtime.http.enabled).
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

const FILES = {
  overview: "019-worker-runtime-overview-desktop.png",
  backlog: "019-worker-runtime-backlog-desktop.png",
  draining: "019-worker-runtime-draining-desktop.png",
  stale: "019-worker-runtime-stale-recovery-desktop.png",
  mobile: "019-worker-runtime-mobile.png",
};

async function waitApi() {
  for (let i = 0; i < 90; i++) {
    try {
      const r = await fetch(`${API}/v1/console/runtime`);
      if (r.ok) return r.status;
      if (r.status === 404) {
        console.warn("runtime respondeu 404 — verifique as flags local-demo; tentando novamente");
      }
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
  throw new Error("API /v1/console/runtime não respondeu 200 — verifique as flags local-demo");
}

async function openRuntime(page) {
  await page.goto(UI, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Runtime de Workers" }).click();
  await page.getByTestId("worker-runtime").waitFor({ timeout: 15000 });
  await page.getByTestId("worker-runtime-boundary-banner").waitFor();
}

async function shot(page, file) {
  await page.screenshot({ path: path.join(outDir, file), fullPage: true });
}

async function captureDraining(page) {
  const drainButtons = page.locator(
    'button[data-testid^="worker-runtime-drain-"]:not([data-testid*="confirm"])',
  );
  if ((await drainButtons.count()) === 0) {
    console.warn("nenhum worker elegível a drenagem — capturando o estado atual do runtime");
    return false;
  }
  await drainButtons.first().click();
  await page.getByTestId("worker-runtime-drain-confirmation").waitFor({ timeout: 10000 });
  await page.waitForTimeout(400);
  const confirm = page.locator('[data-testid^="worker-runtime-drain-confirm-"]').first();
  if ((await confirm.count()) === 0) return false;
  await confirm.click();
  await page
    .getByTestId("worker-runtime-drain-message")
    .waitFor({ timeout: 20000 })
    .catch(() => console.warn("sem retorno visível da drenagem — capturando o estado atual"));
  await page.waitForTimeout(800);
  return true;
}

async function main() {
  await waitApi();

  const browser = await chromium.launch({ headless: true });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await desktop.newPage();

  await openRuntime(page);
  await page.getByTestId("worker-runtime-summary").waitFor({ timeout: 15000 });
  await page.waitForTimeout(600);
  await shot(page, FILES.overview);

  // Backlog: mesma leitura real, seção de backlog em foco.
  const backlogs = page.getByTestId("worker-runtime-backlogs");
  if ((await backlogs.count()) > 0) {
    await backlogs.scrollIntoViewIfNeeded();
  }
  await page.waitForTimeout(500);
  await shot(page, FILES.backlog);

  // Recuperação/stale: resumo com staleWorkers e leases expirados em foco.
  await page.getByTestId("worker-runtime-summary").scrollIntoViewIfNeeded();
  const schedules = page.getByTestId("worker-runtime-schedules");
  if ((await schedules.count()) > 0) {
    await schedules.scrollIntoViewIfNeeded();
  }
  await page.waitForTimeout(500);
  await shot(page, FILES.stale);

  await page.getByTestId("worker-runtime").scrollIntoViewIfNeeded();
  await captureDraining(page);
  await shot(page, FILES.draining);
  await desktop.close();

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mpage = await mobile.newPage();
  await openRuntime(mpage);
  await mpage.waitForTimeout(800);
  await shot(mpage, FILES.mobile);
  await mobile.close();
  await browser.close();

  for (const file of Object.values(FILES)) {
    const target = path.join(outDir, file);
    if (!fs.existsSync(target) || fs.statSync(target).size < 1000) {
      throw new Error(`Screenshot inválido: ${file}`);
    }
    console.log("ok", file, fs.statSync(target).size);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
