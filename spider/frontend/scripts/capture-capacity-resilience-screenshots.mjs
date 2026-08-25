/**
 * Captura screenshots de Capacidade & Resiliência (PROMPT-020).
 * Pré-requisito: .\scripts\start-presentation.ps1 com o perfil local-demo
 * (spider.capacity.enabled + spider.capacity.http.enabled).
 *
 * Todas as telas usam dados reais da API: os estados de disjuntor aberto e de descarte de carga
 * vêm dos cenários de capacidade do Failure Lab, que operam em escopos dedicados de laboratório.
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
const CREDENTIAL = process.env.SPIDER_CONSOLE_CREDENTIAL || "local-demo-console";

const FILES = {
  overview: "020-capacity-overview-desktop.png",
  pressure: "020-capacity-pressure-desktop.png",
  circuitOpen: "020-capacity-circuit-open-desktop.png",
  loadShedding: "020-capacity-load-shedding-desktop.png",
  mobile: "020-capacity-mobile.png",
};

async function waitApi() {
  for (let attempt = 0; attempt < 90; attempt++) {
    try {
      const res = await fetch(`${API}/v1/console/capacity`, {
        headers: { "X-Spider-Credential-Ref": CREDENTIAL },
      });
      if (res.ok) return await res.json();
      if (res.status === 404) {
        console.warn("capacity respondeu 404 — verifique as flags local-demo; tentando novamente");
      }
    } catch {
      /* retry */
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error("API /v1/console/capacity não respondeu 200 — verifique as flags local-demo");
}

/** Dispara um cenário de capacidade do Failure Lab e aguarda o desfecho. */
async function runLabScenario(scenarioCode) {
  try {
    const started = await fetch(`${API}/v1/console/failure-lab/runs`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, application/problem+json",
        "X-Spider-Credential-Ref": CREDENTIAL,
      },
      body: JSON.stringify({ scenarioCode, parameters: {} }),
    });
    if (!started.ok) {
      console.warn(`cenário ${scenarioCode} indisponível (HTTP ${started.status})`);
      return false;
    }
    const run = await started.json();
    if (!run?.labRunId) return true;
    for (let attempt = 0; attempt < 40; attempt++) {
      const res = await fetch(
        `${API}/v1/console/failure-lab/runs/${encodeURIComponent(run.labRunId)}`,
        { headers: { "X-Spider-Credential-Ref": CREDENTIAL } },
      );
      if (!res.ok) break;
      const current = await res.json();
      const status = String(current?.status || "").toUpperCase();
      if (status && status !== "RUNNING" && status !== "PENDING" && status !== "STARTED") {
        return true;
      }
      await new Promise((resolve) => setTimeout(resolve, 750));
    }
    return true;
  } catch (failure) {
    console.warn(`falha ao executar ${scenarioCode}: ${failure.message}`);
    return false;
  }
}

async function openCapacity(page) {
  await page.goto(UI, { waitUntil: "networkidle" });
  await page.getByRole("button", { name: "Capacidade & Resiliência" }).click();
  await page.getByTestId("capacity-resilience").waitFor({ timeout: 15000 });
  await page.getByTestId("capacity-boundary-banner").waitFor();
}

async function refreshCapacity(page) {
  await page.getByTestId("capacity-refresh").click();
  await page.getByTestId("capacity-executive").waitFor({ timeout: 15000 });
  await page.waitForTimeout(600);
}

async function setSection(page, id, shouldOpen) {
  const toggle = page.getByTestId(`capacity-toggle-${id}`);
  if ((await toggle.count()) === 0) return;
  const expanded = (await toggle.getAttribute("aria-expanded")) === "true";
  if (expanded !== shouldOpen) {
    await toggle.click();
    await page.waitForTimeout(250);
  }
}

async function shot(page, file) {
  await page.screenshot({ path: path.join(outDir, file), fullPage: true });
}

async function main() {
  const snapshot = await waitApi();
  console.log("capacity mode:", snapshot?.mode, "· escopos:", (snapshot?.pressure || []).length);

  const browser = await chromium.launch({ headless: true });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await desktop.newPage();

  await openCapacity(page);
  await page.getByTestId("capacity-executive").waitFor({ timeout: 15000 });

  // Visão executiva: modo, pressão consolidada e momento do cálculo.
  await setSection(page, "pressure", false);
  await page.waitForTimeout(500);
  await shot(page, FILES.overview);

  // Pressão por escopo: ocupação, fila pendente, cota e frescor da observação.
  await setSection(page, "pressure", true);
  await page.getByTestId("capacity-pressure").waitFor({ timeout: 10000 }).catch(() => {
    console.warn("nenhum escopo publicado — capturando a seção de pressão vazia");
  });
  await page.waitForTimeout(500);
  await shot(page, FILES.pressure);

  // Disjuntor aberto: estado real produzido pelo cenário de capacidade do Failure Lab.
  const circuitRan = await runLabScenario("CAPACITY_CIRCUIT_OPEN_RECOVER");
  if (!circuitRan) {
    console.warn("cenário de disjuntor indisponível — capturando o estado corrente dos disjuntores");
  }
  await refreshCapacity(page);
  await setSection(page, "pressure", false);
  await setSection(page, "resilience", true);
  const circuits = page.getByTestId("capacity-circuits");
  if ((await circuits.count()) > 0) {
    await circuits.scrollIntoViewIfNeeded();
  } else {
    console.warn("nenhum disjuntor registrado nesta leitura");
  }
  await page.waitForTimeout(500);
  await shot(page, FILES.circuitOpen);

  // Descarte de carga: decisões reais de cota e limite rígido de fila.
  await runLabScenario("CAPACITY_QUOTA_EXHAUSTION");
  await runLabScenario("CAPACITY_LOAD_SHEDDING");
  await runLabScenario("CAPACITY_BACKLOG_HARD_LIMIT");
  await refreshCapacity(page);
  await setSection(page, "resilience", false);
  await setSection(page, "shedding", true);
  await page.getByTestId("capacity-load-decisions").click();
  await page.waitForTimeout(900);
  const decisions = page.getByTestId("capacity-decisions");
  if ((await decisions.count()) > 0) {
    await decisions.scrollIntoViewIfNeeded();
  } else {
    console.warn("nenhuma decisão de admissão registrada nesta leitura");
  }
  await page.waitForTimeout(500);
  await shot(page, FILES.loadShedding);
  await desktop.close();

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const mpage = await mobile.newPage();
  await openCapacity(mpage);
  await setSection(mpage, "pressure", true);
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

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
