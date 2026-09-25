import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(here, "../../documentacao/evidencias/fiscal-draft-items");
mkdirSync(outDir, { recursive: true });

const FE = process.env.PANNE_FE_URL || "http://127.0.0.1:5198";
const trial = JSON.parse(readFileSync(resolve(outDir, "trial.json"), "utf8"));
const notes = [];

function log(message) {
  notes.push(message);
  console.log(message);
}

async function waitHttp(url, label) {
  const deadline = Date.now() + 40000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok || response.status < 500) return;
    } catch {
      /* retry */
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  throw new Error(`${label} não respondeu em ${url}`);
}

async function shot(page, name, { fullPage = true } = {}) {
  const dest = resolve(outDir, `${name}.png`);
  const url = page.url();
  if (url.includes("/entrar")) {
    throw new Error(`captura recusada: caiu em /entrar (${name}) ${url}`);
  }
  await page.screenshot({ path: dest, fullPage });
  log(`${name} ${url}${fullPage ? "" : " viewport"}`);
}

async function assertNoHorizontalOverflow(page, suffix) {
  if (!suffix.startsWith("390")) return;
  const measure = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }));
  log(`overflow ${suffix} ${JSON.stringify(measure)}`);
  if (measure.scrollWidth !== measure.clientWidth) {
    throw new Error(`overflow-x em 390: ${JSON.stringify(measure)}`);
  }
}

async function assertVisibleAction(page, name) {
  const button = page.getByRole("button", { name, exact: true });
  await button.waitFor({ state: "visible" });
  const box = await button.boundingBox();
  if (!box || box.height < 24 || box.width < 72) {
    throw new Error(`ação invisível ou miúda: ${name} ${JSON.stringify(box)}`);
  }
  const viewport = page.viewportSize();
  if (name === "Adicionar item" && viewport && box.y + box.height > viewport.height) {
    throw new Error(`Adicionar item fora do primeiro viewport: ${JSON.stringify({ ...box, viewport })}`);
  }
  const paint = await button.evaluate((el) => {
    const style = getComputedStyle(el);
    return { background: style.backgroundColor, color: style.color };
  });
  log(`acao ${name} ${JSON.stringify({ ...box, ...paint })}`);
}

async function assertNoGigio(page) {
  const fab = page.locator(".gigio-fab, .product-gigio-fab, [aria-label='Gigio']");
  if (await fab.count()) {
    throw new Error("Gigio visível sobre a nota");
  }
}

async function measureLayout(page, suffix) {
  const geometry = await page.evaluate(() => {
    const pick = (sel) => {
      const node = document.querySelector(sel);
      if (!node) return null;
      const box = node.getBoundingClientRect();
      return { left: Math.round(box.left), width: Math.round(box.width), top: Math.round(box.top) };
    };
    return {
      page: pick(".receipt-page"),
      head: pick(".page-head"),
      items: pick(".draft-items"),
      review: pick(".receipt-sheet"),
      save: (() => {
        const btn = [...document.querySelectorAll("button")].find((el) =>
          el.textContent?.includes("Salvar itens da nota"),
        );
        return btn ? btn.getBoundingClientRect().toJSON() : null;
      })(),
    };
  });
  log(`layout ${suffix} ${JSON.stringify(geometry)}`);
  if (suffix.startsWith("390") && geometry.page) {
    if (geometry.page.left < 12 || geometry.page.left > 20) {
      throw new Error(`padding esquerdo 390 fora de ~16px: ${JSON.stringify(geometry.page)}`);
    }
    if (geometry.page.width < 350 || geometry.page.width > 366) {
      throw new Error(`contêiner 390 deveria ocupar ~358px: ${JSON.stringify(geometry.page)}`);
    }
    for (const key of ["head", "items", "review"]) {
      const row = geometry[key];
      if (!row) continue;
      if (Math.abs(row.left - geometry.page.left) > 1 || Math.abs(row.width - geometry.page.width) > 1) {
        throw new Error(`borda desalinhada ${key}: ${JSON.stringify(geometry)}`);
      }
    }
  }
  return geometry;
}

async function assertDialogActionsReachable(page) {
  const viewport = page.viewportSize();
  for (const name of ["Voltar", "Usar este novo ingrediente"]) {
    const button = page.getByRole("button", { name, exact: true });
    await button.waitFor({ state: "visible" });
    const box = await button.boundingBox();
    if (!box || box.height < 24 || box.width < 48) {
      throw new Error(`ação do diálogo invisível: ${name} ${JSON.stringify(box)}`);
    }
    if (!viewport || box.y < 0 || box.y + box.height > viewport.height + 1) {
      throw new Error(`ação do diálogo fora do viewport: ${name} ${JSON.stringify({ ...box, viewport })}`);
    }
    log(`dialogo-acao ${name} ${JSON.stringify(box)}`);
  }
}

async function login(page) {
  await page.addInitScript(
    ({ orgId }) => {
      try {
        sessionStorage.setItem("panne.demoSubject", "local-dev-owner");
        localStorage.setItem("panne.activeOrganization", orgId);
      } catch {
        /* ignore */
      }
    },
    { orgId: trial.organization_id },
  );
  await page.goto(`${FE}/entrar`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Entrar em desenvolvimento" }).click();
  await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 20000 });
  const picker = page.getByRole("heading", { name: "Escolha a organização" });
  if (await picker.isVisible().catch(() => false)) {
    await page.getByRole("button", { name: /Ensaio itens/ }).click();
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 15000 });
  }
}

async function openDraft(page, suffix) {
  const documentId = trial.documents[suffix.startsWith("390") ? "390" : "1440"].id;
  await page.goto(`${FE}/gestao/compras/entradas/${documentId}`, {
    waitUntil: "domcontentloaded",
  });
  await page.getByRole("heading", { name: "Itens da nota" }).waitFor({ timeout: 20000 });
}

async function runViewport(browser, width, height, suffix) {
  const page = await browser.newPage({ viewport: { width, height } });
  page.on("pageerror", (error) => log(`pageerror ${suffix}: ${error.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") log(`console.error ${suffix}: ${msg.text()}`);
  });
  await login(page);
  await openDraft(page, suffix);
  await page.getByText("Nenhum item informado.").waitFor();
  await assertVisibleAction(page, "Adicionar item");
  await assertNoGigio(page);
  await assertNoHorizontalOverflow(page, suffix);
  await measureLayout(page, `${suffix}-vazio`);
  await shot(page, `01-vazio-${suffix}`);

  await page.getByRole("button", { name: "Adicionar item" }).click();
  await page.getByLabel("Descrição").fill("Farinha tipo 1 saco 25 kg");
  await page.getByLabel("Quantidade").fill("10");
  await page.getByLabel("Unidade").fill("KG");
  await page.getByLabel("Valor unitário").fill("5.40");
  await page.getByLabel("Ingrediente na Panne").click();
  await page.getByLabel("Ingrediente na Panne").fill("Farinha");
  await page.getByRole("option", { name: /Farinha de trigo ensaio/ }).waitFor({ timeout: 15000 });
  await assertNoHorizontalOverflow(page, suffix);
  await shot(page, `02-busca-${suffix}`);

  await page.getByRole("option", { name: /Farinha de trigo ensaio/ }).click();
  await page.getByText("Farinha de trigo ensaio").waitFor();
  await shot(page, `03-existente-${suffix}`);

  await page.getByRole("button", { name: "Trocar" }).click();
  await page.getByRole("button", { name: "Criar novo" }).click();
  const dialog = page.getByRole("dialog", { name: "Criar ingrediente" });
  await dialog.waitFor();
  await page.getByRole("button", { name: "Usar este novo ingrediente" }).click();
  await dialog.getByText("Informe o nome do ingrediente.").waitFor();
  await dialog.getByLabel("Nome do ingrediente").fill("Farinha");
  await dialog.getByLabel("Código").fill(trial.ingredient_code);
  await page.getByText(/Já existe um ingrediente parecido/).waitFor({ timeout: 15000 });
  await page.getByText(/Já existe um ingrediente parecido/).evaluate((node) => {
    node.scrollIntoView({ block: "nearest", inline: "nearest" });
  });
  await assertDialogActionsReachable(page);
  await assertNoHorizontalOverflow(page, suffix);
  await shot(page, `04-dialogo-${suffix}`, { fullPage: !suffix.startsWith("390") });

  await dialog.getByRole("button", { name: "Voltar" }).click();
  await dialog.waitFor({ state: "hidden" });
  await page.getByPlaceholder("Ainda não associado").waitFor();
  log(`voltar-fisico ${suffix} linha preservada`);

  await page.getByRole("button", { name: "Criar novo" }).click();
  await dialog.waitFor();
  await dialog.getByLabel("Nome do ingrediente").fill("Farinha");
  await page.getByText(/Já existe um ingrediente parecido/).waitFor({ timeout: 15000 });
  await page.keyboard.press("Escape");
  await dialog.waitFor({ state: "hidden" });
  await page.getByPlaceholder("Ainda não associado").waitFor();
  const focused = await page.evaluate(() => document.activeElement?.textContent?.trim() || document.activeElement?.id);
  log(`foco-apos-escape ${suffix} ${focused}`);
  if (suffix.startsWith("390")) await shot(page, `05-voltar-${suffix}`);

  await page.getByRole("button", { name: "Criar novo" }).click();
  await dialog.waitFor();
  await dialog.getByLabel("Nome do ingrediente").fill("Trigo especial da casa");
  await dialog.getByLabel("Código").fill(`TRG-${suffix.replace(/\D/g, "").slice(0, 4) || "1"}`);
  await assertDialogActionsReachable(page);
  await dialog.getByRole("button", { name: "Usar este novo ingrediente" }).click();
  await page.getByText("Trigo especial da casa").waitFor();
  await page.getByLabel("Descrição").waitFor();
  const description = await page.getByLabel("Descrição").inputValue();
  if (description !== "Farinha tipo 1 saco 25 kg") {
    throw new Error(`descrição fiscal perdida: ${description}`);
  }
  await assertVisibleAction(page, "Salvar itens da nota");
  await shot(page, `06-novo-pendente-${suffix}`);

  await page.getByRole("button", { name: "Salvar itens da nota" }).click();
  await page.getByText("Aguardando insumo de destino").waitFor({ timeout: 20000 });
  await page.getByLabel("Itens da nota").getByText("Trigo especial da casa").waitFor();
  await assertNoGigio(page);
  await assertNoHorizontalOverflow(page, suffix);
  await measureLayout(page, `${suffix}-salvo`);
  await shot(page, `07-salvo-${suffix}`);
  await page.close();
}

await waitHttp(`${FE}/`, "frontend");
const browser = await chromium.launch({ headless: true });
try {
  await runViewport(browser, 1440, 900, "1440");
  await runViewport(browser, 390, 844, "390");
  writeFileSync(resolve(outDir, "captura-log.txt"), notes.join("\n"), "utf8");
} finally {
  await browser.close();
}
