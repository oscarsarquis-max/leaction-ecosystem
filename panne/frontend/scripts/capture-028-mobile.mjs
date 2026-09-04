/**
 * Capturas reais — adendo experiência mobile/tablet (Fluxo + Gigio + entradas fiscais).
 * Usa Vite preview + Playwright com mock de API (sem publicar / sem rede Hub).
 *
 * Viewports canônicos (RESPONSIVIDADE.md + celular):
 *  1440×900, 1366×768, 1024×768, 768×1024, 390×844
 *
 * Gera fullPage + viewport (para evidenciar FAB fixo sem distorção do scroll).
 */
import { chromium } from "playwright";
import { mkdirSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const outDir = path.resolve(
  root,
  "..",
  "documentacao",
  "evidencias",
  "cursor-028-mobile",
);
mkdirSync(outDir, { recursive: true });

const PORT = Number(process.env.PANNE_EVIDENCE_PORT || 5187);
const BASE = `http://127.0.0.1:${PORT}`;

const VIEWPORTS = [
  { name: "desktop-1440", width: 1440, height: 900 },
  { name: "notebook-1366", width: 1366, height: 768 },
  { name: "tablet-h-1024", width: 1024, height: 768 },
  { name: "tablet-v-768", width: 768, height: 1024 },
  { name: "celular-390", width: 390, height: 844 },
];

const ROUTES = [
  { slug: "fluxo", path: "/fluxo" },
  { slug: "entradas", path: "/gestao/compras/entradas" },
  { slug: "entradas-nova", path: "/gestao/compras/entradas/nova" },
  { slug: "produtos-coach", path: "/produtos" },
];

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

async function mockApi(page) {
  await page.route("**/api/**", async (route) => {
    const url = route.request().url();
    const u = new URL(url);
    const p = u.pathname;
    const json = (data, status = 200) =>
      route.fulfill({
        status,
        contentType: "application/json",
        body: JSON.stringify(data),
      });

    if (p === "/api/v1/me" || p.endsWith("/api/v1/me")) {
      return json({
        user_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        display_name: "Ana Padeiro",
        status: "active",
        associations: [
          {
            organization_id: "11111111-1111-1111-1111-111111111111",
            display_name: "Padaria Central",
            slug: "padaria-central",
            status: "active",
            roles: ["owner"],
            permissions: [
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
            ],
          },
        ],
        permissions: [
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
        ],
      });
    }
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
      return json({
        items: [
          {
            id: "b1b1b1b1-b1b1-4b1b-8b1b-b1b1b1b1b1b1",
            public_code: "ENT-000001",
            document_number: "104532",
            series: "1",
            access_key: null,
            issued_on: "2026-08-28",
            status: "awaiting_check",
            status_label: "Aguardando conferência",
            origin: "xml",
            supplier: {
              id: null,
              display_name: "Moinho Demo",
              tax_id: "00000000000272",
              registered: false,
            },
            item_count: 2,
            matched_item_count: 1,
            checked_item_count: 0,
            divergence_count: 0,
            received_at: null,
            updated_at: "2026-08-29T09:10:00+00:00",
          },
        ],
        total: 1,
        limit: 50,
        offset: 0,
      });
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
    if (p.includes("/products")) {
      return json({ items: [], total: 0, limit: 50, offset: 0 });
    }
    return json({ items: [], total: 0, data: {}, success: true });
  });
}

async function dismissChrome(page) {
  await page.keyboard.press("Escape").catch(() => undefined);
  await page.evaluate(() => {
    const open = document.querySelector(".account-menu__trigger[aria-expanded='true']");
    if (open instanceof HTMLElement) open.click();
  }).catch(() => undefined);
  await page.waitForTimeout(120);
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

async function main() {
  if (!existsSync(path.join(root, "dist", "index.html"))) {
    throw new Error("Execute npm run build antes das capturas.");
  }
  await waitReady();
  const browser = await chromium.launch({ headless: true });
  try {
    for (const vp of VIEWPORTS) {
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 1,
      });
      const page = await context.newPage();
      await mockApi(page);
      await signIn(page);

      for (const route of ROUTES) {
        await page.goto(`${BASE}${route.path}`, { waitUntil: "networkidle" });
        await dismissChrome(page);
        await page.waitForTimeout(350);
        if (vp.width <= 720 && route.slug !== "fluxo") {
          // Coach recolhido: botão exato "Abrir" (não confundir com "Abrir menu do usuário").
          await page
            .locator(".flow-coach")
            .getByRole("button", { name: "Abrir", exact: true })
            .waitFor({ timeout: 3000 })
            .catch(() => undefined);
        }
        await dismissChrome(page);
        const base = path.join(outDir, `${route.slug}__${vp.name}`);
        await page.screenshot({ path: `${base}.png`, fullPage: true });
        await page.screenshot({ path: `${base}__viewport.png`, fullPage: false });
        console.log("shot", `${base}.png`);
      }

      if (vp.width === 390) {
        await page.goto(`${BASE}/gestao/compras/entradas`, { waitUntil: "networkidle" });
        await dismissChrome(page);
        const avatar = page.locator(".assistant-avatar");
        if (await avatar.count()) {
          await avatar.screenshot({
            path: path.join(outDir, "avatar-flutuante__celular-390.png"),
          });
        }
        // Evidência: coach recolhido + FAB sem cobrir CTA principal
        await page.screenshot({
          path: path.join(outDir, "gigio-nao-cobre__celular-390__viewport.png"),
          fullPage: false,
        });
      }
      await context.close();
    }
    console.log("OK evidencias em", outDir);
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
