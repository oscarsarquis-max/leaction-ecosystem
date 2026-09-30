import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "prm-004");
await mkdir(shots, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:5179";
const token = process.env.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A ?? "";
if (!token) {
  throw new Error("ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A is required for capture.");
}

const partialTitle = "11111111-cccc-4111-a111-111111111309";
const bankAccount = "11111111-dddd-4111-a111-111111111401";
const partialSettlement = "11111111-eeee-4111-a111-111111111501";
const browser = await chromium.launch({ headless: true });
const measures = [];

async function signIn(page, path, ready) {
  await page.goto(`${baseUrl}${path}`, { waitUntil: "networkidle" });
  if (await page.getByLabel("Token local").count()) {
    await page.getByLabel("Token local").fill(token);
    await page.getByRole("button", { name: "Entrar na demonstração" }).click();
  }
  await page
    .getByRole("heading", { name: ready })
    .or(page.getByText(ready, { exact: false }))
    .first()
    .waitFor({ timeout: 15000 });
}

async function measure(page, name) {
  const box = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
    tableVisible: document.querySelector(".desktop-table")
      ? getComputedStyle(document.querySelector(".desktop-table")).display
      : "none",
    cardsVisible: document.querySelector(".cards") ? getComputedStyle(document.querySelector(".cards")).display : "none",
  }));
  measures.push({ name, ...box });
  if (box.scrollWidth > box.clientWidth + 1) {
    throw new Error(`overflow ${name}: scrollWidth=${box.scrollWidth} clientWidth=${box.clientWidth}`);
  }
}

async function captureViewport(name, width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  await signIn(page, "/receivables", "Contas a receber");
  await page.getByText(/R\$ \d/).first().waitFor({ timeout: 15000 });
  await page.locator(".desktop-table tbody tr, .cards li").locator("visible=true").first().waitFor({ timeout: 15000 });
  await measure(page, `${name}-receivables`);
  await page.screenshot({ path: join(shots, `${name}-receivables.png`), fullPage: true });

  await signIn(page, `/receivables/${partialTitle}`, "Restante");
  await page.getByText("Recebível demonstrativo de R$ 150").first().waitFor();
  await page
    .locator(".desktop-table tbody tr, .cards li")
    .filter({ hasText: /Pix|Estornado|Ativo/ })
    .locator("visible=true")
    .first()
    .waitFor({ timeout: 15000 });
  await measure(page, `${name}-title-detail`);
  await page.screenshot({ path: join(shots, `${name}-title-detail.png`), fullPage: true });

  await signIn(page, `/receivables/${partialTitle}/settlements/new`, "Registrar recebimento realizado");
  await page.getByText(/Não envia nem movimenta dinheiro/).waitFor();
  await measure(page, `${name}-settlement-form`);
  await page.screenshot({ path: join(shots, `${name}-settlement-form.png`), fullPage: true });

  await signIn(page, "/financial-accounts", "Contas financeiras");
  await measure(page, `${name}-accounts`);
  await page.screenshot({ path: join(shots, `${name}-accounts.png`), fullPage: true });

  await signIn(page, `/financial-accounts/${bankAccount}`, "Conta demonstrativa Banco Exemplo");
  await page.getByText(/não conciliado com o banco/i).waitFor();
  await page.getByText(/Saldo anterior ao período/).waitFor({ timeout: 15000 });
  await page.getByText("Saldo inicial informado").locator("visible=true").first().waitFor({ timeout: 15000 });
  await measure(page, `${name}-statement`);
  await page.screenshot({ path: join(shots, `${name}-statement.png`), fullPage: true });

  await signIn(page, `/settlements/${partialSettlement}`, "Registro de baixa");
  await page.getByText(/Conta demonstrativa Banco Exemplo|Pix/).first().waitFor();
  if (await page.getByRole("button", { name: "Estornar registro" }).count()) {
    await page.getByRole("button", { name: "Estornar registro" }).click();
    await page.getByText(/Nenhuma devolução ou operação bancária será enviada/).waitFor();
    await measure(page, `${name}-reversal-modal`);
    await page.screenshot({ path: join(shots, `${name}-reversal-modal.png`), fullPage: true });
    await page.getByRole("button", { name: "Voltar" }).click();
  }
  await page.close();
}

try {
  await captureViewport("desktop-1280", 1280, 800);
  await captureViewport("mobile-360", 360, 800);
  console.log(JSON.stringify({ ok: true, baseUrl, shots, measures }, null, 2));
} finally {
  await browser.close();
}
