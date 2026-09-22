import { chromium, devices } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const OUT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../documentacao/evidencias/r028-003-critical-map/screenshots",
);
const BASE = "https://demo.panne.ia.br";

async function login(page, subject = "demo-owner") {
  await page.goto(`${BASE}/entrar`, { waitUntil: "domcontentloaded", timeout: 60000 });
  const select = page.locator("select").first();
  if (await select.count()) await select.selectOption(subject).catch(() => {});
  await page.getByRole("button", { name: "Entrar na demonstração" }).click();
  await page.waitForURL(/\/(fluxo|organizacao)/, { timeout: 45000 });
  if (page.url().includes("/organizacao")) {
    await page.getByText("Panne Demonstração", { exact: true }).click({ force: true });
    await page.waitForURL(/\/fluxo/, { timeout: 45000 });
  }
  await page.getByRole("heading", { name: "Fluxo produtivo" }).waitFor({ timeout: 45000 });
}

async function shot(page, name) {
  await mkdir(OUT, { recursive: true });
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true });
  console.log("saved", name);
}

const browser = await chromium.launch({ headless: true });
const desktop = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await desktop.newPage();
await login(page);
await shot(page, "01-visao-geral-desktop");
await page.goto(`${BASE}/fluxo?etapa=8`);
await page.getByRole("heading", { name: "Fluxo produtivo" }).waitFor();
await page.waitForTimeout(1500);
await shot(page, "05-foco-diferente-posicao");

const codes = ["PAO-TRAD", "PAO-FR", "REF-COLA", "COCA", "BRIOCHE"];
for (const code of codes) {
  await page.goto(`${BASE}/fluxo?modo=produto&produto=${code}`);
  await page.waitForTimeout(2000);
  const body = await page.locator(".flow-page").innerText().catch(() => "");
  if (/não encontrado/i.test(body)) continue;
  if (/parado em Receitas|Você está aqui[\s\S]*Receitas|Receitas[\s\S]*Você está aqui/i.test(body) && !/02-/.test("")) {
    await shot(page, "02-produzido-bloqueado-receita");
  }
  if (/parado em Preparo|Preparo e execução[\s\S]*Você está aqui|Você está aqui[\s\S]*Preparo/i.test(body)) {
    await shot(page, "03-produzido-pronto-execucao");
  }
  if (/produto comprado|Não se aplica — produto comprado/i.test(body)) {
    await shot(page, "04-comprado-nao-aplicavel");
  }
}
await desktop.close();

const mobile = await browser.newContext({ ...devices["iPhone 12"] });
const m = await mobile.newPage();
await login(m);
await shot(m, "06-mobile");
await mobile.close();

const tablet = await browser.newContext({ viewport: { width: 768, height: 1024 } });
const t = await tablet.newPage();
await login(t);
await shot(t, "07-tablet");
await tablet.close();

const reader = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const r = await reader.newPage();
await login(r, "demo-reader");
await r.goto(`${BASE}/fluxo`);
await r.waitForTimeout(2000);
await shot(r, "08-perfil-sem-custos");
await reader.close();

await browser.close();
console.log("done", OUT);
