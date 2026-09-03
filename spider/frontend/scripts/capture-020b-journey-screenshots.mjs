/**
 * Capturas 020B — jornada visual e navegação agrupada.
 * Uso (a partir de frontend/): node scripts/capture-020b-journey-screenshots.mjs
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
const CREDENTIAL = "local-demo-console";

function headers(extra = {}) {
  return {
    "X-Spider-Credential-Ref": CREDENTIAL,
    Accept: "application/json",
    ...extra,
  };
}

async function waitApi() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`${API}/v1/canonical/executions`, { headers: headers() });
      if (r.ok) return;
    } catch {
      /* retry */
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  throw new Error("API local-demo indisponível");
}

async function submit(operation, mockScenario) {
  const executionId = `exec-020b-${operation.toLowerCase()}-${Date.now()}`;
  const body = {
    contract: { schemaVersion: "1.0", contractVersion: "1.0.0" },
    execution: {
      executionId,
      requestedAt: new Date().toISOString(),
      idempotencyKey: `idem-020b-${executionId}`,
    },
    contextRef: {
      contextId: `ctx-${operation}`,
      intentId: "intent:demo",
      capabilityId: "capability:mock",
      productServiceId: "product:mock",
      journeyId: "journey:mock",
    },
    origin: {
      channel: "operational-console",
      originatorId: "console-local-demo",
      interactionRef: `corr-${executionId}`,
    },
    trace: {
      correlationId: `corr-${executionId}`,
      traceparent: "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
    },
    target: { capability: "mock", operation },
    payload: { canonicalData: { mockScenario: mockScenario || operation } },
  };
  const res = await fetch(`${API}/v1/canonical/executions`, {
    method: "POST",
    headers: headers({ "Content-Type": "application/json", "Idempotency-Key": body.execution.idempotencyKey }),
    body: JSON.stringify(body),
  });
  const payload = await res.json().catch(() => ({}));
  const id =
    payload.execution?.executionId ||
    payload.executionId ||
    (payload.execution && payload.execution.executionId) ||
    executionId;
  if (!id) {
    throw new Error(`POST ${operation} -> ${res.status} ${JSON.stringify(payload).slice(0, 300)}`);
  }
  return id;
}

async function screenshotJourney(page, testIdPath, file) {
  await page.getByTestId("execution-journey").waitFor();
  await page.locator('[data-testid="execution-journey"]').screenshot({
    path: path.join(outDir, file),
  });
}

async function openHomeExecution(page, executionId) {
  await page.getByRole("button", { name: "Home" }).click();
  await page.getByRole("heading", { name: "Home operacional" }).waitFor();
  const cell = page.locator(`td[title="${executionId}"]`);
  try {
    await cell.waitFor({ timeout: 8000 });
    await cell.locator("xpath=ancestor::tr").getByRole("button", { name: "Abrir" }).click();
  } catch {
    await page.getByRole("button", { name: "Execuções" }).click();
    await page.getByRole("heading", { name: "Execuções" }).waitFor();
    const suffix = executionId.length > 8 ? executionId.slice(-4) : executionId;
    await page.getByRole("button", { name: new RegExp(suffix) }).first().click();
  }
  await page.getByTestId("execution-journey").waitFor();
}

async function main() {
  await waitApi();
  const failId = await submit("TECHNICAL_TERMINAL_FAILURE", "INVALID_RESPONSE");
  let waitId = null;
  try {
    waitId = await submit("WAIT_AND_RESUME", "ACCEPTED_ASYNC");
  } catch {
    waitId = null;
  }

  const browser = await chromium.launch({ headless: true });
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await desktop.newPage();
  await page.goto(UI, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Home operacional" }).waitFor();
  await page.locator(".console-nav-grouped").screenshot({
    path: path.join(outDir, "020B-navegacao-console.png"),
  });

  await openHomeExecution(page, "demo-retry-001");
  await page.screenshot({ path: path.join(outDir, "020B-home-jornada.png"), fullPage: true });
  await screenshotJourney(page, null, "020B-jornada-retry.png");

  await page.getByRole("button", { name: "Ver detalhe técnico" }).click();
  await page.getByRole("heading", { name: "O que aconteceu?" }).waitFor();
  await page.screenshot({ path: path.join(outDir, "020B-detalhe-execucao.png"), fullPage: true });

  await openHomeExecution(page, failId);
  await page.getByTestId("journey-stage-completion").waitFor();
  await screenshotJourney(page, null, "020B-jornada-failure.png");

  if (waitId) {
    await openHomeExecution(page, waitId);
    await screenshotJourney(page, null, "020B-jornada-wait-resume.png");
  }

  await browser.close();
  console.log("020B screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
