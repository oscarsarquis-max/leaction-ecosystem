/**
 * Evidências visuais SPIDER-DEMO-001C — entrada SpiderBank vs Console.
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
      // stack ainda iniciando
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Serviço indisponível: ${url}`);
}

async function main() {
  await waitHealthy(`${API}/actuator/health`);
  await waitHealthy(`${API}/demo/partner/agro-hoje`);
  await waitHealthy(UI);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  await page.goto(`${UI}/`, { waitUntil: "networkidle" });
  await page.getByTestId("hub-hero").waitFor();
  if (await page.getByRole("heading", { name: "Home operacional" }).count()) {
    throw new Error("Root still shows operational home");
  }
  await page.screenshot({ path: path.join(outDir, "DEMO-001C-root-spiderbank.png") });

  await page.goto(`${UI}/spiderbank`, { waitUntil: "networkidle" });
  await page.getByTestId("direct-entry").waitFor();
  await page.screenshot({ path: path.join(outDir, "DEMO-001C-spiderbank-direct.png") });

  await page.goto(`${UI}/console`, { waitUntil: "networkidle" });
  await page.getByTestId("spider-console").waitFor();
  await page.getByRole("heading", { name: "Home operacional" }).waitFor();
  await page.screenshot({ path: path.join(outDir, "DEMO-001C-console-route.png") });

  await page.goto(`${API}/demo/partner/agro-hoje`, { waitUntil: "networkidle" });
  const popupPromise = page.waitForEvent("popup");
  await page.getByTestId("spiderbank-cta").click();
  const bank = await popupPromise;
  await bank.waitForURL(/\/spiderbank(?:\/entry)?\?ctx=ctx-/);
  await bank.getByTestId("fold-moment").waitFor();
  const landed = bank.url();
  if (!/\/spiderbank/.test(landed) || /\/console/.test(landed)) {
    throw new Error(`Redirect landed on unexpected URL: ${landed}`);
  }
  await bank.screenshot({ path: path.join(outDir, "DEMO-001C-campoaberto-to-spiderbank.png") });

  await page.goto(`${UI}/demo/contextual-link`, { waitUntil: "networkidle" });
  await page.getByTestId("experience-hub").waitFor();
  await page.screenshot({ path: path.join(outDir, "DEMO-001C-presentation-three-surfaces.png") });

  await browser.close();
  console.log("DEMO-001C screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
