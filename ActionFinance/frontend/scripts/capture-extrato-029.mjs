import { mkdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "extrato-029");
await mkdir(shots, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_CAPTURE_URL ?? "http://127.0.0.1:5179";
const companyId = "11111111-1111-4111-a111-111111111111";
const longText = "Pagamento de formação de preço da vitrine com descrição longa o bastante para ocupar a linha inteira e não pode empurrar o valor para fora da tela do celular.";
let showLines = false;

const line = {
  id: "line-1",
  accountId: "acc-1",
  sourceId: "pay-sint-100",
  recordType: "SETTLEMENT",
  externalReference: "order-sint-100",
  description: longText,
  effectiveOn: "2026-10-01",
  direction: "IN",
  eventKind: "SETTLEMENT",
  balanceEffect: "AFFECTS",
  grossMinor: 9000,
  grossAbsent: false,
  feeMinor: 500,
  feeAbsent: false,
  netMinor: 8500,
  netAbsent: false,
  classificationState: "UNCLASSIFIED",
  initiativeState: "UNASSIGNED",
  importStatus: "ACTIVE",
  suggestions: [{
    receiptId: "rec-sint-1",
    strength: "QUALIFIED",
    namespace: "MP_PAYMENT",
    reason: "A referência do pagamento no extrato coincide com a referência do processador no recebimento.",
    divergence: "Líquido do extrato difere do pago do recebimento.",
  }],
  originalRows: ["2026-10-01,pay-sint-100,SETTLEMENT,85.00"],
};

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await page.route("**/api/**", async (route) => {
  const url = route.request().url();
  const json = (body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  if (url.includes("/system/info")) {
    return json({ accessMode: "DEMO", version: "0.2.0", receiptSyncEnabled: true });
  }
  if (url.includes("/access/me")) {
    return json({
      actorId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
      displayName: "Operador laboratório",
      permissions: [],
      authorizedCompanies: [{ id: companyId, tenantId: "t", name: "Loja de Pães", active: true, demo: true }],
      authorizedCompanyDetails: [{
        id: companyId,
        tenantId: "t",
        name: "Loja de Pães",
        active: true,
        demo: true,
        permissions: ["financial-accounts:read", "financial-accounts:write", "titles:read", "system:read", "company-context:read"],
      }],
    });
  }
  if (url.includes("/financial-accounts")) {
    return json([{ id: "acc-1", name: "Conta laboratório", type: "BANK", active: true, currentBalanceMinor: "0" }]);
  }
  if (url.includes("/statement-previews") && route.request().method() === "POST") {
    return json({
      id: "prev-1",
      previewToken: "a".repeat(64),
      accountId: "acc-1",
      linkedRef: "mp-conta-sintetica",
      profileId: "mp-account-money-csv-1",
      recognized: true,
      fileDiagnostic: null,
      blockReason: null,
      confirmBlocked: false,
      accountEvidenceRequired: false,
      currencyAssumed: false,
      periodFrom: "2026-10-01",
      periodTo: "2026-10-02",
      rows: [
        { lineNumber: 2, description: longText, effectiveOn: "2026-10-01", direction: "IN", eventKind: "SETTLEMENT", netMinor: 8500, netAbsent: false, eligible: true },
        { lineNumber: 3, description: "Sem líquido informado", effectiveOn: "2026-10-02", direction: "NONE", eventKind: "SETTLEMENT", netMinor: null, netAbsent: true, eligible: false },
      ],
      issues: [{ lineNumber: 4, code: "UNSUPPORTED_CURRENCY", message: "Moeda USD sem regra de conversão. Nenhuma conversão foi feita." }],
    });
  }
  if (url.includes("/statement-lines/line-1")) {
    return json(line);
  }
  if (url.includes("/statement-lines")) {
    return json(showLines
      ? { page: 0, size: 20, total: 1, creditMinor: "8500", creditCount: 1, debitMinor: "0", debitCount: 0, availabilityCount: 0, amountAbsentCount: 0, items: [line], imported: 1 }
      : { page: 0, size: 20, total: 0, creditMinor: "0", creditCount: 0, debitMinor: "0", debitCount: 0, availabilityCount: 0, amountAbsentCount: 0, items: [], imported: 0 });
  }
  if (url.includes("/statement-links")) {
    return json([{ id: "link-1", accountId: "acc-1", externalRef: "mp-conta-sintetica", provenance: "vínculo sintético de laboratório" }]);
  }
  if (url.includes("/statement-batches")) {
    return json(showLines ? [{
      id: "batch-1", fileName: "extrato-sintetico.csv", status: "CONFIRMED", profileId: "mp-account-money-csv-1",
      periodFrom: "2026-10-01", periodTo: "2026-10-01", createdCount: 1, enrichedCount: 0, unchangedCount: 0, rejectedCount: 1, withdrawReason: null,
    }] : []);
  }
  return json({});
});

async function shot(name) {
  const box = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  if (box.scrollWidth > box.clientWidth + 1) {
    throw new Error(`overflow ${name} ${box.scrollWidth}>${box.clientWidth}`);
  }
  const target = join(shots, `${name}.png`);
  await page.screenshot({ path: target, fullPage: false });
  const info = await stat(target);
  console.log(JSON.stringify({ name, bytes: info.size, ...box }));
}

await page.goto(baseUrl + "/financial-accounts/statement", { waitUntil: "networkidle" });
await page.getByLabel("Token local").fill("demo-token");
await page.getByRole("button", { name: "Entrar na demonstração" }).click();
await page.getByRole("heading", { name: "Extrato" }).waitFor();
await page.getByText("Extrato não importado.").waitFor();
await page.getByRole("button", { name: "Extrato" }).waitFor();
await shot("vazio-1280");

await page.setViewportSize({ width: 390, height: 844 });
await page.evaluate(() => window.scrollTo(0, 0));
const file = await page.locator("input[type=file]");
await file.setInputFiles({ name: "extrato.csv", mimeType: "text/csv", buffer: Buffer.from("a") });
await page.getByText("Moeda USD sem regra de conversão.").waitFor();
await page.locator(".statement-cards").getByText("Não informado").scrollIntoViewIfNeeded();
await shot("previa-390");
await page.setViewportSize({ width: 1280, height: 1100 });
await page.locator(".statement-preview").scrollIntoViewIfNeeded();
await shot("previa-1280");

await page.getByRole("button", { name: "Cancelar prévia" }).click();
showLines = true;
await page.getByLabel("Direção").selectOption("IN");
await page.getByText("Entradas que afetam disponibilidade").waitFor();
await shot("lista-1280");
await page.getByRole("button", { name: "Abrir" }).first().click();
await page.getByText("Não classificada").waitFor();
await page.getByText("Não atribuída").waitFor();
await page.getByText("R$ 5,00").waitFor();
await page.getByText("A tarifa desta linha explica a composição.").waitFor();
await shot("detalhe-1280");
await page.getByRole("button", { name: "Voltar" }).click();
await page.setViewportSize({ width: 390, height: 844 });
await page.evaluate(() => window.scrollTo(0, 0));
await page.locator(".statement-cards").getByText(longText).scrollIntoViewIfNeeded();
await shot("lista-390");

await browser.close();
