/**
 * Evidências visuais SPIDER-DEMO-001B — redesign editorial do Banco Contextual.
 * Viewport de apresentação: 1920×1080.
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

function dataUrl(file) {
  return `data:image/png;base64,${fs.readFileSync(file).toString("base64")}`;
}

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

  await page.goto(`${API}/demo/partner/agro-hoje`, { waitUntil: "networkidle" });
  await page.getByTestId("partner-ad").waitFor();
  await page.getByTestId("partner-ad").screenshot({
    path: path.join(outDir, "DEMO-001B-campoaberto-ad.png"),
  });

  const popupPromise = page.waitForEvent("popup");
  await page.getByTestId("spiderbank-cta").click();
  const bank = await popupPromise;
  await bank.waitForURL(/\/spiderbank(?:\/entry)?\?ctx=ctx-/);
  await bank.getByTestId("spiderbank-hero").waitFor();
  await bank.getByTestId("fold-moment").waitFor();
  await bank.screenshot({
    path: path.join(outDir, "DEMO-001B-spiderbank-first-fold.png"),
  });
  await bank.getByTestId("origin-context").scrollIntoViewIfNeeded();
  await bank.getByTestId("origin-context").screenshot({
    path: path.join(outDir, "DEMO-001B-spiderbank-context.png"),
  });
  await bank.getByTestId("objective-block").scrollIntoViewIfNeeded();
  await bank.getByTestId("objective-block").screenshot({
    path: path.join(outDir, "DEMO-001B-spiderbank-objective.png"),
  });
  await bank.getByTestId("story-path").scrollIntoViewIfNeeded();
  await bank.getByTestId("story-path").screenshot({
    path: path.join(outDir, "DEMO-001B-spiderbank-context-objective-path.png"),
  });

  await bank.getByTestId("open-provenance").click();
  await bank.getByTestId("provenance-panel").waitFor();
  await bank.locator(".sb-drawer").screenshot({
    path: path.join(outDir, "DEMO-001B-context-proof-drawer.png"),
  });
  await bank.keyboard.press("Escape");

  await page.goto(`${UI}/demo/contextual-link`, { waitUntil: "networkidle" });
  await page.getByTestId("experience-hub").waitFor();
  await page.screenshot({
    path: path.join(outDir, "DEMO-001B-presentation-route.png"),
  });

  const beforePath = path.join(outDir, "DEMO-001A-spiderbank-hero.png");
  const afterPath = path.join(outDir, "DEMO-001B-spiderbank-first-fold.png");
  if (!fs.existsSync(beforePath)) {
    throw new Error("Missing DEMO-001A-spiderbank-hero.png for before/after");
  }
  const compare = await context.newPage();
  await compare.setViewportSize({ width: 1920, height: 1080 });
  await compare.setContent(`<!DOCTYPE html>
<html><body style="margin:0;background:#1a1216;color:#fff;font-family:Segoe UI,Arial,sans-serif">
  <div style="display:grid;grid-template-columns:1fr 1fr;height:1080px">
    <figure style="margin:0;position:relative;overflow:hidden;background:#111">
      <img src="${dataUrl(beforePath)}" alt="antes" style="width:100%;height:100%;object-fit:contain;object-position:top;background:#f7f3f1"/>
      <figcaption style="position:absolute;top:28px;left:28px;background:#7c2748;padding:10px 16px;letter-spacing:.16em;font-size:14px;font-weight:800">ANTES — DEMO-001A</figcaption>
    </figure>
    <figure style="margin:0;position:relative;overflow:hidden">
      <img src="${dataUrl(afterPath)}" alt="depois" style="width:100%;height:100%;object-fit:contain;object-position:top;background:#f7f3f1"/>
      <figcaption style="position:absolute;top:28px;left:28px;background:#7c2748;padding:10px 16px;letter-spacing:.16em;font-size:14px;font-weight:800">DEPOIS — DEMO-001B</figcaption>
    </figure>
  </div>
</body></html>`);
  await compare.screenshot({ path: path.join(outDir, "DEMO-001B-before-after.png") });
  await compare.close();

  await browser.close();
  console.log("DEMO-001B screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
