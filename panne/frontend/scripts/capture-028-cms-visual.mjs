/**
 * Fecho visual CURSOR-028-CMS — 3 screenshots only.
 * node scripts/capture-028-cms-visual.mjs
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const outDir = path.resolve(root, "..", "documentacao", "evidencias", "cursor-028-cms");
const opsDir = path.join(outDir, "ops");
mkdirSync(opsDir, { recursive: true });

// Next 16 bloqueia HMR/assets cross-origin de 127.0.0.1 quando o dev server anuncia localhost.
const HUB = process.env.HUB_FE_BASE || "http://localhost:4000";
const PANNE = process.env.PANNE_FE_BASE || "http://127.0.0.1:5180";
const NAV = 25000;
const ACT = 20000;

function loadJwtSecret() {
  const envPath = path.resolve(root, "..", "..", "leaction-platform", ".env");
  if (!existsSync(envPath)) throw new Error("Hub .env missing");
  const raw = readFileSync(envPath, "utf8");
  for (const line of raw.split(/\r?\n/)) {
    if (line.startsWith("JWT_SECRET=")) {
      return line.slice("JWT_SECRET=".length).trim().replace(/^"|"$/g, "");
    }
  }
  throw new Error("JWT_SECRET not found");
}

async function main() {
  const jwt = require(
    path.resolve(root, "..", "..", "leaction-platform", "services", "gateway-api", "node_modules", "jsonwebtoken"),
  );
  const secret = loadJwtSecret();
  const token = jwt.sign(
    { sub: "cms-visual-fecho", email: "admin@actionhub.com.br" },
    secret,
    { expiresIn: "30m" },
  );

  const browser = await chromium.launch({ headless: true });
  const session = {
    user: { id: "cms-visual", email: "admin@actionhub.com.br", name: "CMS Visual" },
    token,
  };
  try {
    // 1) Admin selector
    {
      const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
      await ctx.addInitScript((s) => {
        localStorage.setItem("actionhub_session", JSON.stringify(s));
      }, session);
      const page = await ctx.newPage();
      page.setDefaultTimeout(ACT);
      page.setDefaultNavigationTimeout(NAV);
      await page.goto(`${HUB}/dashboard/cms/site`, {
        waitUntil: "load",
        timeout: NAV,
      });
      const select = page.locator('select').filter({ has: page.locator('option[value="panne-demo"]') }).first();
      try {
        await select.waitFor({ state: "visible", timeout: ACT });
      } catch (err) {
        const body = await page.locator("body").innerText().catch(() => "");
        writeFileSync(path.join(opsDir, "seletor-debug-body.txt"), body.slice(0, 4000), "utf8");
        await page.screenshot({
          path: path.join(opsDir, "seletor-debug.png"),
          fullPage: true,
          timeout: ACT,
        });
        throw err;
      }
      await select.evaluate((el) => {
        el.size = Math.min(el.options.length, 8);
      });
      await select.selectOption("panne-demo");
      await page.getByRole("heading", { name: /Panne Demonstra/i }).waitFor({ timeout: ACT }).catch(() => {});
      const box = await select.boundingBox();
      if (box) {
        await page.screenshot({
          path: path.join(outDir, "hub-cms-seletor-panne.png"),
          clip: {
            x: Math.max(0, box.x - 40),
            y: Math.max(0, box.y - 120),
            width: Math.min(720, box.width + 120),
            height: Math.min(480, box.height + 200),
          },
          timeout: ACT,
        });
      } else {
        await page.screenshot({
          path: path.join(outDir, "hub-cms-seletor-panne.png"),
          fullPage: false,
          timeout: ACT,
        });
      }
      const options = await select.locator("option").allTextContents();
      writeFileSync(path.join(opsDir, "seletor-options.json"), JSON.stringify({ options }, null, 2), "utf8");
      const joined = options.join(" | ");
      if (!options.some((o) => /Demonstra/i.test(o))) {
        throw new Error(`missing Panne Demonstração in ${joined}`);
      }
      if (!options.some((o) => /Produ/i.test(o))) {
        throw new Error(`missing Panne Produção in ${joined}`);
      }
      await ctx.close();
    }

    // 2) /entrar desktop
    {
      const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
      const page = await ctx.newPage();
      page.setDefaultTimeout(ACT);
      page.setDefaultNavigationTimeout(NAV);
      await page.goto(`${PANNE}/entrar`, { waitUntil: "networkidle", timeout: NAV });
      await page.getByRole("heading", { name: "CURSOR-028-CMS SYNTH LEFT" }).waitFor({ timeout: ACT });
      await page.getByRole("heading", { name: "Entrar na Panne" }).waitFor({ timeout: ACT });
      await page.screenshot({
        path: path.join(outDir, "entrar-desktop-synth.png"),
        fullPage: false,
        timeout: ACT,
      });
      await ctx.close();
    }

    // 3) /entrar mobile
    {
      const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
      const page = await ctx.newPage();
      page.setDefaultTimeout(ACT);
      page.setDefaultNavigationTimeout(NAV);
      await page.goto(`${PANNE}/entrar`, { waitUntil: "networkidle", timeout: NAV });
      await page.getByRole("heading", { name: "Entrar na Panne" }).waitFor({ timeout: ACT });
      await page.screenshot({
        path: path.join(outDir, "entrar-mobile-synth.png"),
        fullPage: false,
        timeout: ACT,
      });
      await ctx.close();
    }

    console.log("OK visual evidences", outDir);
  } finally {
    await browser.close();
  }
}

main().catch((e) => {
  console.error("CAPTURE_FAIL", e);
  process.exit(1);
});
