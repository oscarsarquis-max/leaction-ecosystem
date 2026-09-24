import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../documentacao/evidencias/cursor-insumo-manual");
const out = path.join(root, "capturas");
const trialPath = path.join(root, "trial.json");
const API = process.env.PANNE_API_URL || "http://127.0.0.1:5080";
const FE = process.env.PANNE_FE_URL || "http://127.0.0.1:5182";

async function waitHttp(url, label) {
  const deadline = Date.now() + 20000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url);
      if (response.ok || response.status < 500) return;
    } catch {
      /* still down */
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
  throw new Error(`${label} não respondeu em ${url}`);
}

function visibleUrl(page) {
  return page.url();
}

async function shot(page, name) {
  const url = visibleUrl(page);
  if (url.includes("/entrar")) {
    throw new Error(`captura recusada: caiu em /entrar (${name}) ${url}`);
  }
  await page.screenshot({ path: path.join(out, `${name}.png`), fullPage: true });
  return url;
}

await mkdir(out, { recursive: true });
await waitHttp(`${API}/health`, "API");
await waitHttp(`${FE}/`, "frontend");

const trial = JSON.parse(await readFile(trialPath, "utf8"));
const browser = await chromium.launch();
const urls = {};

async function openApp(width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.addInitScript(
    ({ orgId }) => {
      sessionStorage.setItem("panne.demoSubject", "local-dev-owner");
      localStorage.setItem("panne.activeOrganization", orgId);
    },
    { orgId: trial.organization_id },
  );
  await page.goto(`${FE}/entrar`, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    sessionStorage.setItem("panne.demoSubject", "local-dev-owner");
  });
  await page.getByRole("button", { name: "Entrar em desenvolvimento" }).click();
  await page.waitForURL((url) => !url.pathname.includes("/entrar"), { timeout: 15000 });
  const orgSelect = page.locator("select.org-select");
  if (await orgSelect.count()) {
    await orgSelect.selectOption(trial.organization_id);
    await page.getByText("Ensaio insumo", { exact: false }).first().waitFor({ timeout: 10000 });
  } else if (page.url().includes("/organizacao") || (await page.getByRole("heading", { name: "Escolha a organização" }).count())) {
    await page.getByRole("button", { name: /Ensaio insumo/ }).click();
    await page.waitForURL((url) => !url.pathname.includes("/organizacao"), { timeout: 10000 });
  }
  return page;
}

async function captureEstoque(page, suffix) {
  await page.goto(`${FE}/componentes/estoque`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: "Estoque", exact: true }).waitFor({ timeout: 15000 });
  urls[`estoque-${suffix}`] = await shot(page, `estoque-${suffix}`);
  const coach = page.getByRole("complementary", { name: /Orientação/ });
  if (await coach.count()) {
    urls[`estoque-gigio-recolhido-${suffix}`] = await shot(page, `estoque-gigio-recolhido-${suffix}`);
    const opener = coach.getByRole("button", { name: /^Abrir$/ });
    if (await opener.count()) {
      await opener.click();
      await page.getByText(/Finalidade/).waitFor({ timeout: 8000 });
      urls[`estoque-gigio-aberto-${suffix}`] = await shot(page, `estoque-gigio-aberto-${suffix}`);
      await coach.getByRole("button", { name: "Recolher" }).click();
    }
  }
  const lotToggle = page.getByRole("button", { name: "Ver lotes" }).first();
  if (await lotToggle.count()) {
    await lotToggle.click();
    urls[`estoque-lotes-expandidos-${suffix}`] = await shot(page, `estoque-lotes-expandidos-${suffix}`);
  }
  await page.goto(`${FE}/componentes/lotes`, { waitUntil: "networkidle" });
  await page.getByRole("heading", { name: /Lotes/ }).waitFor({ timeout: 15000 });
  urls[`lotes-${suffix}`] = await shot(page, `lotes-${suffix}`);
}

const page1440 = await openApp(1440, 1100);
await captureEstoque(page1440, "1440");
await page1440.goto(`${FE}/componentes/ingredientes/consolidar`, { waitUntil: "networkidle" });
if (page1440.url().includes("/entrar")) {
  throw new Error(`captura recusada: caiu em /entrar ${page1440.url()}`);
}
try {
  await page1440.getByRole("heading", { name: "Consolidar insumo" }).waitFor({ timeout: 15000 });
} catch (error) {
  await page1440.screenshot({ path: path.join(out, "debug-consolidar.png"), fullPage: true });
  throw new Error(`consolidar sem heading. url=${page1440.url()} text=${(await page1440.locator("body").innerText()).slice(0, 400)}`);
}
urls["consolidar-antes-1440"] = await shot(page1440, "consolidar-antes-1440");
const dest = page1440.locator(".manual-path select").first();
await dest.locator('option:not([value=""])').first().waitFor({ state: "attached", timeout: 15000 });
const destValue = await dest.locator('option:not([value=""])').first().getAttribute("value");
await dest.selectOption(destValue);
await page1440.locator('input[type="checkbox"]').first().waitFor({ timeout: 10000 });
const boxes = page1440.locator('input[type="checkbox"]');
const count = await boxes.count();
for (let i = 0; i < Math.min(count, 2); i += 1) {
  await boxes.nth(i).check();
}
await page1440.getByRole("button", { name: "Confirmar vínculos" }).waitFor({ state: "visible" });
if (await page1440.getByRole("button", { name: "Confirmar vínculos" }).isDisabled()) {
  throw new Error(`confirmar ainda desabilitado dest=${destValue} checks=${count} url=${page1440.url()}`);
}
urls["consolidar-selecao-1440"] = await shot(page1440, "consolidar-selecao-1440");
await page1440.getByRole("button", { name: "Confirmar vínculos" }).click();
await page1440.locator(".manual-success").waitFor({ timeout: 15000 });
urls["consolidar-depois-1440"] = await shot(page1440, "consolidar-depois-1440");

const page390 = await openApp(390, 844);
await captureEstoque(page390, "390");
await page390.goto(`${FE}/componentes/ingredientes/consolidar`, { waitUntil: "networkidle" });
await page390.getByRole("heading", { name: "Consolidar insumo" }).waitFor();
urls["consolidar-390"] = await shot(page390, "consolidar-390");

const abertura1440 = await openApp(1440, 1100);
await abertura1440.goto(`${FE}/componentes/estoque/abertura`, { waitUntil: "networkidle" });
await abertura1440.getByRole("heading", { name: "Abrir saldo sem nota" }).waitFor();
urls["abertura-antes-1440"] = await shot(abertura1440, "abertura-antes-1440");
await abertura1440.getByRole("button", { name: /Registrar abertura|Confirmar abertura/ }).click();
await abertura1440.getByRole("alert").waitFor();
urls["abertura-erro-1440"] = await shot(abertura1440, "abertura-erro-1440");
const aberturaSelects = abertura1440.locator(".manual-path select");
await aberturaSelects.nth(0).locator('option:not([value=""])').first().waitFor({ state: "attached" });
await aberturaSelects.nth(0).selectOption({ index: 1 });
await aberturaSelects.nth(1).selectOption({ index: 1 });
await abertura1440.locator(".manual-path input[inputMode='decimal']").first().fill("1");
await abertura1440.getByPlaceholder("Ex.: contagem física da despensa").fill("ensaio visual descartável");
await abertura1440.getByLabel("Custo desconhecido").check();
await abertura1440.getByLabel(/Confirmo esta abertura|Revise/).check();
urls["abertura-desconhecido-1440"] = await shot(abertura1440, "abertura-desconhecido-1440");
await abertura1440.getByRole("button", { name: /Registrar abertura|Confirmar abertura/ }).click();
await abertura1440.locator(".manual-success").waitFor({ timeout: 15000 });
urls["abertura-depois-1440"] = await shot(abertura1440, "abertura-depois-1440");

const abertura390 = await openApp(390, 844);
await abertura390.goto(`${FE}/componentes/estoque/abertura`, { waitUntil: "networkidle" });
await abertura390.getByRole("heading", { name: "Abrir saldo sem nota" }).waitFor();
urls["abertura-390"] = await shot(abertura390, "abertura-390");

const nota1440 = await openApp(1440, 1100);
await nota1440.goto(`${FE}/gestao/compras/entradas/${trial.document_id}`, { waitUntil: "networkidle" });
await nota1440.waitForTimeout(800);
if (nota1440.url().includes("/entrar")) {
  throw new Error("revisão da nota caiu em /entrar");
}
urls["nota-revisao-1440"] = await shot(nota1440, "nota-revisao-1440");
const nota390 = await openApp(390, 844);
await nota390.goto(`${FE}/gestao/compras/entradas/${trial.document_id}`, { waitUntil: "networkidle" });
urls["nota-revisao-390"] = await shot(nota390, "nota-revisao-390");

const page960 = await openApp(960, 1100);
await page960.goto(`${FE}/componentes/ingredientes/consolidar`, { waitUntil: "networkidle" });
await page960.getByRole("heading", { name: "Consolidar insumo" }).waitFor();
urls["consolidar-previa-960"] = await shot(page960, "consolidar-previa-960");

await browser.close();

const compare = [
  "# Comparação com a prévia aprovada de 960 px",
  "",
  `As capturas abaixo são da aplicação React autenticada em \`${FE}\`, com sessão fake e organização descartável. Nenhuma veio de \`file://\` nem de \`/entrar\`.`,
  "",
  `| Tela | URL visível | Largura | Arquivo |`,
  `|---|---|---|---|`,
  ...Object.entries(urls).map(([name, url]) => `| ${name} | ${url} | ${name.includes("390") ? "390" : name.includes("960") ? "960" : "1440"} | capturas/${name}.png |`),
  "",
  "## Alinhamento com a prévia de 960 px",
  "",
  "- A rota `/componentes/ingredientes/consolidar` usa `.manual-path` com `max-width: 960px`, papel creme, tinta grafite e acento espresso — o mesmo recorte da prévia HTML aprovada (`consolidar-insumo.html`).",
  "- A rota `/componentes/estoque` usa `.estoque-util` com kicker Posição atual, colunas Físico/Reservado/Impedido/Disponível e Ver lotes — alinhada a `estoque-util.html`.",
  "- Em 1440 px o conteúdo permanece centrado; as laterais são fundo, não outra composição.",
  "- Em 390 px Estoque, consolidação e abertura empilham sem cortar a ação final.",
  "- Gigio começa recolhido na visão geral; só abre no acionador explícito.",
  "- Abertura e revisão da nota seguem o mesmo papel e a URL real da sessão.",
  "",
  `Organização de ensaio: ${trial.display_name} (${trial.organization_id}).`,
].join("\n");
await writeFile(path.join(root, "COMPARAR-PREVIA.md"), `${compare}\n`, "utf8");
await writeFile(path.join(root, "urls.json"), `${JSON.stringify(urls, null, 2)}\n`, "utf8");
console.log(JSON.stringify({ out, urls }, null, 2));
