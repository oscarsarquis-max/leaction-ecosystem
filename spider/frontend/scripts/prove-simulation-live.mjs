import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const dir = "test-results/simulation-live";
mkdirSync(dir, { recursive: true });

const scenarios = [
  { id: "SUCCESS_MULTI_STEP", label: "Sucesso em múltiplas etapas", twoPhase: false },
  { id: "RETRY_THEN_SUCCESS", label: "Retry com sucesso", twoPhase: false },
  { id: "BUSINESS_NEGATIVE", label: "Negativa de negócio", twoPhase: false },
  { id: "WAIT_SIGNAL_RESUME", label: "Espera, sinal e retomada", twoPhase: true },
  { id: "CALLBACK_RECONCILIATION", label: "Callback e reconciliação", twoPhase: false },
  { id: "TECHNICAL_FAILURE", label: "Falha técnica", twoPhase: false },
];

const results = [];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(30000);

const posts = [];
page.on("response", async (response) => {
  const url = response.url();
  if (!url.includes("/v1/canonical/")) return;
  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }
  posts.push({
    url,
    method: response.request().method(),
    status: response.status(),
    executionId: body?.execution?.executionId || body?.executionId || null,
    state: body?.execution?.state || null,
    processingStatus: body?.processingStatus || null,
    technicalStatus: body?.outcome?.technicalStatus || null,
    accepted: body?.outcome?.businessOutcome?.accepted,
    callback: body?.callback || null,
  });
});

await page.goto("http://127.0.0.1:5180/", { waitUntil: "networkidle" });
await page.getByRole("button", { name: "Simulação" }).click();
await page.waitForSelector("[data-testid=simulation-panel]");
await page.getByRole("button", { name: "Executar Sucesso em múltiplas etapas" }).waitFor({ state: "visible" });
await page.waitForFunction(() => {
  const button = [...document.querySelectorAll("button")].find((item) =>
    item.getAttribute("aria-label") === "Executar Sucesso em múltiplas etapas",
  );
  return button && !button.disabled;
}, null, { timeout: 20000 });
await page.waitForTimeout(400);
await page.screenshot({ path: `${dir}/01-simulation-catalog.png`, fullPage: true });

for (const scenario of scenarios) {
  await page.getByRole("button", { name: "Simulação" }).click();
  const run = page.getByRole("button", { name: `Executar ${scenario.label}` });
  const enabled = await run.isEnabled();
  if (!enabled) {
    results.push({ id: scenario.id, available: false, reason: "botão desabilitado na UI" });
    continue;
  }
  const before = posts.length;
  await run.click();
  if (scenario.twoPhase) {
    await page.getByText("Execução em espera. Envie o sinal para retomar.").waitFor();
    await page.screenshot({ path: `${dir}/02-wait-signal.png`, fullPage: true });
    await page.getByRole("button", { name: "Enviar sinal" }).click();
  }
  await page.getByRole("status").first().waitFor({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1200);
  const selected = await page.locator("button.monitor-transaction[aria-pressed=true]").innerText().catch(() => "");
  const heading = await page.locator(".workspace-stage, .monitor-workspace-grid").innerText().catch(() => "");
  await page.screenshot({ path: `${dir}/monitor-${scenario.id.toLowerCase()}.png`, fullPage: true });
  const related = posts.slice(before);
  results.push({
    id: scenario.id,
    available: true,
    enabled,
    related,
    selected,
    headingSnippet: heading.slice(0, 500),
  });
}

writeFileSync(`${dir}/ui-results.json`, JSON.stringify({ capturedAt: new Date().toISOString(), results }, null, 2));
console.log(JSON.stringify(results, null, 2));
await browser.close();
