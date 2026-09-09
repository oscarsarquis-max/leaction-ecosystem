/**
 * Evidências visuais SPIDER-DEMO-002 — reportagem, link genérico, contexto vs entrada direta.
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
const SCENARIO_A =
  "Perdi parte da safra, tenho compromissos vencendo e preciso de recursos para preparar o próximo plantio.";
const DIRECT = "Preciso de recursos para manter minha produção.";

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

async function stitchLabeled(browser, panels, outPath) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  const cells = panels
    .map(
      (panel) => `
      <section>
        <h1>${panel.label}</h1>
        <p>${panel.caption}</p>
        <img src="data:image/png;base64,${fs.readFileSync(panel.file).toString("base64")}" alt="">
      </section>`,
    )
    .join("");
  await page.setContent(`<!doctype html>
    <html><head><style>
      body { margin: 0; background: #f7f3f1; color: #2c2226; font-family: Segoe UI, Arial, sans-serif; }
      main { display: grid; grid-template-columns: repeat(${panels.length}, 1fr); }
      section { padding: 1rem; border-right: 1px solid #eadde1; }
      h1 { font-size: 1.1rem; color: #7c2748; margin: 0 0 .4rem; letter-spacing: .08em; text-transform: uppercase; }
      p { margin: 0 0 .8rem; font-size: .9rem; }
      img { width: 100%; height: auto; display: block; }
    </style></head><body><main>${cells}</main></body></html>`);
  await page.screenshot({ path: outPath, fullPage: true });
  await page.close();
}

async function main() {
  await waitHealthy(`${API}/actuator/health`);
  await waitHealthy(`${API}/demo/partner/agro-hoje`);
  await waitHealthy(UI);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage();

  await page.goto(`${API}/demo/partner/agro-hoje`, { waitUntil: "networkidle" });
  await page.getByTestId("partner-article").waitFor();
  await page.screenshot({
    path: path.join(outDir, "DEMO-002-campoaberto-report.png"),
    fullPage: true,
  });

  await page.getByTestId("demo-link-proof").locator("summary").click();
  await page.getByTestId("installed-link").waitFor();
  await page.screenshot({
    path: path.join(outDir, "DEMO-002-generic-link.png"),
    fullPage: true,
  });

  const popupPromise = page.waitForEvent("popup");
  await page.getByTestId("spiderbank-cta").click();
  const bank = await popupPromise;
  await bank.waitForURL(/\/spiderbank(?:\/entry)?\?ctx=ctx-/);
  await bank.getByTestId("objective-input").waitFor();
  await bank.getByTestId("objective-input").fill(SCENARIO_A);
  await bank.getByTestId("understand-objective").click();
  await bank.getByTestId("understanding-block").waitFor();
  await bank.getByTestId("open-understanding").click();
  await bank.getByTestId("economic-context").waitFor();
  await bank.screenshot({
    path: path.join(outDir, "DEMO-002-context-from-article.png"),
    fullPage: true,
  });
  const withContextPath = path.join(outDir, "DEMO-002-with-context-side.png");
  await bank.screenshot({ path: withContextPath, fullPage: true });

  const direct = await context.newPage();
  await direct.goto(`${UI}/spiderbank`, { waitUntil: "networkidle" });
  await direct.getByTestId("direct-entry").waitFor();
  await direct.getByTestId("objective-input").fill(DIRECT);
  await direct.getByTestId("understand-objective").click();
  await direct.getByTestId("understanding-block").waitFor();
  await direct.getByTestId("open-understanding").click();
  await direct.getByTestId("economic-context").waitFor();
  const directPath = path.join(outDir, "DEMO-002-direct-side.png");
  await direct.screenshot({ path: directPath, fullPage: true });

  await stitchLabeled(
    browser,
    [
      {
        file: withContextPath,
        label: "Lado A",
        caption: "CampoAberto → reportagem → link genérico → objetivo → CROP_FAILURE",
      },
      {
        file: directPath,
        label: "Lado B",
        caption: "Entrada direta SpiderBank → mesmo tipo de pedido sem safra → CROP_FAILURE ausente",
      },
    ],
    path.join(outDir, "DEMO-002-with-context-vs-direct.png"),
  );

  await page.goto(`${UI}/demo/contextual-link`, { waitUntil: "networkidle" });
  await page.getByTestId("experience-hub").waitFor();
  const presentationPath = path.join(outDir, "DEMO-002-presentation.png");
  await page.screenshot({ path: presentationPath, fullPage: true });

  const partnerShot = path.join(outDir, "DEMO-002-campoaberto-report.png");
  const consolePage = await context.newPage();
  await consolePage.goto(`${UI}/console`, { waitUntil: "networkidle" });
  await consolePage.getByTestId("spider-console").waitFor();
  const consolePath = path.join(outDir, "DEMO-002-console-side.png");
  await consolePage.screenshot({ path: consolePath });

  await stitchLabeled(
    browser,
    [
      { file: partnerShot, label: "Aba 1 — CampoAberto", caption: "De onde surgiu o contexto?" },
      { file: withContextPath, label: "Aba 2 — SpiderBank", caption: "Como o cliente experimenta um Banco Contextual?" },
      { file: consolePath, label: "Aba 3 — Spider Console", caption: "Como provamos tecnicamente o que aconteceu?" },
    ],
    path.join(outDir, "DEMO-002-three-surfaces.png"),
  );

  await browser.close();
  console.log("DEMO-002 screenshots written to", outDir);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
