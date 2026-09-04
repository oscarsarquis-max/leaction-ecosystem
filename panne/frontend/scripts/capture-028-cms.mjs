/**
 * Evidências CURSOR-028-CMS — /entrar (remoto simulado + fallback Hub down).
 * Sessão local controlada; timeouts explícitos; não repete matriz mobile completa.
 * Rodar: node scripts/capture-028-cms.mjs  (não usar `npm exec` — instala node desnecessário).
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const outDir = path.resolve(root, "..", "documentacao", "evidencias", "cursor-028-cms");
mkdirSync(outDir, { recursive: true });

const BASE = process.env.PANNE_EVIDENCE_BASE || "http://127.0.0.1:5180";
const NAV_TIMEOUT = 15000;
const ACTION_TIMEOUT = 10000;

const VIEWPORTS = [
  { name: "celular-390", width: 390, height: 844 },
  { name: "tablet-v-768", width: 768, height: 1024 },
  { name: "tablet-h-1024", width: 1024, height: 768 },
  { name: "desktop-1440", width: 1440, height: 900 },
];

const remotePayload = {
  schema_version: 1,
  source: "hub",
  config_key: "panne-demo",
  columns: [
    {
      schema_version: 1,
      placement: "left",
      locale: "pt-BR",
      eyebrow: "Hub",
      title: "Editorial remoto panne-demo",
      summary: "Conteúdo mapeado do Action Hub (evidência local).",
      sections: ["Sem hero.", "CTA allowlist."],
      image: { url: "/images/aprovados/horizontal-claro.png", alt: "Panne" },
      priority: 10,
      hash: "ev-remote-l",
    },
    {
      schema_version: 1,
      placement: "right",
      locale: "pt-BR",
      eyebrow: "CMS",
      title: "Coluna direita remota",
      summary: "Login permanece no centro.",
      sections: ["Key servidor."],
      image: { url: "/images/aprovados/compacto-escuro.png", alt: "Marca" },
      cta: { label: "Docs LeAction", url: "https://docs.leaction.com.br/panne" },
      priority: 9,
      hash: "ev-remote-r",
    },
  ],
};

async function fulfillEditorial(page, body) {
  await page.route("**/api/v1/public/login-editorial**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

async function shot(page, file) {
  await page.screenshot({
    path: path.join(outDir, file),
    fullPage: false,
    timeout: ACTION_TIMEOUT,
  });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const started = Date.now();
  try {
    // --- remoto (payload Hub simulado no BFF mock) ---
    for (const vp of VIEWPORTS) {
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
      });
      const page = await context.newPage();
      page.setDefaultTimeout(ACTION_TIMEOUT);
      page.setDefaultNavigationTimeout(NAV_TIMEOUT);
      await fulfillEditorial(page, remotePayload);
      await page.goto(`${BASE}/entrar`, { waitUntil: "networkidle", timeout: NAV_TIMEOUT });
      await page.getByRole("heading", { name: "Entrar na Panne" }).waitFor({ timeout: ACTION_TIMEOUT });
      await page.getByRole("heading", { name: "Editorial remoto panne-demo" }).waitFor({ timeout: ACTION_TIMEOUT });
      await shot(page, `entrar-remoto-${vp.name}.png`);
      await context.close();
    }

    // --- fallback Hub down (API real ou static via provider) ---
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await context.newPage();
    page.setDefaultTimeout(ACTION_TIMEOUT);
    page.setDefaultNavigationTimeout(NAV_TIMEOUT);
    // força falha de rede no editorial → FE cai para static provider
    await page.route("**/api/v1/public/login-editorial**", (route) => route.abort("failed"));
    await page.goto(`${BASE}/entrar`, { waitUntil: "networkidle", timeout: NAV_TIMEOUT });
    await page.getByRole("heading", { name: "Entrar na Panne" }).waitFor({ timeout: ACTION_TIMEOUT });
    await page.getByRole("heading", { name: "O turno cabe no quadro" }).waitFor({ timeout: ACTION_TIMEOUT });
    await shot(page, "entrar-fallback-hub-down-desktop.png");
    await context.close();

    writeFileSync(
      path.join(outDir, "evidence-capture-meta.json"),
      JSON.stringify(
        {
          base: BASE,
          viewports_remoto: VIEWPORTS.map((v) => v.name),
          hub_admin_selector: "bloqueado — Docker Desktop off",
          elapsed_ms: Date.now() - started,
        },
        null,
        2,
      ),
      "utf8",
    );
    console.log("OK evidences in", outDir, "ms=", Date.now() - started);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error("CAPTURE_FAIL", err);
  process.exit(1);
});
