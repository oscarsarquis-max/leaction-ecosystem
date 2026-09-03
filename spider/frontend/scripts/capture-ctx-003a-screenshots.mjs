/**
 * Evidências CTX-003A no Console real.
 * A origem NL usa scripted-evidence; Plan/Capability/Route resolvers permanecem determinísticos.
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

async function waitHealthy(url, attempts = 60) {
  for (let index = 0; index < attempts; index += 1) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      // Stack ainda iniciando.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Serviço indisponível: ${url}`);
}

async function interpret(page, objective) {
  await page.getByLabel("Interpretação em linguagem natural").fill(objective);
  await page.getByRole("button", { name: "Interpretar" }).click();
  return page.getByTestId("intent-preview");
}

async function clickPhase(page, id) {
  await page.getByTestId(`objective-phase-${id}`).locator("button").first().click();
}

async function main() {
  await waitHealthy(`${API}/actuator/health`);
  await waitHealthy(UI);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();
  await page.goto(UI, { waitUntil: "networkidle" });
  await page.getByTestId("context-ai-state").getByText("IA CONTEXTUAL — ATIVA").waitFor();

  const workingCapital = await interpret(
    page,
    "Preciso de R$ 50 mil para reforçar meu estoque.",
  );
  await workingCapital.getByText("SEEK_WORKING_CAPITAL").first().waitFor();
  await workingCapital.getByText("WORKING_CAPITAL_DIAGNOSTIC_V1").first().waitFor();
  await page.getByTestId("objective-journey").waitFor();
  if ((await workingCapital.getByRole("button", { name: "Executar" }).count()) > 0) {
    throw new Error("Plano parcial expôs execução");
  }

  await clickPhase(page, "objective");
  await page.screenshot({
    path: path.join(outDir, "CTX-003A-objective-to-result.png"),
    fullPage: true,
  });

  await clickPhase(page, "understanding");
  await page.getByTestId("objective-journey-detail").getByText("SEEK_WORKING_CAPITAL").first().waitFor();
  await page
    .getByTestId("objective-journey")
    .screenshot({ path: path.join(outDir, "CTX-003A-understanding.png") });

  await clickPhase(page, "plan");
  await page.getByTestId("context-execution-plan").waitFor();
  await page
    .getByTestId("objective-journey")
    .screenshot({ path: path.join(outDir, "CTX-003A-plan.png") });

  const capabilities = page.getByTestId("context-capabilities");
  if ((await capabilities.locator("li").count()) !== 7) {
    throw new Error("Plano de capital de giro não exibiu sete capabilities");
  }
  await capabilities.screenshot({ path: path.join(outDir, "CTX-003A-capabilities.png") });

  await capabilities.getByRole("button", { name: /IDENTIFY_CUSTOMER/ }).click();
  const detail = page.getByTestId("context-capability-detail");
  await detail.getByText("AUTHENTICATED_CONTEXT_CUSTOMER_V1").first().waitFor();
  await detail.screenshot({ path: path.join(outDir, "CTX-003A-capability-detail.png") });

  await clickPhase(page, "resolution");
  await page.getByTestId("objective-resolution-table").waitFor();
  await page
    .getByTestId("objective-journey")
    .screenshot({ path: path.join(outDir, "CTX-003A-capability-resolution.png") });

  await clickPhase(page, "result");
  await page.getByTestId("objective-result").getByText("PLANO PARCIALMENTE DISPONÍVEL").waitFor();
  await page
    .getByTestId("objective-journey")
    .screenshot({ path: path.join(outDir, "CTX-003A-result.png") });
  await page.screenshot({
    path: path.join(outDir, "CTX-003A-partial-result.png"),
    fullPage: true,
  });

  const credit = await interpret(
    page,
    "Minha proposta 12345 foi aprovada, mas o crédito ainda não foi liberado.",
  );
  await credit.getByText("CREDIT_RELEASE_INVESTIGATION_PLAN_V1").first().waitFor();
  await credit.getByRole("button", { name: "Executar" }).click();
  await page.getByTestId("home-current-execution").waitFor({ timeout: 20000 });
  const journey = page.getByTestId("execution-journey");
  await journey.getByTestId("journey-zone-context").waitFor({ timeout: 20000 });
  await journey.getByTestId("journey-zone-plan").waitFor({ timeout: 20000 });
  await journey.getByTestId("journey-zone-data").waitFor({ timeout: 20000 });
  await clickPhase(page, "execution");
  await page.screenshot({
    path: path.join(outDir, "CTX-003A-dataplane.png"),
    fullPage: true,
  });

  await browser.close();
  console.log("CTX-003A screenshots written to", outDir);
}

main().catch((event) => {
  console.error(event);
  process.exit(1);
});
