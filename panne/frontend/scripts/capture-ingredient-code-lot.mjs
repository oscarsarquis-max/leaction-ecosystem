import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const outDir = resolve(here, "../../documentacao/evidencias/ingredient-code-lot");
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
    await new Promise((resolveWait) => setTimeout(resolveWait, 400));
  }
  throw new Error(`${label} não respondeu em ${url}`);
}

async function shot(page, name) {
  const dest = resolve(outDir, `${name}.png`);
  const url = page.url();
  if (url.includes("/entrar")) {
    throw new Error(`captura recusada: caiu em /entrar (${name}) ${url}`);
  }
  await page.screenshot({ path: dest, fullPage: true });
  log(`${name} ${url} fullPage`);
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
    await page.getByRole("button", { name: /Ensaio código/ }).click();
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 15000 });
  }
}

async function openNote(page, group, suffix) {
  const documentId = trial.documents[group][suffix].id;
  await page.goto(`${FE}/gestao/compras/entradas/${documentId}`, { waitUntil: "domcontentloaded" });
  await page.locator(".receipt-page").waitFor({ timeout: 20000 });
}

async function inspectPage(page, suffix, extra = {}) {
  const geometry = await page.evaluate(() => {
    const box = (node) => {
      if (!node) return null;
      const rect = node.getBoundingClientRect();
      return {
        top: Math.round(rect.top),
        left: Math.round(rect.left),
        width: Math.round(rect.width),
        height: Math.round(rect.height),
        bottom: Math.round(rect.bottom),
        right: Math.round(rect.right),
      };
    };
    const style = (node) => {
      if (!node) return null;
      const computed = getComputedStyle(node);
      return {
        fontSize: computed.fontSize,
        lineHeight: computed.lineHeight,
        overflow: computed.overflow,
      };
    };
    const summaries = [...document.querySelectorAll(".receipt-summary")];
    const actions = [...document.querySelectorAll(".receipt-primary")];
    const pairs = [
      ["page", document.querySelector(".receipt-page")],
      ["head", document.querySelector(".page-head")],
      ["sheet", document.querySelector(".receipt-sheet")],
      ["lots", document.querySelector(".receipt-lots")],
      ["destination", document.getElementById("local-estoque")],
      ["summary", summaries.at(-1) || null],
      ["action", actions.at(-1) || document.querySelector(".receipt-primary")],
      ["dialog", document.querySelector('[role="dialog"]')],
      ["code", document.getElementById("novo-ingrediente-codigo")],
    ];
    const nodes = Object.fromEntries(pairs.map(([key, node]) => [key, { box: box(node), style: style(node) }]));
    const focused = document.activeElement;
    nodes.focus = {
      tag: focused?.tagName || null,
      id: focused?.id || null,
      label: focused?.getAttribute("aria-label") || focused?.labels?.[0]?.textContent || null,
      box: box(focused),
    };
    nodes.viewport = { width: window.innerWidth, height: window.innerHeight, scrollWidth: document.documentElement.scrollWidth };
    const dialog = document.querySelector('[role="dialog"]');
    if (dialog) {
      const insides = [...dialog.querySelectorAll("h3, label, input, button, p")].map((node) => ({
        text: (node.textContent || "").trim().slice(0, 60),
        box: box(node),
      }));
      nodes.dialogChildren = insides;
    }
    return nodes;
  });
  log(`layout ${suffix} ${JSON.stringify({ ...geometry, extra })}`);
  if (suffix.includes("390")) {
    if (geometry.viewport.scrollWidth > geometry.viewport.width + 1) {
      throw new Error(`overflow-x 390: ${JSON.stringify(geometry.viewport)}`);
    }
    if (geometry.page.box && (geometry.page.box.left < 8 || geometry.page.box.width < 340)) {
      throw new Error(`contêiner 390 ilegível: ${JSON.stringify(geometry.page.box)}`);
    }
    const readable = [geometry.head, geometry.sheet, geometry.lots, geometry.summary, geometry.dialog]
      .map((row) => row?.style?.fontSize)
      .filter(Boolean);
    for (const fontSize of readable) {
      if (Number.parseFloat(fontSize) < 12) {
        throw new Error(`fonte abaixo de 12px em 390: ${fontSize}`);
      }
    }
    const stacked = [geometry.lots?.box, geometry.destination?.box, geometry.summary?.box, geometry.action?.box]
      .filter(Boolean)
      .sort((left, right) => left.top - right.top);
    for (let index = 0; index < stacked.length - 1; index += 1) {
      const current = stacked[index];
      const next = stacked[index + 1];
      if (current.bottom - 2 > next.top && current.right > next.left && current.left < next.right) {
        throw new Error(`sobreposição 390: ${JSON.stringify({ current, next })}`);
      }
    }
    if (geometry.dialog?.box) {
      const panel = geometry.dialog.box;
      if (panel.left < -1 || panel.right > geometry.viewport.width + 2) {
        throw new Error(`diálogo 390 sai da largura: ${JSON.stringify(panel)}`);
      }
    }
    if (geometry.focus?.box && (geometry.focus.box.left < 0 || geometry.focus.box.right > geometry.viewport.width + 2)) {
      throw new Error(`foco fora da largura 390: ${JSON.stringify(geometry.focus)}`);
    }
  }
  return geometry;
}

async function fillLine(page) {
  const item = page.locator(".draft-item").first();
  await item.getByLabel("Descrição na nota").fill("Açúcar da nota");
  await item.getByLabel("Quantos foram comprados?").fill("2");
  await item.getByLabel("Unidade de compra").selectOption("kg");
}

async function openCreateDialog(page) {
  await page.getByRole("button", { name: "Cadastrar novo ingrediente" }).click();
  const dialog = page.getByRole("dialog", { name: "Criar ingrediente" });
  await dialog.waitFor();
  await dialog.getByLabel("Código interno sugerido").waitFor({ state: "visible" });
  await page.waitForFunction(() => {
    const input = document.getElementById("novo-ingrediente-codigo");
    return Boolean(input && input.value.trim());
  }, null, { timeout: 15000 });
  return dialog;
}

async function captureDialog(page, suffix) {
  await openNote(page, "dialog", suffix);
  await page.getByRole("heading", { name: "Itens da nota" }).waitFor({ timeout: 20000 });
  await page.getByRole("button", { name: "Adicionar item" }).click();
  await fillLine(page);
  const dialog = await openCreateDialog(page);
  await dialog.getByLabel("Nome do ingrediente").fill("Açúcar cristal");
  await dialog.getByRole("button", { name: "Editar código" }).click();
  const code = dialog.getByLabel("Código interno sugerido");
  await code.waitFor({ state: "visible" });
  const suggested = await code.inputValue();
  if (!suggested.trim()) throw new Error("código sugerido vazio");
  await code.fill("ACU-1");
  await code.focus();
  const unit = dialog.getByLabel("Unidade de base");
  await unit.waitFor({ state: "visible" });
  await unit.selectOption({ index: 1 });
  await inspectPage(page, `${suffix}-dialog`, { suggested, edited: "ACU-1" });
  await shot(page, `01-dialogo-sugerido-edicao-${suffix}`);
}

async function captureOccupied(page, suffix) {
  await openNote(page, "error", suffix);
  await page.getByRole("heading", { name: "Itens da nota" }).waitFor({ timeout: 20000 });
  await page.getByRole("button", { name: "Adicionar item" }).click();
  await fillLine(page);
  const dialog = await openCreateDialog(page);
  await dialog.getByLabel("Nome do ingrediente").fill("Açúcar cristal");
  await dialog.getByRole("button", { name: "Editar código" }).click();
  await dialog.getByLabel("Código interno sugerido").fill(trial.occupied_code);
  const unit = dialog.getByLabel("Unidade de base");
  await unit.selectOption({ index: 1 });
  await dialog.getByRole("button", { name: "Usar este novo ingrediente" }).click();
  await page.getByRole("button", { name: "Salvar itens da nota" }).click();
  const again = page.getByRole("dialog", { name: "Criar ingrediente" });
  await again.waitFor({ timeout: 20000 });
  await again.getByText(/código interno já/).waitFor();
  const keptName = await again.getByLabel("Nome do ingrediente").inputValue();
  const keptCode = await again.getByLabel("Código interno sugerido").inputValue();
  const keptDesc = await page.getByLabel("Descrição na nota").inputValue();
  if (keptName !== "Açúcar cristal") throw new Error(`nome perdido: ${keptName}`);
  if (keptCode !== trial.occupied_code) throw new Error(`código perdido: ${keptCode}`);
  if (keptDesc !== "Açúcar da nota") throw new Error(`descrição perdida: ${keptDesc}`);
  await again.getByLabel("Código interno sugerido").focus();
  await inspectPage(page, `${suffix}-ocupado`, { keptName, keptCode, keptDesc });
  await shot(page, `05-erro-codigo-preservado-${suffix}`);
}

async function fillLots(page, lots) {
  const block = page.locator(".receipt-lots").first();
  await block.getByRole("heading", { name: "Lote e validade" }).waitFor();
  while ((await block.getByLabel(/Quantidade do lote/).count()) < lots.length) {
    await page.getByRole("button", { name: "Dividir em outro lote" }).click();
  }
  for (const [index, lot] of lots.entries()) {
    const qty = block.getByLabel(`Quantidade do lote ${index + 1}`);
    await qty.fill(lot.quantity);
    await block.getByLabel(`Identificação do lote ${index + 1}`).fill(lot.lot);
    await block.getByLabel(`Validade do lote ${index + 1}`).fill(lot.expires);
  }
  if (lots.length > 1) {
    await page.getByText(/A soma dos lotes precisa ser a quantidade conferida/).waitFor({ state: "hidden" }).catch(() => {});
  }
}

async function assertAlignedReceipt(page, suffix) {
  const confirm = page.getByRole("button", { name: "Confirmar entrada no estoque" });
  await confirm.waitFor({ state: "visible" });
  const box = await confirm.boundingBox();
  if (!box || box.height < 24 || box.width < 80) {
    throw new Error(`ação final invisível: ${JSON.stringify(box)}`);
  }
  await page.getByText("Ao confirmar").waitFor();
  await page.getByText(/Almoxarifado ensaio|Local/).first().waitFor();
  const geometry = await inspectPage(page, suffix);
  if (!geometry.sheet?.box || !geometry.lots?.box || !geometry.summary?.box || !geometry.destination?.box || !geometry.action?.box) {
    throw new Error(`contêiner incompleto: ${JSON.stringify({ lots: geometry.lots?.box, summary: geometry.summary?.box, destination: geometry.destination?.box, action: geometry.action?.box })}`);
  }
  const lefts = [geometry.lots.box.left, geometry.destination.box.left, geometry.summary.box.left, geometry.action.box.left];
  if (Math.max(...lefts) - Math.min(...lefts) > 24) {
    throw new Error(`lotes/resumo/ação desalinhados: ${JSON.stringify(lefts)}`);
  }
  return geometry;
}

async function captureReceipt(page, group, suffix, lots, name) {
  await openNote(page, group, suffix);
  await page.getByRole("heading", { name: "Revisão da nota" }).waitFor({ timeout: 20000 });
  const arrived = page.getByLabel(/Quanto chegou|Quantidade conferida|chegou/).first();
  if (await arrived.count()) {
    const current = await arrived.inputValue().catch(() => "");
    if (!current.trim()) await arrived.fill(lots.reduce((sum, lot) => sum + Number(lot.quantity), 0).toString());
  }
  const content = page.getByLabel("Conteúdo de cada embalagem");
  if (await content.count()) {
    await content.first().fill("1000");
  }
  await fillLots(page, lots);
  await page.getByLabel(`Validade do lote ${lots.length}`).focus();
  await assertAlignedReceipt(page, `${suffix}-${group}`);
  await shot(page, name);
}

async function runViewport(browser, width, height, suffix) {
  const page = await browser.newPage({ viewport: { width, height } });
  page.on("pageerror", (error) => log(`pageerror ${suffix}: ${error.message}`));
  page.on("console", (msg) => {
    if (msg.type() === "error") log(`console.error ${suffix}: ${msg.text()}`);
  });
  await login(page);
  await captureDialog(page, suffix);
  await captureReceipt(
    page,
    "manual_one",
    suffix,
    [{ quantity: "10", lot: "L-MANUAL-1", expires: "2027-12-31" }],
    `02-manual-um-lote-${suffix}`,
  );
  await captureReceipt(
    page,
    "manual_split",
    suffix,
    [
      { quantity: "6", lot: "L-A", expires: "2027-01-10" },
      { quantity: "4", lot: "L-B", expires: "2028-06-20" },
    ],
    `03-manual-dois-lotes-${suffix}`,
  );
  await captureReceipt(
    page,
    "xml_one",
    suffix,
    [{ quantity: "25", lot: "L-XML-1", expires: "2027-11-15" }],
    `04a-xml-um-lote-${suffix}`,
  );
  await captureReceipt(
    page,
    "xml_split",
    suffix,
    [
      { quantity: "15", lot: "L-XML-A", expires: "2027-03-01" },
      { quantity: "10", lot: "L-XML-B", expires: "2028-09-30" },
    ],
    `04b-xml-dois-lotes-${suffix}`,
  );
  await captureOccupied(page, suffix);
  await page.close();
}

await waitHttp(`${FE}/`, "frontend");
await waitHttp("http://127.0.0.1:5086/ready", "api");
const browser = await chromium.launch({ headless: true });
try {
  await runViewport(browser, 1440, 900, "1440");
  await runViewport(browser, 390, 844, "390");
  writeFileSync(resolve(outDir, "captura-log.txt"), notes.join("\n"), "utf8");
} finally {
  await browser.close();
}
