import { readFileSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const shots = join(root, "documents", "reviews", "screenshots", "provas-cadastros-013");
const evidence = join(root, "documents", "reviews", "evidence", "provas-cadastros-013");
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_LOCAL_UI_URL ?? "http://127.0.0.1:5179";
if (baseUrl.includes(":4179") && process.env.ACTIONFINANCE_ALLOW_PREVIEW !== "1") {
  throw new Error("Candidata 013 usa Vite em :5179. A preview :4179 nao prova o bundle revisado.");
}

const journal = [];
const WIDTHS = [360, 768, 1280];

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

function fail(message) {
  throw new Error(message);
}

async function apiGet(request, token, path) {
  const response = await request.get(`${baseUrl}${path}`, {
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
  });
  if (!response.ok()) {
    fail(`GET ${path} status=${response.status()}`);
  }
  return response.json();
}

async function shotSet(page, width, name, meta) {
  await page.setViewportSize({ width, height: width <= 400 ? 820 : 960 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(250);
  const url = page.url();
  if (meta.expectedUrlPart && !url.includes(meta.expectedUrlPart)) {
    fail(`${name} @${width}: URL ${url} nao contem ${meta.expectedUrlPart}`);
  }
  const body = await page.locator("body").innerText();
  if (meta.expectedText && !body.includes(meta.expectedText)) {
    fail(`${name} @${width}: texto ausente (${meta.expectedText})`);
  }
  if (meta.forbiddenText && body.includes(meta.forbiddenText)) {
    fail(`${name} @${width}: frase interna ainda visivel (${meta.forbiddenText})`);
  }
  const entry = {
    width,
    name,
    url,
    partyId: meta.partyId ?? null,
    expectedState: meta.expectedState,
    interaction: meta.interaction,
    files: {},
  };
  const rest = join(shots, `${width}-${name}-rest.png`);
  await page.screenshot({ path: rest, fullPage: false });
  entry.files.rest = rest;
  await page.evaluate(() => window.scrollTo(0, Math.min(480, document.body.scrollHeight)));
  await page.waitForTimeout(150);
  const scroll = join(shots, `${width}-${name}-scroll.png`);
  await page.screenshot({ path: scroll, fullPage: false });
  entry.files.scroll = scroll;
  await page.evaluate(() => window.scrollTo(0, 0));
  const full = join(shots, `${width}-${name}-full.png`);
  await page.screenshot({ path: full, fullPage: true });
  entry.files.full = full;
  journal.push(entry);
}

async function shotWidths(page, name, meta) {
  for (const width of WIDTHS) {
    await shotSet(page, width, name, {
      ...meta,
      interaction: width === 1280 ? meta.interaction : "photographed-after-resize",
    });
  }
}

async function login(page, token) {
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.getByLabel("Token local").fill(token);
  await page.getByRole("button", { name: "Entrar na demonstração" }).click();
  await page.getByRole("button", { name: "Cadastros" }).waitFor({ timeout: 30000 });
}

async function openCadastros(page) {
  await page.getByRole("button", { name: "Cadastros" }).click();
  await page.getByRole("heading", { name: "Clientes e fornecedores" }).waitFor({ timeout: 15000 });
}

function cnpjFromStamp() {
  const base = `8${Date.now().toString().slice(-11)}`.slice(0, 12);
  const values = [...base].map((char) => char.charCodeAt(0) - 48);
  const digit = (weights) => {
    const sum = values.reduce((total, value, index) => total + value * weights[index], 0);
    const rem = sum % 11;
    return rem < 2 ? 0 : 11 - rem;
  };
  const first = digit([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  values.push(first);
  const second = digit([6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]);
  const raw = `${base}${first}${second}`;
  return `${raw.slice(0, 2)}.${raw.slice(2, 5)}.${raw.slice(5, 8)}/${raw.slice(8, 12)}-${raw.slice(12)}`;
}

async function waitSavedParty(page, submitName) {
  const pending = page.waitForResponse((response) => {
    const url = response.url();
    const method = response.request().method();
    return url.includes("/api/v1/catalogs/parties") && ["POST", "PUT"].includes(method);
  }, { timeout: 20000 });
  await page.getByRole("button", { name: submitName }).click();
  const response = await pending;
  const saved = await response.json().catch(() => ({}));
  if (!response.ok() || !saved?.id) {
    fail(`gravacao recusada status=${response.status()} body=${JSON.stringify(saved)}`);
  }
  await page.waitForURL(new RegExp(`/catalogs/counterparties/${saved.id}$`), { timeout: 15000 });
  await page.getByLabel("Razão social ou nome").waitFor();
  return saved;
}

const runId = `013-${Date.now().toString(36)}`;
const minName = `Cliente minimo ${runId}`;
const fullName = `Fornecedor completo ${runId}`;
const fullDocument = cnpjFromStamp();
const titleName = `Via titulo ${runId}`;

const creds = tokens();
if (!creds.operator || !creds.viewer) {
  fail("Tokens de demonstracao ausentes.");
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
page.on("dialog", (dialog) => dialog.accept());
page.setDefaultTimeout(20000);

await login(page, creds.operator);
const me = await apiGet(page.request, creds.operator, "/api/v1/access/me");
const companyId = me.authorizedCompanies?.[0]?.id ?? me.authorizedCompanyDetails?.[0]?.id;
if (!companyId) {
  fail("access/me sem empresa.");
}

await openCadastros(page);
await page.setViewportSize({ width: 1280, height: 960 });
await shotWidths(page, "lista", {
  expectedUrlPart: "/catalogs/counterparties",
  expectedText: "Busca consulta a lista",
  expectedState: "lista da empresa demo, sem credencial",
  interaction: "clicked-cadastros",
  forbiddenText: "Isto não é conector Panne",
});

await page.setViewportSize({ width: 1280, height: 960 });
await page.getByRole("button", { name: "Cadastrar", exact: true }).click();
await page.getByRole("group", { name: "Identificação" }).waitFor();
if ((await page.locator("body").innerText()).includes("Não invente número")) {
  fail("frase interna ainda no formulario");
}
await shotWidths(page, "cadastrar-vazio", {
  expectedUrlPart: "/catalogs/counterparties/new",
  expectedText: "Documento opcional",
  expectedState: "formulario vazio alinhado",
  interaction: "clicked-cadastrar",
});

await page.setViewportSize({ width: 1280, height: 960 });
await page.getByLabel("Razão social ou nome").fill(minName);
await page.getByRole("checkbox", { name: "Cliente" }).check();
await page.getByRole("checkbox", { name: "Fornecedor" }).uncheck();
const minSaved = await waitSavedParty(page, "Cadastrar cliente");
const minLoaded = await apiGet(
  page.request,
  creds.operator,
  `/api/v1/catalogs/parties/${minSaved.id}?companyId=${companyId}`,
);
if (minLoaded.name !== minName || minLoaded.documentPending !== true) {
  fail(`minimo nao persistiu: ${JSON.stringify(minLoaded)}`);
}
await shotWidths(page, "cadastro-minimo", {
  expectedUrlPart: `/catalogs/counterparties/${minSaved.id}`,
  expectedText: minName,
  expectedState: "detalhe apos gravacao minima",
  interaction: "clicked-submit-minimo",
  partyId: minSaved.id,
});

await page.getByRole("button", { name: "Voltar à lista" }).click();
await page.getByRole("link", { name: minName }).click();
await page.waitForURL(new RegExp(`/catalogs/counterparties/${minSaved.id}$`));
const minReloaded = await apiGet(
  page.request,
  creds.operator,
  `/api/v1/catalogs/parties/${minSaved.id}?companyId=${companyId}`,
);
if (minReloaded.name !== minName) {
  fail("recarga do minimo divergiu");
}
await shotWidths(page, "detalhe-minimo-recarga", {
  expectedUrlPart: `/catalogs/counterparties/${minSaved.id}`,
  expectedText: minName,
  expectedState: "mesmo ID e nome apos voltar e reabrir",
  interaction: "clicked-reabrir-minimo",
  partyId: minSaved.id,
});

await page.getByRole("button", { name: "Cadastros" }).click();
await page.getByRole("button", { name: "Cadastrar", exact: true }).click();
await page.getByLabel("Razão social ou nome").fill(fullName);
await page.getByRole("checkbox", { name: "Cliente" }).uncheck();
await page.getByRole("checkbox", { name: "Fornecedor" }).check();
await page.getByLabel("Tipo de pessoa").selectOption("LEGAL");
await page.getByLabel("Tipo do documento").selectOption("CNPJ");
await page.getByLabel("Número do documento").fill(fullDocument);
await page.getByRole("button", { name: "Adicionar unidade" }).click();
await page.getByLabel("Nome da unidade").fill("Sede 013");
await page.getByRole("button", { name: "Adicionar endereço" }).click();
await page.getByLabel("CEP ou código postal").fill("01001-000");
await page.getByLabel("Logradouro").fill("Praça da Sé");
await page.getByRole("textbox", { name: "Número", exact: true }).fill("100");
await page.getByLabel("Município").fill("São Paulo");
await page.getByLabel("UF ou região").fill("SP");
await page.getByRole("button", { name: "Adicionar contato" }).click();
await page.locator("fieldset").filter({ hasText: "Contatos" }).getByLabel("Nome").fill("Ana Completo");
await page.getByLabel("Função").fill("Compras");
await page.getByRole("button", { name: "Adicionar fornecimento" }).click();
await page.getByLabel("Produto ou serviço").fill("Farinha 013");
const fullSaved = await waitSavedParty(page, "Cadastrar fornecedor");
const fullLoaded = await apiGet(
  page.request,
  creds.operator,
  `/api/v1/catalogs/parties/${fullSaved.id}?companyId=${companyId}`,
);
if (
  fullLoaded.name !== fullName ||
  fullLoaded.units?.[0]?.name !== "Sede 013" ||
  fullLoaded.addresses?.[0]?.street !== "Praça da Sé" ||
  fullLoaded.contacts?.[0]?.name !== "Ana Completo" ||
  fullLoaded.supplies?.[0]?.description !== "Farinha 013"
) {
  fail(`completo nao persistiu: ${JSON.stringify(fullLoaded)}`);
}

await page.setViewportSize({ width: 360, height: 820 });
await page.getByLabel("Razão social ou nome").focus();
await page.waitForTimeout(200);
await shotSet(page, 360, "cadastro-completo-foco", {
  expectedUrlPart: `/catalogs/counterparties/${fullSaved.id}`,
  expectedText: fullName,
  expectedState: "campo focado abaixo do cabecalho sticky em 360",
  interaction: "clicked-focus-nome",
  partyId: fullSaved.id,
});

await shotWidths(page, "cadastro-completo", {
  expectedUrlPart: `/catalogs/counterparties/${fullSaved.id}`,
  expectedText: fullName,
  expectedState: "detalhe apos gravacao completa com unidade/endereco/contato/fornecimento",
  interaction: "clicked-submit-completo",
  partyId: fullSaved.id,
});

await page.setViewportSize({ width: 1280, height: 960 });
await page.getByLabel("Nome fantasia").fill("Fantasia 013");
const edited = await waitSavedParty(page, "Salvar alterações");
if (edited.id !== fullSaved.id || edited.tradeName !== "Fantasia 013") {
  fail("edicao nao persistiu no mesmo ID");
}
await page.getByRole("button", { name: "Voltar à lista" }).click();
await page.getByLabel("Buscar").fill(fullName);
await page.getByRole("button", { name: "Buscar" }).click();
await page.getByRole("link", { name: fullName }).click();
await page.waitForURL(new RegExp(`/catalogs/counterparties/${fullSaved.id}$`));
const editedReload = await apiGet(
  page.request,
  creds.operator,
  `/api/v1/catalogs/parties/${fullSaved.id}?companyId=${companyId}`,
);
if (
  editedReload.tradeName !== "Fantasia 013" ||
  (editedReload.documentNumber !== fullDocument && editedReload.documentNumber !== fullDocument.replace(/\D/g, ""))
) {
  fail("recarga apos edicao divergiu");
}
await page.getByLabel("Nome fantasia").waitFor();
if ((await page.getByLabel("Nome fantasia").inputValue()) !== "Fantasia 013") {
  fail("campo nome fantasia nao recarregou o valor persistido");
}
await shotWidths(page, "edicao-recarga", {
  expectedUrlPart: `/catalogs/counterparties/${fullSaved.id}`,
  expectedText: fullName,
  expectedState: "mesmo ID apos edicao e reabertura; fantasia persistida no campo",
  interaction: "clicked-salvar-e-reabrir",
  partyId: fullSaved.id,
});

await page.getByRole("button", { name: "Cadastros" }).click();
await page.getByRole("button", { name: "Cadastrar", exact: true }).click();
await page.getByLabel("Razão social ou nome").fill("Tentativa duplicada 013");
await page.getByRole("checkbox", { name: "Cliente" }).uncheck();
await page.getByRole("checkbox", { name: "Fornecedor" }).check();
await page.getByLabel("Tipo do documento").selectOption("CNPJ");
await page.getByLabel("Número do documento").fill(fullDocument);
const dupResponse = page.waitForResponse(
  (response) => response.url().includes("/catalogs/parties") && response.request().method() === "POST",
);
await page.getByRole("button", { name: "Cadastrar fornecedor" }).click();
const dup = await dupResponse;
if (dup.ok()) {
  fail("duplicidade foi gravada");
}
await page.getByText(/já identifica outro cadastro/).waitFor();
if (!page.url().includes("/catalogs/counterparties/new")) {
  fail("duplicidade saiu do formulario Cadastrar");
}
await shotWidths(page, "duplicidade", {
  expectedUrlPart: "/catalogs/counterparties/new",
  expectedText: "já identifica outro cadastro",
  expectedState: "permanece em Cadastrar; caso separado da gravacao",
  interaction: "clicked-submit-duplicado",
});

await page.getByRole("button", { name: "Pagamentos" }).click();
await page.getByRole("button", { name: "Nova conta a pagar" }).click();
await page.getByRole("button", { name: "Cadastrar contraparte" }).click();
await page.getByLabel("Nome").fill(titleName);
const quickPending = page.waitForResponse(
  (response) =>
    response.url().includes("/catalogs/counterparties") &&
    response.request().method() === "POST" &&
    response.ok(),
);
await page.getByRole("button", { name: "Salvar", exact: true }).click();
const quick = await quickPending.then((response) => response.json());
if (!quick?.id) {
  fail("cadastro rapido no titulo sem id");
}
const quickLoaded = await apiGet(
  page.request,
  creds.operator,
  `/api/v1/catalogs/parties/${quick.id}?companyId=${companyId}`,
);
if (quickLoaded.name !== titleName || quickLoaded.documentPending !== true) {
  fail("cadastro rapido nao persistiu pendente");
}
await shotWidths(page, "titulo-cadastro-rapido", {
  expectedUrlPart: "/payables/new",
  expectedText: "Cadastrar contraparte",
  expectedState: `API persistiu ${quick.id} (${titleName}, documento pendente)`,
  interaction: "clicked-cadastrar-contraparte",
  partyId: quick.id,
});

await page.getByRole("button", { name: "Cadastros" }).click();
await page.getByRole("button", { name: "Importar arquivo" }).click();
await page.locator('input[type="file"]').setInputFiles({
  name: "invalido-013.csv",
  mimeType: "text/csv",
  buffer: Buffer.from(
    "nome;relacao;tipo_pessoa;pais_documento;tipo_documento;documento\nLinha invalida;FORNECEDOR;JURIDICA;BR;CNPJ;12.ABC.345/0001-95\n",
    "utf8",
  ),
});
await page.getByRole("button", { name: "Validar arquivo" }).click();
await page.getByRole("cell", { name: "Inválido", exact: true }).waitFor();
const confirm = page.getByRole("button", { name: "Confirmar linhas selecionadas" });
if (await confirm.isEnabled()) {
  fail("confirmar habilitado sem linha elegivel");
}
await page.getByText(/1 inválido/).waitFor();
await shotWidths(page, "importacao-erro", {
  expectedUrlPart: "/catalogs/counterparties/import",
  expectedText: "1 inválido",
  expectedState: "INVALID traduzido; confirmar indisponivel",
  interaction: "clicked-validar-csv",
});

const viewer = await browser.newPage();
viewer.on("dialog", (dialog) => dialog.accept());
await login(viewer, creds.viewer);
await openCadastros(viewer);
await viewer.getByLabel("Buscar").fill(fullName);
await viewer.getByRole("button", { name: "Buscar" }).click();
await viewer.getByRole("link", { name: fullName }).click();
await viewer.waitForURL(new RegExp(`/catalogs/counterparties/${fullSaved.id}$`));
if (await viewer.getByRole("button", { name: "Salvar alterações" }).count()) {
  fail("viewer conseguiu acao de escrita");
}
if (await viewer.getByLabel("Razão social ou nome").isEnabled()) {
  fail("viewer editou nome");
}
await shotWidths(viewer, "somente-leitura", {
  expectedUrlPart: `/catalogs/counterparties/${fullSaved.id}`,
  expectedText: fullName,
  expectedState: "consulta sem gravar",
  interaction: "clicked-abrir-detalhe-viewer",
  partyId: fullSaved.id,
});

await browser.close();
const payload = {
  capturedAt: new Date().toISOString(),
  baseUrl,
  personalData: "synthetic-only",
  ids: {
    minimo: minSaved.id,
    completo: fullSaved.id,
    tituloRapido: quick.id,
  },
  notes: {
    fullPage: "A captura full costura o cabecalho sticky; rest e scroll mostram a tela visivel.",
    deletedNothing: true,
  },
  files: journal,
};
await writeFile(join(evidence, "capturas.json"), JSON.stringify(payload, null, 2));
console.log(`captured=${journal.length} minimo=${minSaved.id} completo=${fullSaved.id} titulo=${quick.id}`);
