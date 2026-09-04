/**
 * Evidências pontuais — correção gate Cortex mobile (8 etapas + Gigio tablet).
 * Não regenera a matriz completa das 42 imagens.
 *
 * Pré-requisito: vite preview em :5187 com dist atual.
 */
import { chromium } from "playwright";
import { mkdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const outDir = path.resolve(root, "..", "documentacao", "evidencias", "cursor-028-mobile");
mkdirSync(outDir, { recursive: true });

const PORT = Number(process.env.PANNE_EVIDENCE_PORT || 5187);
const BASE = `http://127.0.0.1:${PORT}`;

/** Proprietário autorizado — inclui custos (etapa 8) e demais etapas do fluxo. */
const OWNER_PERMS = [
  "procurement.read",
  "procurement.receive",
  "fiscal.document.read",
  "fiscal.document.capture",
  "fiscal.document.match",
  "fiscal.document.check",
  "product.read",
  "inventory.read",
  "recipe.read",
  "ingredient.read",
  "production.board.read",
  "production.plan.read",
  "production.order.read",
  "labeling.read",
  "costing.read",
  "pricing.review",
  "pricing.simulation.manage",
  "supplier.read",
];

const READER_PERMS = OWNER_PERMS.filter(
  (code) =>
    !code.startsWith("costing.")
    && !code.startsWith("pricing."),
);

async function waitReady(ms = 60000) {
  const start = Date.now();
  while (Date.now() - start < ms) {
    try {
      const res = await fetch(BASE);
      if (res.ok || res.status === 200) return;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`preview não respondeu em ${BASE}`);
}

function mePayload(perms, role = "owner") {
  return {
    user_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    display_name: "Ana Padeiro",
    status: "active",
    associations: [
      {
        organization_id: "11111111-1111-1111-1111-111111111111",
        display_name: "Padaria Central",
        slug: "padaria-central",
        status: "active",
        roles: [role],
        permissions: perms,
      },
    ],
    permissions: perms,
  };
}

async function mockApi(page, perms) {
  await page.route("**/api/**", async (route) => {
    const p = new URL(route.request().url()).pathname;
    const json = (data, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(data),
      });
    if (p.endsWith("/api/v1/me") || p === "/api/v1/me") return json(mePayload(perms));
    if (p.includes("/fiscal/documents/summary")) {
      return json({
        data: {
          total: 4,
          awaiting_match: 1,
          awaiting_check: 1,
          partially_received: 1,
          divergent: 1,
          confirmed: 0,
        },
      });
    }
    if (p.includes("/fiscal/documents") && !p.includes("/items")) {
      return json({ items: [], total: 0, limit: 50, offset: 0 });
    }
    if (p.includes("/products/summary")) {
      return json({
        data: {
          total: 6,
          purchased: 2,
          produced: 3,
          mixed: 1,
          combo: 0,
          produced_without_recipe: 1,
        },
      });
    }
    if (p.includes("/products")) return json({ items: [], total: 0, limit: 50, offset: 0 });
    return json({ items: [], total: 0, data: {}, success: true });
  });
}

async function dismissChrome(page) {
  await page.keyboard.press("Escape").catch(() => undefined);
  await page.evaluate(() => {
    const open = document.querySelector(".account-menu__trigger[aria-expanded='true']");
    if (open instanceof HTMLElement) open.click();
  }).catch(() => undefined);
  await page.waitForTimeout(100);
}

async function signIn(page) {
  await page.goto(`${BASE}/entrar`, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    sessionStorage.setItem("panne.fakeSession", "1");
    sessionStorage.setItem("panne.demoSubject", "demo-owner");
    localStorage.setItem("panne.activeOrganization", "11111111-1111-1111-1111-111111111111");
  });
  const entrar = page.getByRole("button", { name: /^Entrar/ }).first();
  if (await entrar.count()) {
    await entrar.click();
    await page.waitForURL(/\/fluxo/, { timeout: 15000 }).catch(() => undefined);
  } else {
    await page.goto(`${BASE}/fluxo`, { waitUntil: "networkidle" });
  }
  await dismissChrome(page);
}

async function shot(page, fileBase, fullPage = true) {
  await dismissChrome(page);
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${fileBase}.png`, fullPage });
  console.log("shot", `${fileBase}.png`);
}

async function withContext(browser, vp, perms, run) {
  const context = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  await mockApi(page, perms);
  await signIn(page);
  await run(page);
  await context.close();
}

async function main() {
  if (!existsSync(path.join(root, "dist", "index.html"))) {
    throw new Error("Execute npm run build antes das capturas.");
  }
  await waitReady();
  const browser = await chromium.launch({ headless: true });
  try {
    // Proprietário — 8 etapas + Gigio compacto
    await withContext(browser, { width: 390, height: 844 }, OWNER_PERMS, async (page) => {
      await page.goto(`${BASE}/fluxo`, { waitUntil: "networkidle" });
      await shot(page, path.join(outDir, "fix-fluxo-8etapas__celular-390__viewport"), false);
      await shot(page, path.join(outDir, "fix-fluxo-8etapas__celular-390"), true);
      await page.goto(`${BASE}/gestao/compras/entradas`, { waitUntil: "networkidle" });
      await shot(page, path.join(outDir, "fix-trilha-8etapas__celular-390__viewport"), false);
    });

    await withContext(browser, { width: 768, height: 1024 }, OWNER_PERMS, async (page) => {
      await page.goto(`${BASE}/fluxo`, { waitUntil: "networkidle" });
      await shot(page, path.join(outDir, "fix-fluxo-gigio-compacto__tablet-v-768__viewport"), false);
      await shot(page, path.join(outDir, "fix-fluxo-8etapas__tablet-v-768"), true);
    });

    await withContext(browser, { width: 1440, height: 900 }, OWNER_PERMS, async (page) => {
      await page.goto(`${BASE}/fluxo`, { waitUntil: "networkidle" });
      await shot(page, path.join(outDir, "fix-fluxo-8etapas__desktop-1440__viewport"), false);
    });

    // Sem custos — etapa 8 oculta (7 etapas), Anterior/Próxima coerentes
    await withContext(browser, { width: 390, height: 844 }, READER_PERMS, async (page) => {
      await page.goto(`${BASE}/fluxo`, { waitUntil: "networkidle" });
      await shot(page, path.join(outDir, "fix-fluxo-sem-custos__celular-390__viewport"), false);
    });

    console.log("OK evidencias pontuais em", outDir);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
