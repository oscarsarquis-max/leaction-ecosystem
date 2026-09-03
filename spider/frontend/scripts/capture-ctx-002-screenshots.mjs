/**
 * Evidências CTX-002 no Console real, usando provider scripted explicitamente habilitado.
 * Não intercepta rotas e não representa smoke Bedrock real.
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
  const field = page.getByLabel("Interpretação em linguagem natural");
  await field.fill(objective);
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

  const contextPlane = page.getByTestId("context-intelligence");
  await contextPlane.waitFor();
  await page.getByTestId("context-ai-state").getByText("IA CONTEXTUAL — ATIVA").waitFor();
  await page.screenshot({
    path: path.join(outDir, "CTX-002-natural-language-home.png"),
    fullPage: true,
  });

  const success = await interpret(
    page,
    "Minha proposta 12345 foi aprovada, mas o crédito ainda não foi liberado.",
  );
  await success.getByText("NATURAL_LANGUAGE", { exact: true }).waitFor();
  await success.getByText("CREDIT_RELEASE_DIAGNOSTIC_V1", { exact: true }).first().waitFor();
  await success.screenshot({ path: path.join(outDir, "CTX-002-spider-entendeu.png") });

  await success.getByRole("button", { name: "Executar" }).click();
  await page.getByTestId("home-current-execution").waitFor({ timeout: 20000 });
  const journey = page.getByTestId("execution-journey");
  await journey.getByTestId("journey-stage-context-ai-interpreted").waitFor({
    timeout: 20000,
  });
  await journey.getByTestId("journey-zone-data").waitFor();
  await page.screenshot({
    path: path.join(outDir, "CTX-002-context-to-dataplane.png"),
    fullPage: true,
  });

  await journey.getByTestId("journey-stage-context-ai-interpreted").getByRole("button").click();
  const detail = journey.getByTestId("journey-step-detail");
  await detail.getByText("scripted-evidence", { exact: true }).waitFor();
  await detail.getByText(/Eventos relacionados \([1-9][0-9]*\)/).waitFor({ timeout: 10000 });
  await journey.screenshot({
    path: path.join(outDir, "CTX-002-ai-interpretation.png"),
  });

  const ambiguous = await interpret(
    page,
    "Quero saber o que aconteceu com o cliente João.",
  );
  await ambiguous.getByText("AMBIGUOUS", { exact: true }).waitFor();
  if ((await ambiguous.getByRole("button", { name: "Executar" }).count()) > 0) {
    throw new Error("Interpretação ambígua expôs execução");
  }
  await ambiguous.screenshot({ path: path.join(outDir, "CTX-002-ambiguous.png") });

  const missing = await interpret(
    page,
    "Minha proposta foi aprovada, mas o crédito ainda não foi liberado.",
  );
  await missing.getByText("MISSING_CONTEXT", { exact: true }).waitFor();
  await missing.getByText("Qual é o número da proposta?", { exact: true }).waitFor();
  if ((await missing.getByRole("button", { name: "Executar" }).count()) > 0) {
    throw new Error("Interpretação com contexto ausente expôs execução");
  }
  await missing.screenshot({ path: path.join(outDir, "CTX-002-missing-context.png") });

  const unsupported = await interpret(page, "Quero comprar passagens para Paris.");
  await unsupported.getByText("UNSUPPORTED_INTENT", { exact: true }).waitFor();
  if ((await unsupported.getByText("Nenhuma rota foi determinada", { exact: false }).count()) !== 1) {
    throw new Error("Interpretação não suportada não falhou de forma fechada");
  }

  await page.setViewportSize({ width: 390, height: 844 });
  const mobile = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  if (mobile.content > mobile.viewport) {
    throw new Error("CTX-002 gerou scroll horizontal no viewport móvel");
  }

  await browser.close();
  console.log("CTX-002 scripted-provider screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
