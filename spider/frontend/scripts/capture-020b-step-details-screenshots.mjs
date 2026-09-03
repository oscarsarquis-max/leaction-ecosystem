/**
 * Aceite visual do painel explicativo 020B.
 * Exercita a Home real e cada seleção obrigatória, sem rotas preparadas.
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

async function waitApi() {
  for (let i = 0; i < 30; i++) {
    try {
      if ((await fetch(`${API}/actuator/health`)).ok) return;
    } catch {
      // Serviço ainda iniciando.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error("API local-demo indisponível");
}

async function select(page, name, expected) {
  await page.getByRole("button", { name }).click();
  const panel = page.getByTestId("journey-step-detail");
  await panel.getByText(expected, { exact: false }).waitFor();
  return panel;
}

async function main() {
  await waitApi();
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await context.newPage();
  await page.goto(UI, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Home operacional" }).waitFor();
  await page.getByRole("button", { name: "Executar demonstração" }).click();
  await page.getByRole("button", { name: /Interaction #1/ }).waitFor({ timeout: 15000 });

  const journey = page.getByTestId("execution-journey");
  await journey.screenshot({ path: path.join(outDir, "020B-step-details-overview.png") });

  await select(page, /Solicitação recebida/, "O Spider recebeu a solicitação");
  const failed = await select(page, /Interaction #1/, "falha transitória");
  await failed.getByText(/TRANSIENT/, { exact: false }).waitFor();
  await journey.screenshot({
    path: path.join(outDir, "020B-step-details-failed-interaction.png"),
  });

  await select(page, /^Retry/, "A tentativa anterior terminou");
  await journey.screenshot({ path: path.join(outDir, "020B-step-details-retry.png") });

  await select(page, /Interaction #2/, "concluída com sucesso");
  await journey.screenshot({ path: path.join(outDir, "020B-step-details-success.png") });

  const completed = await select(page, /Execução concluída/, "terminou em SUCCEEDED");
  await completed.getByText(/Eventos relacionados/).click();
  await completed.getByText("EXECUTION_SUCCEEDED", { exact: true }).waitFor();
  await journey.screenshot({ path: path.join(outDir, "020B-step-details-events.png") });

  const homeText = await page.locator(".home-operational").innerText();
  if (!/Interaction #1[\s\S]*FAILED[\s\S]*Retry[\s\S]*Interaction #2[\s\S]*SUCCEEDED/.test(homeText)) {
    throw new Error("Jornada de retry não permaneceu visível na Home");
  }
  if (/Bearer|local-demo-console|Submetido\. Resposta/.test(homeText)) {
    throw new Error("Conteúdo protegido ou JSON bruto exposto na Home");
  }

  await page.setViewportSize({ width: 390, height: 844 });
  const timelineBox = await page.getByLabel("Etapas da jornada").boundingBox();
  const panelBox = await page.getByTestId("journey-step-detail").boundingBox();
  const widths = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  if (!timelineBox || !panelBox || panelBox.y < timelineBox.y + timelineBox.height - 2) {
    throw new Error("Jornada e painel não foram empilhados no viewport móvel");
  }
  if (widths.content > widths.viewport) {
    throw new Error("Painel explicativo gerou scroll horizontal no viewport móvel");
  }

  await browser.close();
  console.log("020B step-detail screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
