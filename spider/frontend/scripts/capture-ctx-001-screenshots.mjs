/**
 * Evidências funcionais CTX-001 em stack local-demo real.
 * Nenhuma rota é interceptada e nenhum estado é injetado no browser.
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

async function waitHealthy(url, attempts = 45) {
  for (let index = 0; index < attempts; index += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch {
      // Stack ainda iniciando.
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
  await page.screenshot({
    path: path.join(outDir, "CTX-001-home-context.png"),
    fullPage: true,
  });
  await page.getByTestId("business-intent-cards").screenshot({
    path: path.join(outDir, "CTX-001-business-intents.png"),
  });

  await contextPlane.getByRole("button", { name: "Investigar" }).first().click();
  const preview = page.getByTestId("intent-preview");
  await preview.getByText("CREDIT_RELEASE_DIAGNOSTIC_V1", { exact: true }).waitFor();
  await preview.screenshot({ path: path.join(outDir, "CTX-001-intent-preview.png") });
  await page.getByTestId("context-route-resolution").screenshot({
    path: path.join(outDir, "CTX-001-route-resolution.png"),
  });

  await preview.getByRole("button", { name: "Executar" }).click();
  await page.getByTestId("home-current-execution").waitFor({ timeout: 20000 });
  await page.getByTestId("journey-stage-context-route-resolved").waitFor({ timeout: 20000 });
  await page.screenshot({
    path: path.join(outDir, "CTX-001-context-to-execution.png"),
    fullPage: true,
  });
  const journey = page.getByTestId("execution-journey");
  await journey.getByText("CONTEXTO", { exact: true }).waitFor();
  await journey.getByText("DATA PLANE", { exact: true }).waitFor();
  await journey.screenshot({ path: path.join(outDir, "CTX-001-context-journey.png") });

  const body = await page.locator("body").innerText();
  if (!/IA — próxima etapa/.test(body) || /Submetido\. Resposta/.test(body)) {
    throw new Error("Boundary visual CTX-001 inválido");
  }
  if (externalAiCalls.length > 0) {
    throw new Error(`CTX-001 chamou serviço de IA: ${externalAiCalls.join(", ")}`);
  }

  await page.setViewportSize({ width: 390, height: 844 });
  const mobile = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  if (mobile.content > mobile.viewport) {
    throw new Error("Context Intelligence gerou scroll horizontal no viewport móvel");
  }

  await browser.close();
  console.log("CTX-001 screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
