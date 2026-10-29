import { readFileSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const shots = join(root, "documents", "reviews", "screenshots", "revisao-cadastros-012");
const evidence = join(root, "documents", "reviews", "evidence", "revisao-cadastros-012");
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_LOCAL_UI_URL ?? "http://127.0.0.1:5179";
const log = [];

function tokens() {
  const raw = readFileSync(join(root, ".local", "demo-tokens.env"), "utf8");
  const map = {};
  for (const line of raw.split(/\r?\n/)) {
    const match = line.match(/^([A-Z0-9_]+)=(.*)$/);
    if (match) {
      map[match[1]] = match[2];
    }
  }
  return {
    operator: process.env.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A || map.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A,
    viewer: process.env.ACTIONFINANCE_DEMO_TOKEN_VIEWER_A || map.ACTIONFINANCE_DEMO_TOKEN_VIEWER_A,
  };
}

async function shot(page, width, name) {
  await page.setViewportSize({ width, height: width <= 400 ? 900 : 960 });
  const file = join(shots, `${width}-${name}.png`);
  await page.screenshot({ path: file, fullPage: true });
  log.push({ width, name, file });
}

const creds = tokens();
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
page.on("dialog", (dialog) => dialog.accept());
await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
await page.getByLabel("Token local").fill(creds.operator);
await page.getByRole("button", { name: "Entrar na demonstração" }).click();
await page.getByRole("button", { name: "Cadastros" }).waitFor({ timeout: 30000 });
await page.waitForTimeout(2500);
await page.getByRole("button", { name: "Cadastros" }).click();
await page.waitForTimeout(2000);
const listText = await page.locator("body").innerText();
if (!listText.includes("Busca consulta a lista") && !listText.includes("Importar arquivo")) {
  await shot(page, 1280, "lista-inesperada");
  throw new Error("Lista nova nao apareceu apos Cadastros.");
}
for (const width of [360, 768, 1280]) {
  await shot(page, width, "lista");
}

await page.getByRole("button", { name: "Cadastrar", exact: true }).click();
await page.waitForTimeout(800);
for (const width of [360, 768, 1280]) {
  await shot(page, width, "cadastrar-sem-busca");
}
await page.getByLabel("Razão social ou nome").fill("Fornecedor incompleto 012");
await page.getByRole("checkbox", { name: "Cliente" }).uncheck();
await page.getByRole("checkbox", { name: "Fornecedor" }).check();
await page.locator("form.party-form button[type='submit']").click();
await page.waitForTimeout(1500);
for (const width of [360, 768, 1280]) {
  await shot(page, width, "cadastro-incompleto");
}

await page.getByRole("button", { name: "Cadastros" }).click();
await page.waitForTimeout(800);
await page.getByRole("button", { name: "Cadastrar", exact: true }).click();
await page.getByLabel("Razão social ou nome").fill("Fornecedor completo 012");
await page.getByRole("checkbox", { name: "Cliente" }).uncheck();
await page.getByRole("checkbox", { name: "Fornecedor" }).check();
await page.getByLabel("Tipo de pessoa").selectOption("LEGAL");
await page.getByLabel("Tipo do documento").selectOption("CNPJ");
await page.getByLabel("Número do documento").fill("12.ABC.345/01DE-35");
await page.getByRole("button", { name: "Adicionar unidade" }).click();
await page.getByLabel("Nome da unidade").fill("Depósito 012");
await page.getByRole("button", { name: "Adicionar endereço" }).click();
await page.getByLabel("CEP ou código postal").fill("01001-000");
await page.getByLabel("Logradouro").fill("Praça da Sé");
await page.getByRole("textbox", { name: "Número", exact: true }).fill("100");
await page.getByLabel("Município").fill("São Paulo");
await page.getByLabel("UF ou região").fill("SP");
await page.locator("form.party-form button[type='submit']").click();
await page.waitForTimeout(1500);
for (const width of [360, 768, 1280]) {
  await shot(page, width, "cadastro-completo");
  await shot(page, width, "detalhe");
}

await page.getByRole("button", { name: "Cadastros" }).click();
await page.waitForTimeout(800);
await page.getByRole("button", { name: "Cadastrar", exact: true }).click();
await page.getByLabel("Razão social ou nome").fill("Tentativa duplicada 012");
await page.getByRole("checkbox", { name: "Cliente" }).uncheck();
await page.getByRole("checkbox", { name: "Fornecedor" }).check();
await page.getByLabel("Tipo do documento").selectOption("CNPJ");
await page.getByLabel("Número do documento").fill("12.ABC.345/01DE-35");
await page.locator("form.party-form button[type='submit']").click();
await page.waitForTimeout(1500);
for (const width of [360, 768, 1280]) {
  await shot(page, width, "duplicidade");
}

await page.getByRole("button", { name: "Cadastros" }).click();
await page.waitForTimeout(2000);
await page.getByRole("button", { name: "Importar arquivo" }).click();
await page.waitForTimeout(500);
await page.locator('input[type="file"]').setInputFiles({
  name: "invalido-012.csv",
  mimeType: "text/csv",
  buffer: Buffer.from(
    "nome;relacao;tipo_pessoa;pais_documento;tipo_documento;documento\nLinha invalida;FORNECEDOR;JURIDICA;BR;CNPJ;12.ABC.345/0001-95\n",
    "utf8",
  ),
});
await page.getByRole("button", { name: "Validar arquivo" }).click();
await page.waitForTimeout(1500);
for (const width of [360, 768, 1280]) {
  await shot(page, width, "importacao-erro");
}

const viewer = await browser.newPage();
await viewer.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
await viewer.getByLabel("Token local").fill(creds.viewer);
await viewer.getByRole("button", { name: "Entrar na demonstração" }).click();
await viewer.getByRole("button", { name: "Cadastros" }).waitFor({ timeout: 30000 });
await viewer.waitForTimeout(2500);
await viewer.getByRole("button", { name: "Cadastros" }).click();
await viewer.waitForTimeout(1500);
for (const width of [360, 768, 1280]) {
  await shot(viewer, width, "lista-consulta");
}

await browser.close();
await writeFile(join(evidence, "capturas.json"), JSON.stringify({ capturedAt: new Date().toISOString(), baseUrl, personalData: "synthetic-only", files: log }, null, 2));
console.log(`captured=${log.length}`);
