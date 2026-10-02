import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "mapa-menus-006");
const evidence = join(here, "..", "..", "documents", "reviews", "evidence", "mapa-menus-006");
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:4179";
const companyId = "11111111-1111-1111-1111-111111111111";
const measures = [];
const notes = ["Capturas com API simulada no Playwright. Não são escritas financeiras nem sessão pública."];

const me = {
  actorId: "actor",
  displayName: "Operador A",
  accessState: "READY",
  permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write"],
  authorizedCompanies: [{ id: companyId, tenantId: "t", name: "Loja demonstração", active: true, demo: true }],
  authorizedCompanyDetails: [
    {
      id: companyId,
      tenantId: "t",
      name: "Loja demonstração",
      active: true,
      demo: true,
      permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write"],
    },
  ],
};

const emptyList = {
  items: [],
  totalItems: 0,
  page: 0,
  size: 20,
  summary: { openCount: 0, openAmountMinor: "0", overdueCount: 0, overdueAmountMinor: "0", draftCount: 0 },
  businessDate: "2026-10-02",
};

function prefixOf(width) {
  if (width <= 400) return "360";
  if (width < 1024) return "768";
  return "1280";
}

const browser = await chromium.launch({ headless: true });

async function measure(page, name) {
  const box = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  measures.push({ name, ...box, overflow: box.scrollWidth > box.clientWidth + 1 });
}

async function shot(page, name) {
  await measure(page, name);
  await page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
}

async function installRoutes(page) {
  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/system/info")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ accessMode: "DEMO", receiptSyncEnabled: true }),
      });
      return;
    }
    if (url.includes("/access/me")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(me) });
      return;
    }
    if (url.includes("/access/csrf")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ token: "t", headerName: "X-XSRF-TOKEN" }),
      });
      return;
    }
    if (url.includes("/pay-receipts")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          environment: "PRODUCTION",
          homolog: false,
          createsFinancialMovement: false,
          latestRun: null,
          items: [],
        }),
      });
      return;
    }
    if (url.includes("/receivables") || url.includes("/payables")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(emptyList) });
      return;
    }
    if (url.includes("/financial-accounts") || url.includes("/catalogs/")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
}

async function signIn(page) {
  await page.goto(`${baseUrl}/receivables`, { waitUntil: "networkidle" });
  if (await page.getByLabel("Token local").count()) {
    await page.getByLabel("Token local").fill("operator-demo-token");
    await page.getByRole("button", { name: "Entrar na demonstração" }).click();
  }
  await page.getByRole("heading", { name: "Contas a receber" }).waitFor({ timeout: 20000 });
}

try {
  for (const width of [360, 768, 1280]) {
    const prefix = prefixOf(width);
    const page = await browser.newPage({ viewport: { width, height: width <= 400 ? 800 : 900 } });
    await installRoutes(page);
    await signIn(page);
    await shot(page, `${prefix}-receber`);
    await page.getByRole("button", { name: "Transações importadas" }).click();
    await page.getByRole("heading", { name: "Recebimentos ActionHub Pay" }).waitFor({ timeout: 15000 });
    await shot(page, `${prefix}-importadas`);
    await page.getByRole("button", { name: "Pagamentos" }).click();
    await page.getByRole("heading", { name: "Contas a pagar" }).waitFor();
    await shot(page, `${prefix}-pagar`);
    await page.getByRole("button", { name: "Contas" }).click();
    await page.getByRole("heading", { name: "Contas financeiras" }).waitFor();
    await shot(page, `${prefix}-contas`);
    await page.getByRole("button", { name: "Cadastros" }).click();
    await page.getByRole("heading", { name: "Clientes e fornecedores" }).waitFor();
    await shot(page, `${prefix}-clientes`);
    await page.getByRole("button", { name: "Categorias" }).click();
    await page.getByRole("heading", { name: "Categorias" }).waitFor();
    await shot(page, `${prefix}-categorias`);
    await page.goto(`${baseUrl}/catalogs`, { waitUntil: "networkidle" });
    if (await page.getByLabel("Token local").count()) {
      await page.getByLabel("Token local").fill("operator-demo-token");
      await page.getByRole("button", { name: "Entrar na demonstração" }).click();
    }
    await page.getByRole("heading", { name: "Clientes e fornecedores" }).waitFor({ timeout: 20000 });
    await shot(page, `${prefix}-catalogs-redirect`);
    await page.close();
  }
} finally {
  await browser.close();
}

const overflow = measures.filter((row) => row.overflow);
await writeFile(join(evidence, "medidas.json"), JSON.stringify({ at: new Date().toISOString(), baseUrl, measures, notes }, null, 2), "utf8");
if (overflow.length) {
  throw new Error(`overflow: ${overflow.map((row) => row.name).join(", ")}`);
}
console.log(JSON.stringify({ shots, count: measures.length, notes }, null, 2));
