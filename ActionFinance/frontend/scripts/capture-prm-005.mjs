import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "prm-005");
const evidence = join(here, "..", "..", "documents", "reviews", "evidence", "prm-005");
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:5179";
const operator = process.env.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A ?? "";
const viewer = process.env.ACTIONFINANCE_DEMO_TOKEN_VIEWER_A ?? "";
if (!operator || !viewer) {
  throw new Error("ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A and ACTIONFINANCE_DEMO_TOKEN_VIEWER_A are required.");
}

const clicks = [];
const measures = [];
const created = [];
const inspected = [];

function note(step, how) {
  clicks.push({ step, how });
}

function prefixOf(width) {
  if (width <= 400) return "mobile-360";
  if (width < 1024) return "tablet-768";
  return "desktop-1280";
}

const browser = await chromium.launch({ headless: true });

async function signIn(page, token, path, ready) {
  await page.goto(`${baseUrl}${path}`, { waitUntil: "networkidle" });
  if (await page.getByLabel("Token local").count()) {
    await page.getByLabel("Token local").fill(token);
    await page.getByRole("button", { name: "Entrar na demonstração" }).click();
    note(`entrar ${path}`, "automatizado: preencheu Token local e clicou Entrar na demonstração");
  }
  await page.getByRole("heading", { name: ready }).or(page.getByText(ready, { exact: false })).first().waitFor({ timeout: 20000 });
}

async function measure(page, name) {
  const box = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  measures.push({ name, ...box });
  if (box.scrollWidth > box.clientWidth + 1) {
    throw new Error(`overflow ${name}: scrollWidth=${box.scrollWidth} clientWidth=${box.clientWidth}`);
  }
}

async function shot(page, name) {
  await measure(page, name);
  await page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
}

async function goNav(page, width, name) {
  if (width <= 1023) {
    await page.getByRole("button", { name: "Menu" }).click();
  }
  await page.getByRole("button", { name }).click();
}

async function selectLabeled(page, label, index = 1) {
  await page.locator("label.searchable, label").filter({ hasText: label }).locator("select").selectOption({ index });
}

async function selectAccount(page, accountName) {
  const box = page.locator("label.searchable").filter({ hasText: "Conta financeira" });
  await box.getByLabel("Buscar Conta financeira").fill(accountName);
  await box.locator("select").selectOption({ label: accountName });
}

async function captureLoginAndError() {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await page.goto(`${baseUrl}/receivables`, { waitUntil: "networkidle" });
  await page.getByLabel("Token local").waitFor();
  const filled = await page.getByLabel("Token local").inputValue();
  if (filled) {
    throw new Error("login screenshot would expose a token value");
  }
  note("entrada demo", "inspecionado: tela de entrada sem token preenchido");
  await shot(page, "login-1280");
  await page.setViewportSize({ width: 360, height: 800 });
  await shot(page, "login-360");
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.getByLabel("Token local").fill("token-invalido-prm-005");
  await page.getByRole("button", { name: "Entrar na demonstração" }).click();
  await page.getByRole("alert").waitFor({ timeout: 15000 });
  note("erro de entrada", "automatizado: token inválido e alerta acessível");
  await page.getByLabel("Token local").fill("");
  await shot(page, "login-error-1280");
  await page.close();
}

async function runJourney(width, height) {
  const prefix = prefixOf(width);
  const stamp = `${prefix}-${Date.now()}`;
  const accountName = `Conta jornada PRM 005 ${stamp}`;
  const receivableName = `Recebível jornada PRM 005 ${stamp}`;
  const payableName = `Obrigação jornada PRM 005 ${stamp}`;
  created.push({ viewport: prefix, accountName, receivableName, payableName });
  const page = await browser.newPage({ viewport: { width, height } });

  await signIn(page, operator, "/financial-accounts/new", "Nova conta financeira");
  await page.getByLabel("Nome").fill(accountName);
  await page.getByLabel("Tipo").selectOption("CASH");
  await page.getByLabel("Início do controle").fill("2026-09-01");
  await page.getByLabel("Saldo inicial").fill("200,00");
  note("criar conta", "automatizado: nome/tipo/2026-09-01/200,00 e Criar conta");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await page.getByRole("heading", { name: accountName }).waitFor({ timeout: 20000 });
  await page
    .locator(".desktop-table td, .movement-card, .cards li")
    .locator("visible=true")
    .filter({ hasText: /Saldo inicial informado|Abertura/ })
    .first()
    .waitFor({ timeout: 20000 });
  await shot(page, `${prefix}-account-created`);

  await goNav(page, width, "A receber");
  await page.getByRole("heading", { name: "Contas a receber" }).waitFor();
  await page.waitForFunction(() => {
    const value = document.querySelector(".financial-summary strong")?.textContent?.trim();
    return Boolean(value && value !== "…");
  }, null, { timeout: 20000 });
  await shot(page, `${prefix}-list`);
  await page.getByRole("button", { name: "Novo recebível" }).click();
  await page.getByRole("heading", { name: "Novo recebível" }).waitFor();
  await shot(page, `${prefix}-form`);
  await page.getByLabel(/Descrição/).fill(receivableName);
  await selectLabeled(page, "Cliente / pagador");
  await page.getByLabel("Valor (BRL)").fill("150,00");
  await page.getByLabel("Competência").fill("2026-09-15");
  await page.getByLabel("Vencimento").fill("2026-09-30");
  await selectLabeled(page, "Categoria");
  note("criar recebível 150", "automatizado: formulário Novo recebível + Registrar");
  await page.getByRole("button", { name: "Registrar" }).click();
  await page.getByText(receivableName).first().waitFor({ timeout: 20000 });
  await page.getByText("R$ 150,00").first().waitFor();
  await shot(page, `${prefix}-detail`);

  await page.getByRole("button", { name: "Registrar recebimento" }).click();
  await page.getByRole("heading", { name: "Registrar recebimento realizado" }).waitFor();
  await selectAccount(page, accountName);
  await page.getByLabel("Valor").fill("50,00");
  await page.getByLabel("Meio").selectOption("PIX");
  note("baixa 50", "automatizado: conta da jornada, 50,00, Pix e Registrar recebimento");
  await page.getByRole("button", { name: "Registrar recebimento" }).click();
  await page.getByText("R$ 100,00").first().waitFor({ timeout: 20000 });

  await page.getByRole("button", { name: "Registrar recebimento" }).click();
  await selectAccount(page, accountName);
  await page.getByLabel("Valor").fill("100,00");
  await page.getByLabel("Meio").selectOption("PIX");
  note("baixa 100", "automatizado: 100,00 e Registrar recebimento");
  await page.getByRole("button", { name: "Registrar recebimento" }).click();
  await page.getByText("Recebido").first().waitFor({ timeout: 20000 });
  await page.getByText("R$ 0,00").first().waitFor();

  await page
    .locator(".desktop-table tbody tr, .cards li")
    .locator("visible=true")
    .filter({ hasText: "R$ 50,00" })
    .locator("a")
    .first()
    .click();
  note("abrir baixa 50", "automatizado: vínculo da baixa de R$ 50,00");
  await page.getByRole("heading", { name: "Registro de baixa" }).waitFor();
  await page.getByRole("button", { name: "Estornar registro" }).click();
  await page.getByRole("heading", { name: /Estornar/ }).waitFor();
  await shot(page, `${prefix}-modal`);
  await page.getByLabel("Motivo").fill("Estorno da jornada PRM 005");
  note("estorno 50", "automatizado: diálogo Estornar registro + Confirmar estorno do registro");
  await page.getByRole("button", { name: "Confirmar estorno do registro" }).click();
  await page.getByText("Estornado").first().waitFor({ timeout: 20000 });

  await page.getByRole("link").filter({ hasText: /REC-|Recebível/ }).first().click();
  await page.getByText("R$ 50,00").first().waitFor({ timeout: 20000 });

  await goNav(page, width, "Contas financeiras");
  await page.getByRole("link", { name: accountName }).locator("visible=true").first().click();
  await page.getByRole("heading", { name: accountName }).waitFor({ timeout: 20000 });
  await page.getByText("Extrato gerencial").waitFor({ timeout: 20000 });
  await page.getByText(/Saldo inicial informado|Abertura|Saldo anterior/).first().waitFor({ timeout: 20000 });
  if (width <= 400) {
    await page.locator(".movement-card").filter({ hasText: "Entrada: R$ 50,00" }).first().waitFor({ timeout: 20000 });
    await page.locator(".movement-card").filter({ hasText: "Saída: R$ 50,00" }).first().waitFor({ timeout: 20000 });
    await page.locator(".movement-card p").filter({ hasText: /^Estorno do registro$/ }).waitFor({ timeout: 20000 });
    await page.locator(".movement-card").filter({ hasText: "Saldo após:" }).first().waitFor();
  }
  await shot(page, `${prefix}-statement`);

  if (width <= 400) {
    await page.getByRole("button", { name: "Menu" }).click();
    await page.getByRole("button", { name: "A pagar" }).waitFor();
    note("menu mobile", "automatizado: drawer navy aberto em 360");
    await shot(page, `${prefix}-menu-open`);
    await page.getByRole("button", { name: "A pagar" }).click();
  } else {
    await goNav(page, width, "A pagar");
  }
  await page.getByRole("button", { name: "Nova conta a pagar" }).click();
  await page.getByLabel(/Descrição/).fill(payableName);
  await selectLabeled(page, "Fornecedor / favorecido");
  await page.getByLabel("Valor (BRL)").fill("150,00");
  await page.getByLabel("Competência").fill("2026-09-15");
  await page.getByLabel("Vencimento").fill("2026-09-30");
  await selectLabeled(page, "Categoria");
  note("criar obrigação 150", "automatizado: Nova conta a pagar + Registrar");
  await page.getByRole("button", { name: "Registrar" }).click();
  await page.getByText(payableName).first().waitFor({ timeout: 20000 });
  await page.getByRole("button", { name: "Registrar pagamento" }).click();
  await selectAccount(page, accountName);
  await page.getByLabel("Valor").fill("50,00");
  await page.getByLabel("Meio").selectOption("CASH");
  note("pagamento 50", "automatizado: pagamento de 50,00 em dinheiro na conta da jornada");
  await page.getByRole("button", { name: "Registrar pagamento" }).click();
  await page.getByText("R$ 100,00").first().waitFor({ timeout: 20000 });
  await shot(page, `${prefix}-payable-partial`);

  await page.getByRole("button", { name: "Sair" }).click();
  await signIn(page, viewer, "/receivables", "Contas a receber");
  note("perfil consulta", "automatizado: Sair + token do visualizador A");
  await page.getByText(receivableName).locator("visible=true").first().waitFor({ timeout: 20000 });
  if (await page.getByRole("button", { name: "Novo recebível" }).count()) {
    throw new Error("viewer still has write button Novo recebível");
  }
  await page.getByText(receivableName).locator("visible=true").first().click();
  if (await page.getByRole("button", { name: /Registrar recebimento|Corrigir/ }).count()) {
    throw new Error("viewer still has title write actions");
  }
  await shot(page, `${prefix}-viewer`);
  await page.close();
}

async function captureZoom200() {
  const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
  await signIn(page, operator, "/receivables", "Contas a receber");
  await page.evaluate(() => {
    document.documentElement.style.zoom = "2";
  });
  note("zoom 200%", "inspecionado: lista a receber com zoom CSS 200% em viewport 1280");
  inspected.push("lista a receber em zoom 200% desktop");
  await shot(page, "desktop-1280-zoom-200-list");
  await page.close();
}

try {
  await captureLoginAndError();
  await runJourney(1280, 800);
  await runJourney(768, 900);
  await runJourney(360, 800);
  await captureZoom200();
  const summary = {
    ok: true,
    baseUrl,
    shots,
    created,
    inspected,
    automation:
      "Playwright headless clicou e preencheu os formulários nas jornadas 1280/768/360. Login sem token visível. Erro de entrada e menu mobile capturados. Persistência pela API real, não por mock.",
    clicks,
    measures,
  };
  await writeFile(join(shots, "journey-log.json"), JSON.stringify(summary, null, 2));
  await writeFile(join(evidence, "journey-log.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
} finally {
  await browser.close();
}
