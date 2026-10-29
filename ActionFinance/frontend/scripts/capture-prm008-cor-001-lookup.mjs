import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "prm-008-cor-001");
await mkdir(shots, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:5179";
const operator = process.env.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A ?? "";
const titleId = process.env.ACTIONFINANCE_LOOKUP_TITLE_ID ?? "11111111-cccc-4111-a111-111111111301";
if (!operator) {
  throw new Error("ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A is required.");
}

const clicks = [];
const measures = [];

function note(step, how) {
  clicks.push({ step, how });
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

async function signIn(page) {
  await page.goto(`${baseUrl}/receivables/${titleId}`, { waitUntil: "networkidle" });
  if (await page.getByLabel("Token local").count()) {
    await page.getByLabel("Token local").fill(operator);
    await page.getByRole("button", { name: "Entrar na demonstração" }).click();
    note("entrar", "Token local + Entrar na demonstração");
  }
  await page.getByRole("heading", { name: "Acompanhamento no ActionHub Pay" }).waitFor({ timeout: 20000 });
}

async function run(width, height, prefix) {
  const page = await browser.newPage({ viewport: { width, height } });
  await signIn(page);
  await shot(page, `${prefix}-consulta-inicial`);
  const input = page.getByLabel("Referência do pagamento de teste");
  await input.fill("pay-homolog-ausente");
  await page.getByRole("button", { name: /Consultar/ }).click();
  note(`${prefix} falha`, "referência ausente no simulador");
  await page.getByText(/não encontrado|indisponível|revisão|preservada|recusou/i).first().waitFor({ timeout: 20000 }).catch(() => {});
  await shot(page, `${prefix}-falha`);
  await input.fill("pay-homolog-0001");
  await page.getByRole("button", { name: /Consultar/ }).click();
  note(`${prefix} confirmação`, "fixture pay-homolog-0001");
  await page.getByText(/Confirmado pelo Pay|Requer revisão|Simulador/).first().waitFor({ timeout: 20000 });
  await shot(page, `${prefix}-observacao`);
  await input.fill("pay-homolog-refunded");
  await page.getByRole("button", { name: /Consultar/ }).click();
  note(`${prefix} estorno`, "fixture pay-homolog-refunded sem baixa automática");
  await page.getByText(/Estornado pelo Pay|Requer revisão|vinculada a outro título/).first().waitFor({ timeout: 20000 }).catch(() => {});
  await shot(page, `${prefix}-revisao`);
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
  JSON.stringify({ when: new Date().toISOString(), baseUrl, clicks, measures, brand: "Action Finance" }, null, 2)
);
console.log(JSON.stringify({ shots, clicks: clicks.length, measures }, null, 2));
