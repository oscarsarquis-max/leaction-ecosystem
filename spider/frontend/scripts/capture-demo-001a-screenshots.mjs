/**
 * Evidências visuais SPIDER-DEMO-001A — experiência SpiderBank Banco Contextual.
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
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();

  await page.goto(`${API}/demo/partner/agro-hoje`, { waitUntil: "networkidle" });
  await page.getByTestId("partner-ad").waitFor();
  await page.getByTestId("partner-ad").screenshot({
    path: path.join(outDir, "DEMO-001A-campoaberto-cta.png"),
  });

  await Promise.all([
    page.waitForURL(/\/spiderbank\/entry\?ctx=ctx-/),
    page.getByTestId("spiderbank-cta").click(),
  ]);
  await page.getByTestId("spiderbank-hero").waitFor();
  await page.getByTestId("spiderbank-hero").screenshot({
    path: path.join(outDir, "DEMO-001A-spiderbank-hero.png"),
  });
  await page.getByTestId("origin-context").screenshot({
    path: path.join(outDir, "DEMO-001A-context-arrival.png"),
  });
  await page.getByTestId("objective-block").screenshot({
    path: path.join(outDir, "DEMO-001A-objective-input.png"),
  });

  await page.getByTestId("open-provenance").click();
  await page.getByTestId("provenance-panel").waitFor();
  await page.getByTestId("provenance-panel").screenshot({
    path: path.join(outDir, "DEMO-001A-how-context-was-created.png"),
  });

  await page.goto(`${UI}/demo/contextual-link`, { waitUntil: "networkidle" });
  await page.getByTestId("experience-hub").waitFor();
  await page.screenshot({
    path: path.join(outDir, "DEMO-001A-presentation-flow.png"),
    fullPage: true,
  });

  await browser.close();
  console.log("DEMO-001A screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
