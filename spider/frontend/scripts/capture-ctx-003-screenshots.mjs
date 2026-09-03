/**
 * Evidências CTX-003 no Console real.
 * A origem NL usa scripted-evidence; planejamento e capability resolution são determinísticos.
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
  await workingCapital.getByText("SEEK_WORKING_CAPITAL", { exact: true }).first().waitFor();
  await workingCapital.getByText("R$ 50.000,00", { exact: true }).waitFor();
  await workingCapital
    .getByText("WORKING_CAPITAL_DIAGNOSTIC_V1", { exact: true })
    .first()
    .waitFor();
  await workingCapital
    .getByText("PARCIALMENTE DISPONÍVEL", { exact: true })
    .first()
    .waitFor();
  if ((await workingCapital.getByRole("button", { name: "Executar" }).count()) > 0) {
    throw new Error("Plano parcial expôs execução");
  }
  await page.screenshot({
    path: path.join(outDir, "CTX-003-working-capital-intent.png"),
    fullPage: true,
  });

  const plan = workingCapital.getByTestId("context-execution-plan");
  await plan.screenshot({ path: path.join(outDir, "CTX-003-execution-plan.png") });

  const capabilities = workingCapital.getByTestId("context-capabilities");
  if ((await capabilities.locator("li").count()) !== 7) {
    throw new Error("Plano de capital de giro não exibiu sete capabilities");
  }
  await capabilities.screenshot({ path: path.join(outDir, "CTX-003-capabilities.png") });

  await capabilities.getByRole("button", { name: /IDENTIFY_CUSTOMER/ }).click();
  const detail = workingCapital.getByTestId("context-capability-detail");
  await detail.getByText("AUTHENTICATED_CONTEXT_CUSTOMER_V1", { exact: true }).waitFor();
  await detail.screenshot({ path: path.join(outDir, "CTX-003-capability-detail.png") });

  await workingCapital.screenshot({ path: path.join(outDir, "CTX-003-partial-plan.png") });

  const credit = await interpret(
    page,
    "Minha proposta 12345 foi aprovada, mas o crédito ainda não foi liberado.",
  );
  await credit
    .getByText("CREDIT_RELEASE_INVESTIGATION_PLAN_V1", { exact: true })
    .first()
    .waitFor();
  await credit.getByRole("button", { name: "Executar" }).click();
  await page.getByTestId("home-current-execution").waitFor({ timeout: 20000 });
  const journey = page.getByTestId("execution-journey");
  await journey.getByTestId("journey-zone-context").waitFor({ timeout: 20000 });
  await journey.getByTestId("journey-zone-plan").waitFor({ timeout: 20000 });
  await journey.getByTestId("journey-zone-data").waitFor({ timeout: 20000 });
  await page.screenshot({
    path: path.join(outDir, "CTX-003-context-plan-dataplane.png"),
    fullPage: true,
  });

  await browser.close();
  console.log("CTX-003 screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
