import { mkdirSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(here, "../../documentacao/evidencias/fiscal-entry-real");
mkdirSync(outDir, { recursive: true });

const base = process.env.PANNE_CAPTURE_URL || "http://127.0.0.1:5197";
const orgId = process.env.PANNE_TRIAL_ORG_ID || "";
const orgName = process.env.PANNE_TRIAL_ORG_NAME || "Ensaio fiscal";
const stamp = String(Date.now()).slice(-6);
const notes = [];

function log(message) {
  notes.push(message);
  console.log(message);
}

async function shot(page, name) {
  const dest = resolve(outDir, `${name}.png`);
  const url = page.url();
  if (url.includes("/entrar")) {
    throw new Error(`captura recusada: caiu em /entrar (${name}) ${url}`);
  }
  await page.screenshot({ path: dest, fullPage: true });
  log(`${name} ${url} ${dest}`);
}

async function assertVisibleAction(page, name) {
  const button = page.getByRole("button", { name });
  await button.waitFor({ state: "visible" });
  const box = await button.boundingBox();
  if (!box || box.height < 24 || box.width < 96) {
    throw new Error(`ação invisível ou miúda: ${name} ${JSON.stringify(box)}`);
  }
  const paint = await button.evaluate((el) => {
    const style = getComputedStyle(el);
    return { background: style.backgroundColor, color: style.color, opacity: style.opacity };
  });
  if (paint.background === "rgba(0, 0, 0, 0)" || paint.background === "transparent") {
    throw new Error(`ação sem fundo: ${name} ${JSON.stringify(paint)}`);
  }
  if (paint.background === paint.color) {
    throw new Error(`ação sem contraste: ${name} ${JSON.stringify(paint)}`);
  }
  log(`acao ${name} ${JSON.stringify({ ...box, ...paint })}`);
}

async function assertNoHorizontalOverflow(page) {
  const measure = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  log(`overflow ${JSON.stringify(measure)}`);
  if (measure.scrollWidth !== measure.clientWidth) {
    throw new Error(`overflow-x em 390: ${JSON.stringify(measure)}`);
  }
}

async function chooseOrg(page) {
  if (orgId) {
    await page.evaluate((id) => localStorage.setItem("panne.activeOrganization", id), orgId);
  }
  const picker = page.getByRole("heading", { name: "Escolha a organização" });
  if (await picker.isVisible().catch(() => false)) {
    const named = page.getByRole("button", { name: new RegExp(orgName, "i") });
    if (await named.count()) {
      await named.first().click();
    } else if (orgId) {
      await page.locator("select.org-select").selectOption(orgId).catch(() => {});
    }
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 15000 });
  }
}

async function login(page) {
  await page.goto(`${base}/entrar`, { waitUntil: "domcontentloaded" });
  const enter = page.getByRole("button", { name: "Entrar em desenvolvimento" });
  await enter.waitFor({ timeout: 20000 });
  await enter.click();
  await page.waitForURL((url) => !url.pathname.endsWith("/entrar"), { timeout: 20000 });
  await chooseOrg(page);
}

async function openEntry(page) {
  await page.goto(`${base}/gestao/compras/entradas/nova`, { waitUntil: "domcontentloaded" });
  await chooseOrg(page);
  try {
    await page.getByRole("heading", { name: "Registrar entrada" }).waitFor({ timeout: 20000 });
  } catch (error) {
    await page.screenshot({ path: resolve(outDir, "debug-falha.png"), fullPage: true });
    log(`url=${page.url()}`);
    log(`h1=${JSON.stringify(await page.locator("h1,h2,[role=status],[role=alert]").allTextContents())}`);
    throw error;
  }
}

async function fillValidNote(page, { withKey }) {
  if (withKey) {
    await page.getByLabel("Chave de acesso").fill(`35260812345678000190550010005066121${stamp.padStart(9, "0")}`);
  }
  await page.getByLabel("Número da nota").fill(withKey ? `50${stamp.slice(-3)}` : `41${stamp.slice(-3)}`);
  await page.getByLabel("Série").fill("1");
  await page.getByLabel("Data de emissão").fill("2026-09-18");
  await page.getByLabel("Fornecedor", { exact: true }).fill("Moinho Real do Ensaio");
  await page.getByLabel("CNPJ do fornecedor").fill("12345678000190");
  await page.getByLabel("Descrição").fill("Farinha tipo 1");
  await page.getByLabel("Quantidade").fill("25");
  await page.getByLabel("Unidade").fill("KG");
  await page.getByLabel("Valor unitário").fill("4.10");
}

async function runViewport(browser, width, height, suffix) {
  const page = await browser.newPage({ viewport: { width, height } });
  if (orgId) {
    await page.addInitScript((id) => {
      try {
        localStorage.setItem("panne.activeOrganization", id);
      } catch {
        /* ignore */
      }
    }, orgId);
  }
  page.on("pageerror", (error) => log(`pageerror ${suffix}: ${error.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") log(`console.error ${suffix}: ${msg.text()}`);
  });
  page.on("response", (response) => {
    if (response.status() >= 400) {
      log(`http ${suffix} ${response.status()} ${response.request().method()} ${response.url()}`);
    }
  });
  await login(page);
  await openEntry(page);
  await assertVisibleAction(page, "Revisar e gravar");
  if (suffix.startsWith("390")) await assertNoHorizontalOverflow(page);
  await shot(page, `inicial-${suffix}`);

  await fillValidNote(page, { withKey: suffix.startsWith("1440") });
  await page.getByRole("button", { name: "Revisar e gravar" }).click();
  await page.getByRole("heading", { name: "Revisão" }).waitFor();
  await assertVisibleAction(page, "Gravar nota");
  if (suffix.startsWith("390")) await assertNoHorizontalOverflow(page);
  await shot(page, `revisao-${suffix}`);

  await page.getByRole("button", { name: "Gravar nota" }).click();
  await page.getByText(/Nota gravada · estoque pendente/).waitFor({ timeout: 20000 });
  if (suffix.startsWith("390")) await assertNoHorizontalOverflow(page);
  await shot(page, `gravada-${suffix}`);
  await page.close();
}

const browser = await chromium.launch({ headless: true });
try {
  await runViewport(browser, 1440, 900, "1440");
  await runViewport(browser, 390, 844, "390");
  writeFileSync(resolve(outDir, "captura-log.txt"), notes.join("\n"), "utf8");
} finally {
  await browser.close();
}
