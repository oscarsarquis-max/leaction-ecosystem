import { mkdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "apresentacao-028");
await mkdir(shots, { recursive: true });

const companyId = "11111111-1111-4111-8111-111111111111";
const technical = "lojadepaes.YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXo@amount.hub.local";
const person = "cliente.muito.longo.do.comercial@exemplo-padaria.test";
const description =
  "Consulta avulsa de formação de preço com descrição extensa do produto de vitrine para verificar a quebra em duas linhas sem aumentar a altura de cada recebimento.";

function item(partial) {
  return {
    id: partial.id,
    companyId,
    environment: "PRODUCTION",
    transactionId: partial.transactionId,
    orderReference: partial.transactionId,
    processorReference: partial.processorReference ?? null,
    originalStatus: "PAID",
    normalizedStatus: partial.normalizedStatus ?? "CONFIRMED",
    amountMinor: partial.amountMinor ?? null,
    currency: "BRL",
    amountAbsent: partial.amountMinor == null,
    paidAmountMinor: partial.paidAmountMinor ?? null,
    paidAmountAbsent: partial.paidAmountMinor == null,
    reviewRequired: false,
    testLabeled: false,
    classification: partial.classification ?? "INDETERMINATE",
    classificationReason: partial.classificationReason ?? "sem evidência",
    commercialApplication: partial.commercialApplication ?? null,
    commercialDescription: partial.commercialDescription ?? null,
    payerKind: partial.payerKind ?? "ABSENT",
    payerLabel: partial.payerLabel ?? null,
    payerProvenance: partial.payerLabel ? "ACTIONHUB_PAY" : null,
    paymentMethod: partial.paymentMethod ?? null,
    processorName: partial.processorName ?? null,
    providerStatus: partial.providerStatus ?? null,
    pendingKind: partial.pendingKind ?? "ENVIRONMENT_UNPROVEN",
    originCreatedAt: "2026-10-06T15:01:49.498Z",
    originUpdatedAt: partial.originUpdatedAt ?? "2026-10-06T15:01:49.498Z",
    originRevision: "2026-10-06T15:01:49.498Z",
    lastSyncRunId: "run-synthetic",
    lastCorrelationId: "corr-synthetic",
    updatedAt: "2026-10-15T14:00:00Z",
  };
}

const items = [
  item({
    id: "rec-90",
    transactionId: "11111111-2222-4333-8444-555555555590",
    amountMinor: "9000",
    paidAmountMinor: "9000",
    classification: "REAL",
    classificationReason: "live_mode=true",
    commercialApplication: "lojadepaes",
    commercialDescription: description,
    payerKind: "EMAIL",
    payerLabel: person,
    paymentMethod: "pix",
    processorName: "Mercado Pago",
    pendingKind: "NONE",
  }),
  item({
    id: "rec-tech",
    transactionId: "11111111-2222-4333-8444-555555555591",
    amountMinor: "7000",
    commercialApplication: "lojadepaes",
    commercialDescription: "Checkout avulso por valor",
    payerKind: "EMAIL",
    payerLabel: technical,
    paymentMethod: "pix",
    processorName: "Mercado Pago",
    pendingKind: "ENVIRONMENT_UNPROVEN",
  }),
  item({
    id: "rec-absent",
    transactionId: "11111111-2222-4333-8444-555555555592",
    amountMinor: null,
    normalizedStatus: "IN_PROGRESS",
    commercialApplication: "outro-codigo",
    payerKind: "ABSENT",
    pendingKind: "UNPAID_EXPECTED",
    originUpdatedAt: "2026-10-09T11:30:07.370Z",
  }),
  item({
    id: "rec-paid-missing",
    transactionId: "11111111-2222-4333-8444-555555555593",
    amountMinor: "1500",
    classification: "REAL",
    commercialApplication: "lojadepaes",
    commercialDescription: "Sem valor pago confirmado",
    payerKind: "SUBJECT",
    payerLabel: "subj-sintetico-014",
    paymentMethod: "boleto",
    pendingKind: "PAID_AMOUNT_MISSING",
  }),
];

const overview = {
  environment: "PRODUCTION",
  homolog: false,
  createsFinancialMovement: false,
  receiptSyncEnabled: true,
  latestRun: {
    id: "run-synthetic",
    environment: "PRODUCTION",
    status: "SUCCESS",
    rootCorrelationId: "corr-synthetic",
    spiderMessageId: "msg-synthetic",
    resumeCursor: null,
    pageCount: 1,
    importedCount: 1,
    updatedCount: 11,
    reviewCount: 10,
    lastError: null,
    startedAt: "2026-10-15T13:40:00Z",
    finishedAt: "2026-10-15T13:40:08Z",
    monitorUrl: "https://monitor.spider.actionhub.com.br/",
  },
  items,
  reviews: [],
};

const me = {
  actorId: "actor-synthetic",
  displayName: "Operador de conferência com nome longo",
  accessState: "READY",
  permissions: ["titles:read", "titles:write"],
  authorizedCompanies: [{ id: companyId, tenantId: "tenant-synthetic", name: "Loja de Pães", active: true, demo: false }],
  permissionsByCompany: { [companyId]: ["titles:read", "titles:write"] },
};

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:4188";
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
await context.grantPermissions(["clipboard-read", "clipboard-write"]);
const page = await context.newPage();
await page.route("**/api/**", async (route) => {
  const url = route.request().url();
  const json = (body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  if (url.includes("/api/v1/system/info")) {
    return json({ accessMode: "DEMO", receiptSyncEnabled: true, homologIntegration: false, version: "0.1.2" });
  }
  if (url.includes("/api/v1/access/me")) {
    return json(me);
  }
  if (url.includes("/api/v1/pay-receipts/rec-90")) {
    return json({ item: items[0], history: [], run: overview.latestRun, createsFinancialMovement: false });
  }
  if (url.includes("/api/v1/pay-receipts/rec-tech")) {
    return json({ item: items[1], history: [], run: overview.latestRun, createsFinancialMovement: false });
  }
  if (url.includes("/api/v1/pay-receipts?")) {
    return json(overview);
  }
  return json({});
});

async function measure(name) {
  const box = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    zoom: document.documentElement.style.zoom || "1",
    sair: (() => {
      const button = [...document.querySelectorAll("button")].find((node) => node.textContent === "Sair");
      if (!button) return null;
      const rect = button.getBoundingClientRect();
      return { top: rect.top, left: rect.left, width: rect.width, height: rect.height, text: button.textContent };
    })(),
  }));
  const overflow = box.scrollWidth > box.clientWidth + 1;
  const sairClipped = !box.sair || box.sair.width < 20 || box.sair.left < 0 || box.sair.left + box.sair.width > box.clientWidth + 1;
  console.log(JSON.stringify({ name, overflow, sairClipped, ...box }));
  if ((overflow || sairClipped) && !name.includes("zoom")) {
    throw new Error(`layout ${name}`);
  }
}

async function shot(name) {
  await measure(name);
  const target = join(shots, `${name}.png`);
  await page.screenshot({ path: target, fullPage: false });
  const info = await stat(target);
  console.log("wrote " + target + " bytes=" + info.size);
}

await page.goto(baseUrl + "/pay-receipts", { waitUntil: "networkidle" });
await page.getByLabel("Token local").fill("demo-token");
await page.getByRole("button", { name: "Entrar na demonstração" }).click();
await page.getByRole("heading", { name: "Recebimentos ActionHub Pay" }).waitFor();
await page.getByRole("button", { name: "Transações importadas" }).click();
await page.getByText("Pagador não identificado").first().waitFor();

for (const width of [360, 768, 1280, 1848]) {
  await page.setViewportSize({ width, height: 1000 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await shot(`lista-${width}`);
  await page.locator(".top").screenshot({ path: join(shots, `crop-header-${width}.png`) });
  const headerFit = await page.evaluate(() => {
    const name = document.querySelector(".top-user-name");
    const action = [...document.querySelectorAll("button")].find((node) => node.textContent === "Abrir detalhes");
    const nameBox = name?.getBoundingClientRect();
    const actionBox = action?.getBoundingClientRect();
    return {
      name: name?.textContent,
      nameClient: name?.clientWidth,
      nameScroll: name?.scrollWidth,
      nameH: nameBox ? Math.round(nameBox.height) : null,
      actionH: actionBox ? Math.round(actionBox.height) : null,
      actionW: actionBox ? Math.round(actionBox.width) : null,
    };
  });
  console.log("fit" + width + " " + JSON.stringify(headerFit));
  if (width === 360) {
    await page.locator(".pay-receipt-card").first().screenshot({ path: join(shots, "crop-card-360.png") });
  }
}

await page.setViewportSize({ width: 1280, height: 1000 });
await page.getByLabel("Situação").selectOption("CONFIRMED");
await shot("filtro-situacao-1280");
await page.getByRole("button", { name: "Limpar" }).click();

await page.locator(".pay-receipts-table").getByRole("button", { name: "Abrir detalhes" }).first().click();
await page.getByRole("heading", { name: "Recebimento observado" }).waitFor();
await shot("detalhe-90-1280");
await page.getByRole("button", { name: "Voltar aos recebimentos" }).click();
await page.getByRole("heading", { name: "Recebimentos ActionHub Pay" }).waitFor();

await page.setViewportSize({ width: 360, height: 900 });
await page.locator(".pay-receipts-cards").getByRole("button", { name: "Abrir detalhes" }).nth(1).click();
await page.getByRole("heading", { name: "Recebimento observado" }).waitFor();
await page.getByText("Rastreio técnico").click();
await page.getByText("Identificador gerado pelo checkout avulso").first().waitFor();
await page.screenshot({ path: join(shots, "detalhe-tecnico-360-viewport.png") });
await shot("detalhe-tecnico-360");
await page.getByRole("button", { name: "Voltar aos recebimentos" }).click();

await page.setViewportSize({ width: 1600, height: 1000 });
await page.keyboard.down("Control");
for (let step = 0; step < 6; step += 1) {
  await page.keyboard.press("Equal");
}
await page.keyboard.up("Control");
const zoomInfo = await page.evaluate(() => ({ innerWidth: window.innerWidth, devicePixelRatio: window.devicePixelRatio }));
console.log("keyboard_zoom " + JSON.stringify(zoomInfo));
await shot("lista-zoom-200");

await page.getByRole("button", { name: "Copiar referência" }).first().focus();
const focused = await page.evaluate(() => document.activeElement?.textContent ?? "");
console.log("focused=" + focused);
await page.keyboard.press("Tab");
await shot("foco-1280");

await browser.close();
console.log("captures_ok");
