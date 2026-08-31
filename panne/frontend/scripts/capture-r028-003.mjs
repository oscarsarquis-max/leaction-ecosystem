/**
 * Captura screenshots R028-003 contra preview local (homolog build + proxy API demo).
 * Uso: node scripts/capture-r028-003.mjs  (com `npm run preview` em :4173)
 */
import { chromium, devices } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.resolve(__dirname, "../../documentacao/evidencias/r028-003-critical-map/screenshots");
const BASE = process.env.PANNE_CAPTURE_BASE || "http://127.0.0.1:5180";

async function login(page, subject = "demo-owner") {
  await page.goto(`${BASE}/entrar`);
  await page.waitForSelector('button:has-text("Entrar na demonstração"), button:has-text("Entrar em desenvolvimento")');
  const select = page.locator("label:has-text('Perfil') select, select").first();
  if (await select.count()) {
    await select.selectOption(subject).catch(() => {});
  }
  await page.getByRole("button", { name: "Entrar na demonstração" }).click().catch(async () => {
    await page.getByRole("button", { name: "Entrar em desenvolvimento" }).click();
  });
  await page.waitForTimeout(2500);
  if (page.url().includes("/organizacao")) {
    const opt = page.getByText(/Panne Demonstração/i).first();
    if (await opt.count()) await opt.click();
    const cont = page.getByRole("button", { name: /Continuar|Entrar|Confirmar|Usar/i });
    if (await cont.count()) await cont.first().click();
    await page.waitForTimeout(2000);
  }
  if (!page.url().includes("/fluxo")) {
    await page.goto(`${BASE}/fluxo`);
  }
  await page.waitForSelector("text=Fluxo produtivo", { timeout: 30000 });
}

async function shot(page, name) {
  await page.screenshot({ path: path.join(OUT, `${name}.png`), fullPage: true });
  console.log("saved", name);
}

async function main() {
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  await login(page);
  await shot(page, "01-visao-geral-desktop");

  // Foco diferente da posição: etapa 8
  await page.goto(`${BASE}/fluxo?etapa=8`);
  await page.waitForSelector("text=Custos e preços");
  await shot(page, "05-foco-diferente-posicao");

  // Jornada produto — tentar códigos comuns da demo
  for (const code of ["PAO-TRAD", "PAO-FR", "REF-COLA", "COCA"]) {
    await page.goto(`${BASE}/fluxo?modo=produto&produto=${code}`);
    await page.waitForTimeout(1500);
    const body = await page.locator(".flow-page").innerText().catch(() => "");
    if (body.includes("não encontrado")) continue;
    if (body.match(/Receitas|receita/i) && body.match(/parado|Você está aqui/i)) {
      await shot(page, "02-produzido-bloqueado-receita");
    }
    if (body.match(/Executar|Preparo/i) && body.match(/Você está aqui/i)) {
      await shot(page, "03-produzido-pronto-execucao");
    }
    if (body.match(/Não se aplica — produto comprado|jornada de produto comprado/i)) {
      await shot(page, "04-comprado-nao-aplicavel");
    }
  }

  // Mobile
  await context.close();
  const mobile = await browser.newContext({ ...devices["iPhone 12"] });
  const mpage = await mobile.newPage();
  await login(mpage);
  await shot(mpage, "06-mobile");
  await mobile.close();

  // Tablet
  const tablet = await browser.newContext({ viewport: { width: 768, height: 1024 } });
  const tpage = await tablet.newPage();
  await login(tpage);
  await shot(tpage, "07-tablet");
  await tablet.close();

  // Sem custos — leitor / perfil limitado
  const readerCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const rpage = await readerCtx.newPage();
  await login(rpage, "demo-reader");
  await rpage.goto(`${BASE}/fluxo`);
  await rpage.waitForTimeout(2000);
  await shot(rpage, "08-perfil-sem-custos");
  await readerCtx.close();

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
