import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "acabamento-visual-007");
const evidence = join(here, "..", "..", "documents", "reviews", "evidence", "acabamento-visual-007");
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:4179";
const companyId = "11111111-1111-1111-1111-111111111111";
const measures = [];
const notes = ["API simulada no Playwright. Não é escrita financeira nem sessão pública."];

const me = {
  actorId: "actor",
  displayName: "Operador com nome extenso da demonstração",
  accessState: "READY",
  permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write"],
  authorizedCompanies: [
    { id: companyId, tenantId: "t", name: "Loja de Pães — unidade centro", active: true, demo: true },
    { id: "22222222-2222-2222-2222-222222222222", tenantId: "t", name: "Segunda empresa autorizada", active: true, demo: true },
  ],
  authorizedCompanyDetails: [
    {
      id: companyId,
      tenantId: "t",
      name: "Loja de Pães — unidade centro",
      active: true,
      demo: true,
      permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write"],
    },
    {
      id: "22222222-2222-2222-2222-222222222222",
      tenantId: "t",
      name: "Segunda empresa autorizada",
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

const categories = [{ id: "cat-1", code: "C1", name: "Insumos", active: true, version: 1 }];

function prefixOf(width) {
  if (width <= 400) return "360";
  if (width < 1024) return "768";
  if (width < 1600) return "1280";
  return "1848";
}

const browser = await chromium.launch({ headless: true });

async function measure(page, name) {
  const box = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    companyWidth: document.querySelector(".top-company")?.getBoundingClientRect().width ?? 0,
    searchWidth: document.querySelector(".filter-search input")?.getBoundingClientRect().width ?? 0,
    checkbox: document.querySelector("input[type=checkbox]")?.getBoundingClientRect().width ?? 0,
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
    if (url.includes("/catalogs/categories")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(categories) });
      return;
    }
    if (url.includes("/pay-receipts") || url.includes("/financial-accounts") || url.includes("/catalogs/")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: url.includes("/pay-receipts")
          ? JSON.stringify({ environment: "PRODUCTION", homolog: false, createsFinancialMovement: false, latestRun: null, items: [] })
          : "[]",
      });
      return;
    }
    if (url.includes("/receivables") || url.includes("/payables")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(emptyList) });
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
  for (const width of [360, 768, 1280, 1848]) {
    const prefix = prefixOf(width);
    const page = await browser.newPage({ viewport: { width, height: width <= 400 ? 900 : 1000 } });
    await installRoutes(page);
    await signIn(page);
    const openFilters = page.getByRole("button", { name: /^(Filtros|Filtros \(ativos\))$/ });
    if (await openFilters.count()) {
      await openFilters.click();
    }
    await page.getByRole("checkbox", { name: "Só vencidos" }).waitFor();
    await shot(page, `${prefix}-receber-filtros`);
    await page.getByRole("combobox", { name: "Categoria" }).click();
    await shot(page, `${prefix}-receber-categoria`);
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: "Pagamentos" }).click();
    await page.getByRole("heading", { name: "Contas a pagar" }).waitFor();
    await shot(page, `${prefix}-pagar-filtros`);
    await page.getByRole("button", { name: "Recebimentos" }).click();
    await page.getByRole("button", { name: "Transações importadas" }).click();
    await page.getByRole("heading", { name: "Recebimentos ActionHub Pay" }).waitFor();
    await shot(page, `${prefix}-importadas`);
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
