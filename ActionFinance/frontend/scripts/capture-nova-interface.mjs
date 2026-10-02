import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "nova-interface");
const evidence = join(here, "..", "..", "documents", "reviews", "evidence", "nova-interface");
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:5179";
const companyId = "11111111-1111-1111-1111-111111111111";
const measures = [];
const notes = ["Capturas com API simulada no browser. Não são escritas financeiras nem Cognito real."];

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

const pendingItem = {
  id: "rec-1",
  companyId,
  environment: "PRODUCTION",
  transactionId: "tx-abc-12345678",
  orderReference: "PED-aabbccddeeff0011",
  processorReference: "mp-99887766",
  originalStatus: "approved",
  normalizedStatus: "CONFIRMED",
  amountMinor: "1500",
  currency: "BRL",
  amountAbsent: false,
  paidAmountMinor: null,
  paidAmountAbsent: true,
  reviewRequired: false,
  testLabeled: false,
  classification: "INDETERMINATE",
  classificationReason: "sem evidência",
  originCreatedAt: "2026-09-01T10:00:00Z",
  originUpdatedAt: "2026-09-28T12:00:00Z",
  originRevision: "rev-1",
  lastSyncRunId: "run-1",
  lastCorrelationId: "corr-1",
  updatedAt: "2026-09-28T12:00:00Z",
};

const payOverview = {
  environment: "PRODUCTION",
  homolog: false,
  createsFinancialMovement: false,
  latestRun: {
    id: "run-1",
    environment: "PRODUCTION",
    status: "EMPTY",
    rootCorrelationId: "corr-1",
    spiderMessageId: "msg-1",
    resumeCursor: null,
    pageCount: 1,
    importedCount: 0,
    updatedCount: 0,
    reviewCount: 1,
    lastError: null,
    startedAt: "2026-09-28T12:00:00Z",
    finishedAt: "2026-09-28T12:01:00Z",
    monitorUrl: null,
  },
  items: [],
  reviews: [pendingItem],
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

async function installRoutes(page, mode) {
  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    const method = route.request().method();
    if (url.includes("/system/info")) {
      const body =
        mode === "oidc"
          ? { accessMode: "OIDC", receiptSyncEnabled: true }
          : { accessMode: "DEMO", homologIntegration: true, receiptSyncEnabled: true };
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
      return;
    }
    if (url.includes("/access/me")) {
      if (mode === "oidc") {
        await route.fulfill({ status: 401, contentType: "application/json", body: "{}" });
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(me) });
      return;
    }
    if (url.includes("/access/csrf")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ token: "t", headerName: "X-XSRF-TOKEN" }) });
      return;
    }
    if (url.includes("/pay-receipts/rec-1")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ item: pendingItem, history: [], run: payOverview.latestRun, createsFinancialMovement: false }),
      });
      return;
    }
    if (url.includes("/pay-receipts") && method === "GET") {
      if (mode === "empty") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ...payOverview, latestRun: null, reviews: [], items: [] }),
        });
        return;
      }
      if (mode === "fail") {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ code: "UNAVAILABLE", message: "A origem não respondeu. Os itens já importados foram preservados." }),
        });
        return;
      }
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payOverview) });
      return;
    }
    if (url.includes("/receivables") || url.includes("/payables")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(emptyList) });
      return;
    }
    if (url.includes("/financial-accounts") && !url.includes("/movements")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
      return;
    }
    if (url.includes("/catalogs/")) {
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
    const viewport = { width, height: width <= 400 ? 800 : 900 };

    const oidc = await browser.newPage({ viewport });
    await oidc.route("**/oauth2/**", (route) => route.abort());
    await installRoutes(oidc, "oidc");
    await oidc.goto(`${baseUrl}/?login=failed`, { waitUntil: "domcontentloaded" });
    const reenter = oidc.getByRole("button", { name: /Entrar novamente|Entrar/ });
    await reenter.first().waitFor({ timeout: 15000 });
    await shot(oidc, `${prefix}-entrada-oidc-falha`);
    await oidc.close();

    const page = await browser.newPage({ viewport });
    await installRoutes(page, "pending");
    await page.goto(`${baseUrl}/`, { waitUntil: "networkidle" });
    await shot(page, `${prefix}-entrada-demo`);
    await signIn(page);
    await shot(page, `${prefix}-receber`);
    if (width <= 1023) {
      await page.getByRole("navigation", { name: "Principal móvel" }).getByRole("button", { name: "Mais" }).click();
    } else {
      await page.getByRole("navigation", { name: "Áreas" }).getByRole("button", { name: "Mais" }).click();
    }
    await shot(page, `${prefix}-mais`);
    await page.keyboard.press("Escape");
    await page.getByRole("button", { name: "Recebimentos ActionHub Pay" }).first().click();
    await page.getByRole("heading", { name: "Recebimentos ActionHub Pay" }).waitFor();
    await shot(page, `${prefix}-pay-pendencia`);
    await page.getByRole("button", { name: /Abrir/ }).first().click();
    await page.getByRole("heading", { name: "Recebimento observado" }).waitFor();
    await shot(page, `${prefix}-pay-detalhe`);
    if (width <= 1023) {
      await page.getByRole("navigation", { name: "Principal móvel" }).getByRole("button", { name: "Pagar" }).click();
    } else {
      await page.getByRole("navigation", { name: "Áreas" }).getByRole("button", { name: "Pagamentos" }).click();
    }
    await page.getByRole("heading", { name: "Contas a pagar" }).waitFor();
    await shot(page, `${prefix}-pagar`);
    if (width <= 1023) {
      await page.getByRole("navigation", { name: "Principal móvel" }).getByRole("button", { name: "Contas" }).click();
    } else {
      await page.getByRole("navigation", { name: "Áreas" }).getByRole("button", { name: "Contas e caixa" }).click();
    }
    await page.getByRole("heading", { name: /Contas financeiras/ }).waitFor();
    await shot(page, `${prefix}-contas`);
    await page.close();

    const empty = await browser.newPage({ viewport });
    await installRoutes(empty, "empty");
    await signIn(empty);
    await empty.getByRole("button", { name: "Recebimentos ActionHub Pay" }).first().click();
    await empty.getByText(/Nenhum recebimento importado/).waitFor();
    await shot(empty, `${prefix}-pay-vazio`);
    await empty.close();

    const fail = await browser.newPage({ viewport });
    await installRoutes(fail, "fail");
    await signIn(fail);
    await fail.getByRole("button", { name: "Recebimentos ActionHub Pay" }).first().click();
    await fail.getByRole("alert").waitFor();
    await shot(fail, `${prefix}-pay-falha`);
    await fail.close();
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
