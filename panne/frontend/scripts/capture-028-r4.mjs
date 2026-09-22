import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..");
const outDir = resolve(here, "../../documentacao/evidencias/cursor-028-r4-grafo-produtos");
mkdirSync(outDir, { recursive: true });

const PORT = Number(process.env.PANNE_EVIDENCE_PORT || 5194);
const BASE = `http://127.0.0.1:${PORT}`;
const ORG = "11111111-1111-1111-1111-111111111111";
const PRODUCT_ID = "a1a1a1a1-a1a1-4a1a-8a1a-a1a1a1a1a1a1";
const PRODUCT_PURCHASED_ID = "a2a2a2a2-a2a2-4a2a-8a2a-a2a2a2a2a2a2";
const PRODUCT_READY_ID = "a3a3a3a3-a3a3-4a3a-8a3a-a3a3a3a3a3a3";
const RECIPE_ID = "99999999-9999-9999-9999-999999999999";
const RECIPE_VERSION_ID = "88888888-8888-8888-8888-888888888888";
const FAMILY_ID = "a0a0a0a0-a0a0-4a0a-8a0a-a0a0a0a0a0a0";

const productFixture = {
  id: PRODUCT_ID,
  code: "PAO-TRAD",
  display_name: "Pão tradicional",
  status: "active",
  purpose: "final",
  supply_mode: "produced",
  family: { id: FAMILY_ID, code: "FAM-PAES", display_name: "Pães", status: "active" },
  has_published_recipe: false,
  has_process_steps: false,
  recipe_status_label: "Sem receita vigente",
  row_version: 1,
  current_recipe: null,
};

const productPurchasedFixture = {
  ...productFixture,
  id: PRODUCT_PURCHASED_ID,
  code: "REF-COLA",
  display_name: "Refrigerante de cola",
  supply_mode: "purchased",
  family: null,
  recipe_status_label: "Não se aplica",
};

const productReadyFixture = {
  ...productFixture,
  id: PRODUCT_READY_ID,
  code: "PAO-FR",
  display_name: "Pão francês (Demo)",
  has_published_recipe: true,
  has_process_steps: true,
  recipe_status_label: "Com receita vigente",
  current_recipe: {
    id: RECIPE_ID,
    code: "F-PAO-FR",
    display_name: "Pão francês (Demo)",
    formulation_status: "active",
    version_id: RECIPE_VERSION_ID,
    version_number: 1,
    version_status: "published",
    published_at: "2026-08-24T10:00:00+00:00",
    is_published: true,
    yield_mass_g: "3300",
    items: [
      {
        ingredient_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        code: "FAR-TRIGO",
        display_name: "Farinha de trigo tipo 1",
        quantity: "1000",
        unit: "g",
        role: "ingredient",
        is_flour_basis: true,
      },
      {
        ingredient_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee01",
        code: "AGUA",
        display_name: "Água",
        quantity: "650",
        unit: "g",
        role: "ingredient",
        is_flour_basis: false,
      },
      {
        ingredient_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeee03",
        code: "FER-BIO",
        display_name: "Fermento biológico fresco",
        quantity: "15",
        unit: "g",
        role: "ingredient",
        is_flour_basis: false,
      },
    ],
    steps: [{ sequence: 1, title: "Misturar", instructions: "Misturar." }],
  },
};

const me = {
  user_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
  display_name: "Ana Padeiro",
  status: "active",
  selected_organization_id: ORG,
  associations: [
    {
      organization_id: ORG,
      display_name: "Padaria Central",
      slug: "padaria-central",
      roles: ["owner"],
      status: "active",
      permissions: ["product.read", "product.create", "product.family.manage", "recipe.read", "ingredient.read"],
    },
  ],
  roles: ["owner"],
  permissions: ["product.read", "product.create", "product.family.manage", "recipe.read", "ingredient.read"],
};

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
  throw new Error(`Vite não respondeu em ${BASE}`);
}

async function mockApi(page) {
  await page.route("**/api/v1/**", async (route) => {
    const p = new URL(route.request().url()).pathname;
    const json = (data, status = 200) =>
      route.fulfill({ status, contentType: "application/json", body: JSON.stringify(data) });

    if (p.includes("/api/v1/me") || p.endsWith("/me")) return json(me);
    if (p.includes("/product-families")) return json({ items: [{ id: FAMILY_ID, code: "FAM-PAES", display_name: "Pães", status: "active" }] });
    if (p.includes(`/products/${PRODUCT_PURCHASED_ID}`)) {
      return json({ data: productPurchasedFixture, row_version: 1 });
    }
    if (p.includes(`/products/${PRODUCT_READY_ID}`)) {
      return json({ data: productReadyFixture, row_version: 1 });
    }
    if (p.includes(`/products/${PRODUCT_ID}`)) {
      return json({ data: productFixture, row_version: 1 });
    }
    if (p.endsWith("/products")) {
      return json({
        items: [productReadyFixture, productFixture, productPurchasedFixture],
        total: 3,
        limit: 20,
        offset: 0,
      });
    }
    return json({ items: [], total: 0, data: {}, columns: [] });
  });
}

async function signIn(page) {
  await page.goto(`${BASE}/entrar`, { waitUntil: "networkidle" });
  await page.evaluate((org) => {
    sessionStorage.setItem("panne.fakeSession", "1");
    sessionStorage.setItem("panne.demoSubject", "demo-owner");
    localStorage.setItem("panne.activeOrganization", org);
  }, ORG);
  const entrar = page.getByRole("button", { name: /^Entrar/ }).first();
  if (await entrar.count()) {
    await entrar.click();
    await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 20000 });
  }
}

async function openProdutos(page) {
  await page.goto(`${BASE}/produtos`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Como a estrutura de um produto aparece" }).waitFor({
    timeout: 20000,
  });
}

async function shot(page, name) {
  const dest = resolve(outDir, `${name}.png`);
  await page.screenshot({ path: dest, fullPage: true });
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
  );
  console.log(dest, overflow ? "scrollWidth_ok" : "OVERFLOW");
}

const vite = spawn("npx", ["vite", "--port", String(PORT), "--host", "127.0.0.1", "--strictPort"], {
  cwd: root,
  shell: true,
  stdio: "pipe",
});
vite.stdout?.on("data", (chunk) => process.stdout.write(String(chunk)));
vite.stderr?.on("data", (chunk) => process.stderr.write(String(chunk)));

try {
  await waitReady();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await mockApi(page);
  try {
    await page.setViewportSize({ width: 1440, height: 900 });
    await signIn(page);
    await openProdutos(page);
    await shot(page, "01-previa-inicial-1440");

    await page.getByRole("radio", { name: "Visualizar estrutura de Pão francês (Demo)" }).click();
    await page.getByRole("heading", { name: "Estrutura cadastrada" }).waitFor({ timeout: 20000 });
    await page.getByText("Farinha de trigo tipo 1").waitFor({ timeout: 10000 });
    await shot(page, "02-produto-produzido-1440");

    await page.getByRole("radio", { name: "Visualizar estrutura de Refrigerante de cola" }).click();
    await page.getByText("Produção não se aplica a produto comprado.").waitFor({ timeout: 20000 });
    await shot(page, "03-produto-comprado-1440");

    await page.setViewportSize({ width: 390, height: 844 });
    await openProdutos(page);
    const mobile = resolve(outDir, "04-mobile-390.png");
    await page.screenshot({ path: mobile, fullPage: false });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
    );
    console.log(mobile, overflow ? "scrollWidth_ok" : "OVERFLOW");
  } finally {
    await browser.close();
  }
} finally {
  try {
    vite.kill();
  } catch {
    /* ignore */
  }
  if (vite.pid) {
    spawn("taskkill", ["/PID", String(vite.pid), "/T", "/F"], { shell: true, stdio: "ignore" });
  }
  process.exit(0);
}
