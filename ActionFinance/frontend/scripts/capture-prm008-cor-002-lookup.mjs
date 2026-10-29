import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "prm-008-cor-002");
await mkdir(shots, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:5179";
const operator = process.env.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A ?? "";
const titleId = process.env.ACTIONFINANCE_LOOKUP_TITLE_ID ?? "11111111-cccc-4111-a111-111111111301";
const missingTitleId = process.env.ACTIONFINANCE_LOOKUP_MISSING_TITLE_ID ?? "11111111-cccc-4111-a111-111111111302";
const edge = process.env.ACTIONHUB_PAY_EDGE_URL ?? "http://127.0.0.1:8097";
const journeyRef = process.env.ACTIONFINANCE_LOOKUP_REF ?? "pay-homolog-0001";
if (!operator) {
  throw new Error("ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A is required.");
}

const clicks = [];
const measures = [];

function note(step, how) {
  clicks.push({ step, how, at: new Date().toISOString() });
}

async function setFixture(reference, body) {
  const response = await fetch(`${edge}/__test/fixtures/${encodeURIComponent(reference)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`fixture ${reference} HTTP ${response.status}`);
  }
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

async function signIn(page, path) {
  await page.goto(`${baseUrl}${path}`, { waitUntil: "networkidle" });
  if (await page.getByLabel("Token local").count()) {
    await page.getByLabel("Token local").fill(operator);
    await page.getByRole("button", { name: "Entrar na demonstração" }).click();
    note("entrar", "Token local + Entrar na demonstração");
  }
  await page.getByRole("heading", { name: "Acompanhamento no ActionHub Pay" }).waitFor({ timeout: 20000 });
}

async function observation(page) {
  return page.locator("[data-lookup-observation]").innerText();
}

async function attempt(page) {
  return page.locator("[data-lookup-attempt]").innerText();
}

async function expectLookup(page, expectedObservation, expectedAttempt) {
  await page.locator("[data-lookup-observation]").filter({ hasText: expectedObservation }).waitFor({ timeout: 20000 });
  await page.locator("[data-lookup-attempt]").filter({ hasText: expectedAttempt }).waitFor({ timeout: 20000 });
  const observed = await observation(page);
  const tried = await attempt(page);
  if (observed !== expectedObservation) {
    throw new Error(`observação="${observed}" esperada="${expectedObservation}"`);
  }
  if (!tried.includes(expectedAttempt)) {
    throw new Error(`tentativa="${tried}" esperada contém "${expectedAttempt}"`);
  }
  await page.getByText(/título não foi baixado/i).waitFor({ timeout: 5000 });
}

async function consult(page, reference, expectedObservation, expectedAttempt) {
  const input = page.getByLabel("Referência do pagamento de teste");
  await input.fill(reference);
  const button = page.getByRole("button", { name: /Consultar/ });
  await button.focus();
  if ((await page.evaluate(() => document.activeElement?.tagName)) !== "BUTTON") {
    throw new Error("o botão de consulta não recebeu o foco");
  }
  await button.click();
  await expectLookup(page, expectedObservation, expectedAttempt);
}

async function run(width, height, prefix) {
  const page = await browser.newPage({ viewport: { width, height } });
  await signIn(page, `/receivables/${missingTitleId}`);
  await consult(page, "pay-homolog-ausente", "Aguardando envio", "Falha de transporte — observação anterior preservada");
  await page.locator("section.homolog-lookup").getByText(/Não foi possível/).first().waitFor({ timeout: 10000 });
  const missingObservation = await observation(page);
  if (missingObservation === "Confirmado pelo Pay") {
    throw new Error(`${prefix} referência inexistente não pode aparecer como confirmada`);
  }
  note(`${prefix} inexistente`, "pay-homolog-ausente sem confirmação");
  await shot(page, `${prefix}-inexistente`);

  await setFixture(journeyRef, {
    externalStatus: "CONFIRMED",
    deliveryStatus: "DELIVERED",
    amountMinor: "12550",
    currency: "BRL",
    sandbox: true,
  });
  await signIn(page, `/receivables/${titleId}`);
  await consult(page, journeyRef, "Confirmado pelo Pay", "Resposta válida recebida");
  const origin = await page.locator("section.homolog-lookup dt").filter({ hasText: "Origem da resposta" }).locator("xpath=../dd").innerText();
  if (origin !== "Simulador da borda Pay") {
    throw new Error(`${prefix} origem="${origin}" — o simulador precisa estar identificado`);
  }
  await page.getByText("Sem carimbo do provedor").waitFor({ timeout: 5000 });
  note(`${prefix} válida`, "mesma referência confirmada no simulador");
  await shot(page, `${prefix}-confirmada`);

  await setFixture(journeyRef, { fail: "UNAVAILABLE" });
  await consult(page, journeyRef, "Confirmado pelo Pay", "Falha de transporte — observação anterior preservada");
  await page.locator("section.homolog-lookup").getByText(/Não foi possível/).first().waitFor({ timeout: 10000 });
  if ((await observation(page)) !== "Confirmado pelo Pay") {
    throw new Error(`${prefix} indisponibilidade apagou a observação válida`);
  }
  note(`${prefix} indisponível`, "mesma referência, fixture indisponível após observação válida");
  await shot(page, `${prefix}-indisponivel`);

  await setFixture(journeyRef, {
    externalStatus: "CONFIRMED",
    deliveryStatus: "DELIVERED",
    amountMinor: "12550",
    currency: "BRL",
    sandbox: true,
  });
  await consult(page, journeyRef, "Confirmado pelo Pay", "Resposta válida recebida");
  note(`${prefix} recuperação`, "mesma referência após religar fixture");
  await shot(page, `${prefix}-recuperacao`);

  await setFixture(journeyRef, {
    externalStatus: "CONFIRMED",
    deliveryStatus: "DELIVERED",
    amountMinor: "25000",
    currency: "BRL",
    sandbox: true,
  });
  await consult(page, journeyRef, "Requer revisão", "Divergência em revisão");
  if ((await observation(page)) === "Confirmado pelo Pay") {
    throw new Error(`${prefix} divergência deveria exigir revisão sem confirmar de novo`);
  }
  note(`${prefix} divergência`, "mesma referência, valor da fixture alterado");
  await shot(page, `${prefix}-divergencia`);
  await page.close();
}

const browser = await chromium.launch({ headless: true });
try {
  await run(1280, 800, "desktop-1280");
  await run(360, 800, "mobile-360");
} finally {
  await browser.close();
}

await writeFile(
  join(shots, "journey-log.json"),
  JSON.stringify({ when: new Date().toISOString(), baseUrl, journeyRef, clicks, measures, brand: "Action Finance" }, null, 2)
);
console.log(JSON.stringify({ shots, clicks: clicks.length, measures }, null, 2));
