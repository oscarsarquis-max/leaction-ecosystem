import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { setTimeout as delay } from "node:timers/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const port = 5182;
const base = `http://127.0.0.1:${port}/`;
const running = [
  {
    eventId: "run-0",
    executionId: "sat-run",
    eventType: "SATELLITE_REQUEST_RECEIVED",
    source: "satellite-contract",
    category: "INTERACTION",
    occurredAt: "2026-10-02T12:00:00Z",
    outcome: "SUCCESS",
    metadata: { originSatellite: "actionfinance", aiUsage: "NOT_USED", reasonCode: "RUNNING" },
  },
];

function startPreview() {
  const child = spawn("npx", ["vite", "preview", "--host", "127.0.0.1", "--port", String(port), "--strictPort"], {
    cwd: root,
    stdio: ["ignore", "pipe", "pipe"],
    shell: true,
  });
  return child;
}

async function waitForServer(child) {
  let output = "";
  child.stdout.on("data", (chunk) => {
    output += String(chunk);
  });
  child.stderr.on("data", (chunk) => {
    output += String(chunk);
  });
  const started = Date.now();
  while (Date.now() - started < 20000) {
    if (/localhost:5182|127\.0\.0\.1:5182/.test(output)) return;
    try {
      const res = await fetch(base);
      if (res.ok || res.status === 404) return;
    } catch {
      /* still booting */
    }
    await delay(250);
  }
  throw new Error("vite preview did not start: " + output.slice(-400));
}

async function mockMonitor(page, state) {
  await page.route("**/v1/console/**", async (route) => {
    const url = route.request().url();
    state.requests.push({ at: new Date().toISOString(), url, visibility: await page.evaluate(() => document.visibilityState) });
    if (state.offline || state.failNext) {
      state.failNext = false;
      await route.abort("internetdisconnected");
      return;
    }
    if (url.includes("/monitor/events")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ available: true, items: running, availableScenarios: [] }),
      });
      return;
    }
    if (url.includes("/executions/sat-run/events")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: running }),
      });
      return;
    }
    if (url.includes("/monitor/simulation")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ signalHttpEnabled: false, satellites: [] }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [] }) });
  });
}

const preview = startPreview();
const report = { startedAt: new Date().toISOString(), steps: [] };
try {
  await waitForServer(preview);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const other = await context.newPage();
  const state = { requests: [], failNext: false, offline: false };
  await mockMonitor(page, state);
  await page.goto(base);
  await page.getByRole("button", { name: /ACTIONFINANCE|Interação de satélite/ }).click();
  await page.getByRole("heading", { name: "Percurso registrado" }).waitFor();
  report.steps.push({ name: "selected", at: new Date().toISOString(), selected: true });

  await other.goto("about:blank");
  await other.bringToFront();
  report.steps.push({ name: "other-tab", at: new Date().toISOString(), visibility: await page.evaluate(() => document.visibilityState) });
  await delay(800);
  await page.bringToFront();
  await delay(800);
  report.steps.push({
    name: "returned-tab",
    at: new Date().toISOString(),
    visibility: await page.evaluate(() => document.visibilityState),
    stillSelected: await page.getByRole("heading", { name: "Percurso registrado" }).isVisible(),
    live: await page.locator(".transaction-live-status").innerText(),
    requests: state.requests.length,
  });

  await page.evaluate(() => window.moveTo?.(0, 0));
  report.steps.push({ name: "restore", at: new Date().toISOString(), stillSelected: await page.getByRole("heading", { name: "Percurso registrado" }).isVisible() });

  const beforeOffline = state.requests.length;
  state.offline = true;
  await context.setOffline(true);
  await page.getByRole("button", { name: "Atualizar" }).click();
  await delay(800);
  const staleWhileOffline = await page.locator(".transaction-live-status").innerText();
  const emptyOffline = await page.getByText("Nenhuma transação neste recorte.").isVisible().catch(() => false);
  state.offline = false;
  await context.setOffline(false);
  await page.getByRole("button", { name: "Atualizar" }).click();
  await delay(1000);
  const afterOffline = await page.locator(".transaction-live-status").innerText();
  const empty = emptyOffline || await page.getByText("Nenhuma transação neste recorte.").isVisible().catch(() => false);
  report.steps.push({
    name: "offline-blip",
    at: new Date().toISOString(),
    beforeOffline,
    afterRequests: state.requests.length,
    staleWhileOffline,
    recovered: /Ao vivo/.test(afterOffline),
    live: afterOffline,
    falseEmpty: empty,
    stillSelected: await page.getByRole("heading", { name: "Percurso registrado" }).isVisible(),
  });

  await page.getByRole("button", { name: "Pausar" }).click();
  const pausedCalls = state.requests.length;
  await other.bringToFront();
  await delay(400);
  await page.bringToFront();
  await delay(800);
  report.steps.push({
    name: "pause-respected",
    at: new Date().toISOString(),
    paused: await page.getByText(/Pausado/).isVisible(),
    extraCalls: state.requests.length - pausedCalls,
  });

  if (!report.steps.find((step) => step.name === "returned-tab")?.stillSelected) {
    throw new Error("selected execution was lost after tab switch");
  }
  if (empty) throw new Error("transient network became a false empty list");
  if (!/Desatualizado/.test(staleWhileOffline || "")) {
    throw new Error("offline refresh did not mark the stream as stale");
  }
  if (!/Ao vivo/.test(afterOffline || "")) {
    throw new Error("stream did not recover after the browser network returned");
  }
  if (!report.steps.find((step) => step.name === "pause-respected")?.paused) {
    throw new Error("manual pause was not kept after focus return");
  }

  report.ok = true;
  report.finishedAt = new Date().toISOString();
  console.log(JSON.stringify(report, null, 2));
  await browser.close();
} catch (error) {
  report.ok = false;
  report.error = error.message;
  console.error(JSON.stringify(report, null, 2));
  process.exitCode = 1;
} finally {
  preview.kill("SIGTERM");
  const ended = Promise.race([
    once(preview, "exit"),
    delay(2000),
  ]);
  await ended.catch(() => {});
  try {
    preview.kill("SIGKILL");
  } catch {
    /* already gone */
  }
}
