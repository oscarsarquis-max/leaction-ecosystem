/**
 * Aceite funcional/visual do SPIDER-CTX-001A em stack local-demo real.
 * Exercita os seis cards, o preview separado e a transição Crédito → Jornada.
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
const intents = [
  "INVESTIGATE_CREDIT_RELEASE",
  "INVESTIGATE_COLLECTION_PENDING",
  "INVESTIGATE_BILLING_FAILURE",
  "CHECK_CUSTOMER_DATA_INCONSISTENCY",
  "INVESTIGATE_SERVICE_REQUEST",
  "INVESTIGATE_INCIDENT",
];

async function waitHealthy(url, attempts = 45) {
  for (let index = 0; index < attempts; index += 1) {
    try {
      if ((await fetch(url)).ok) return;
    } catch {
      // Serviço ainda iniciando.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Serviço indisponível: ${url}`);
}

async function main() {
  await waitHealthy(`${API}/actuator/health`);
  await waitHealthy(UI);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();
  const externalAiCalls = [];
  page.on("request", (request) => {
    if (/openai|anthropic|bedrock|ollama|\/llm|\/ai\//i.test(request.url())) {
      externalAiCalls.push(request.url());
    }
  });

  await page.goto(UI, { waitUntil: "networkidle" });
  const contextPlane = page.getByTestId("context-intelligence");
  await contextPlane.waitFor();
  await contextPlane.getByText("IA — próxima etapa", { exact: true }).waitFor();
  await page.screenshot({
    path: path.join(outDir, "CTX-001A-context-home.png"),
    fullPage: true,
  });

  const cards = page.locator(".business-intent-card");
  if ((await cards.count()) !== 6) {
    throw new Error("Os seis Business Intent Cards não estão visíveis");
  }
  for (let index = 0; index < intents.length; index += 1) {
    await cards.nth(index).getByRole("button", { name: "Investigar" }).click();
    const preview = page.getByTestId("intent-preview");
    await preview.getByText(intents[index], { exact: true }).first().waitFor();
    await preview.getByText("BUSINESS_CARD", { exact: true }).waitFor();
    await preview.getByText("100%", { exact: true }).waitFor();
    if (index > 0 && (await preview.getByRole("button", { name: "Executar" }).count()) > 0) {
      throw new Error(`${intents[index]} fingiu possuir execução ponta a ponta`);
    }
  }

  await cards.first().getByRole("button", { name: "Investigar" }).click();
  const preview = page.getByTestId("intent-preview");
  await preview.getByText("CREDIT_RELEASE_DIAGNOSTIC_V1", { exact: true }).first().waitFor();
  await preview.screenshot({ path: path.join(outDir, "CTX-001A-spider-entendeu.png") });
  await preview.locator(".intent-preview-grid").screenshot({
    path: path.join(outDir, "CTX-001A-intent-policy-route.png"),
  });

  await preview.getByRole("button", { name: "Executar" }).click();
  await page.getByTestId("home-current-execution").waitFor({ timeout: 20000 });
  const flow = page.getByLabel("Objetivo, Intent, Policy, Rota, Executar e Jornada");
  await flow.locator('li[data-state="complete"]').last().waitFor({ timeout: 20000 });
  const journey = page.getByTestId("execution-journey");
  await journey.getByTestId("journey-zone-context").waitFor();
  await journey.getByTestId("journey-zone-data").waitFor();
  await page.screenshot({
    path: path.join(outDir, "CTX-001A-context-to-dataplane.png"),
    fullPage: true,
  });

  await journey.getByTestId("journey-stage-context-intent-created").getByRole("button").click();
  const detail = journey.getByTestId("journey-step-detail");
  await detail.getByText(/contrato de intenção INVESTIGATE_CREDIT_RELEASE/).first().waitFor();
  await detail.getByText(/Validar contrato, constraints e provenance/).waitFor();
  await journey.screenshot({
    path: path.join(outDir, "CTX-001A-context-step-detail.png"),
  });

  const journeyText = await journey.innerText();
  if (!/CONTEXTO[\s\S]*DATA PLANE/.test(journeyText)) {
    throw new Error("A transição CONTEXTO → DATA PLANE não está clara");
  }
  const bodyText = await page.locator("body").innerText();
  if (!/IA — próxima etapa/.test(bodyText) || /Submetido\. Resposta/.test(bodyText)) {
    throw new Error("Boundary visual CTX-001A inválido");
  }
  if (externalAiCalls.length > 0) {
    throw new Error(`CTX-001A chamou serviço de IA: ${externalAiCalls.join(", ")}`);
  }

  await page.setViewportSize({ width: 390, height: 844 });
  const mobile = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  if (mobile.content > mobile.viewport) {
    throw new Error("CTX-001A gerou scroll horizontal no viewport móvel");
  }

  await browser.close();
  console.log("CTX-001A screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
