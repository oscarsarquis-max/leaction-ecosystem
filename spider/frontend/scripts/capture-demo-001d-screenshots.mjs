/**
 * Evidências visuais SPIDER-DEMO-001D — reportagem CampoAberto com publicidade SpiderBank.
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
const ARTICLE = `${API}/demo/partner/agro-hoje`;

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
  await waitHealthy(ARTICLE);
  await waitHealthy(UI);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1920, height: 1080 } });
  const page = await context.newPage();

  await page.goto(ARTICLE, { waitUntil: "networkidle" });
  await page.getByTestId("partner-article").waitFor();
  await page.screenshot({
    path: path.join(outDir, "DEMO-001D-campoaberto-full-article.png"),
    fullPage: true,
  });
  await page.screenshot({
    path: path.join(outDir, "DEMO-001D-article-and-spiderbank-ad.png"),
  });
  await page.screenshot({
    path: path.join(outDir, "DEMO-001D-before-click.png"),
  });

  await page.getByTestId("demo-link-proof").locator("summary").click();
  await page.getByTestId("installed-link").waitFor();
  await page.screenshot({
    path: path.join(outDir, "DEMO-001D-generic-link-on-article.png"),
  });

  const popupPromise = page.waitForEvent("popup");
  await page.getByTestId("spiderbank-cta").click();
  const bank = await popupPromise;
  await bank.waitForURL(/\/spiderbank(?:\/entry)?\?ctx=ctx-/);
  await bank.getByTestId("fold-moment").waitFor();
  await bank.getByTestId("origin-name").waitFor();
  await bank.screenshot({
    path: path.join(outDir, "DEMO-001D-after-click-spiderbank.png"),
  });

  await bank.getByTestId("open-provenance").click();
  await bank.getByTestId("provenance-panel").waitFor();
  await bank.getByTestId("source-title").waitFor();
  await bank.getByTestId("fingerprint").waitFor();
  await bank.screenshot({
    path: path.join(outDir, "DEMO-001D-article-context-proof.png"),
  });

  await browser.close();
  console.log("DEMO-001D screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
