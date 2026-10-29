import { readFileSync } from "node:fs";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const shots = join(root, "documents", "reviews", "screenshots", "fechamento-cadastros-014");
const evidence = join(root, "documents", "reviews", "evidence", "fechamento-cadastros-014");
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_LOCAL_UI_URL ?? "http://127.0.0.1:5179";
if (baseUrl.includes(":4179") && process.env.ACTIONFINANCE_ALLOW_PREVIEW !== "1") {
  throw new Error("Candidata 014 usa Vite em :5179.");
}

const journal = [];

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

async function api(request, token, path, init = {}) {
  const response = await request.fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/json",
      ...(init.headers ?? {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok()) {
    fail(`${init.method ?? "GET"} ${path} status=${response.status()} body=${JSON.stringify(body)}`);
  }
  return body;
}

async function shot(page, width, name, meta) {
  await page.setViewportSize({ width, height: width <= 400 ? 820 : 960 });
  if (!meta.keepScroll) {
    await page.evaluate(() => window.scrollTo(0, 0));
  }
  await page.waitForTimeout(200);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) {
    fail(`${name} @${width}: rolagem horizontal da pagina`);
  }
  const url = page.url();
  const text = await page.locator("body").innerText();
  if (meta.expectedText && !text.includes(meta.expectedText)) {
    fail(`${name} @${width}: texto ausente (${meta.expectedText})`);
  }
  const file = join(shots, `${width}-${name}.png`);
  await page.screenshot({ path: file, fullPage: false });
  journal.push({
    width,
    name,
    url,
    interaction: meta.interaction,
    expectedState: meta.expectedState,
    partyId: meta.partyId ?? null,
    file,
  });
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

async function assertNoPageScroll(page, label) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  if (overflow) {
    fail(`${label}: rolagem horizontal da pagina`);
  }
}

const creds = tokens();
if (!creds.operator) {
  fail("Token de demonstracao ausente.");
}

const runId = `014-${Date.now().toString(36)}`;
const anchorName = `Ancora ${runId}`;
const validName = `Valida ${runId}`;
const invalidName = `Invalida ${runId}`;
const valid768 = `Valida768 ${runId}`;
const anchorDoc = cnpjFromStamp();
await new Promise((resolve) => setTimeout(resolve, 5));
const validDoc = cnpjFromStamp();
await new Promise((resolve) => setTimeout(resolve, 5));
const valid768Doc = cnpjFromStamp();

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
page.on("dialog", (dialog) => dialog.accept());
page.setDefaultTimeout(20000);

await login(page, creds.operator);
const me = await api(page.request, creds.operator, "/api/v1/access/me");
const companyId = me.authorizedCompanies?.[0]?.id ?? me.authorizedCompanyDetails?.[0]?.id;
if (!companyId) {
  fail("access/me sem empresa");
}
const info = await api(page.request, creds.operator, "/api/v1/system/info");

await openCadastros(page);
await page.setViewportSize({ width: 1280, height: 960 });
await page.getByRole("button", { name: "Cadastrar", exact: true }).click();
await page.getByLabel("Razão social ou nome").fill(anchorName);
await page.getByRole("checkbox", { name: "Cliente" }).uncheck();
await page.getByRole("checkbox", { name: "Fornecedor" }).check();
await page.getByLabel("Tipo de pessoa").selectOption("LEGAL");
await page.getByLabel("Tipo do documento").selectOption("CNPJ");
await assertNoPageScroll(page, "1280 CNPJ");
await shot(page, 1280, "documento-cnpj", {
  expectedText: "País do documento",
  expectedState: "caixas de documento alinhadas; CNPJ visivel",
  interaction: "clicked-tipo-cnpj",
});
await page.getByLabel("Tipo do documento").selectOption("OTHER");
await shot(page, 1280, "documento-outro", {
  expectedText: "Outro",
  expectedState: "tipo Outro sem corte do texto",
  interaction: "clicked-tipo-outro",
});
await page.getByLabel("Tipo do documento").selectOption("CNPJ");
await page.getByLabel("Número do documento").fill(anchorDoc);
await page.setViewportSize({ width: 640, height: 960 });
await assertNoPageScroll(page, "640 equivalente a 1280 em 200%");
await shot(page, 640, "documento-zoom-200", {
  expectedText: "Número do documento",
  expectedState: "viewport 640 = 1280 em zoom 200%; uma coluna; sem rolagem horizontal",
  interaction: "clicked-viewport-640",
});

for (const width of [360, 768]) {
  await page.setViewportSize({ width, height: 820 });
  await page.getByLabel("Tipo do documento").selectOption("OTHER");
  await assertNoPageScroll(page, `${width} Outro`);
  await shot(page, width, "documento-outro", {
    expectedText: "Outro",
    expectedState: "uma coluna; sem rolagem horizontal",
    interaction: "clicked-tipo-outro",
  });
  await page.getByLabel("Tipo do documento").selectOption("CNPJ");
}

const pending = page.waitForResponse((response) => response.url().includes("/api/v1/catalogs/parties") && response.request().method() === "POST");
await page.getByRole("button", { name: "Cadastrar fornecedor" }).click();
const anchor = await pending.then((response) => response.json());
if (!anchor?.id) {
  fail("ancora nao persistiu");
}
await page.waitForURL(new RegExp(`/catalogs/counterparties/${anchor.id}$`));

const detailUrl = `${baseUrl}/catalogs/counterparties/${anchor.id}`;
await page.reload({ waitUntil: "domcontentloaded" });
await page.waitForTimeout(500);
const afterReload = page.url();
await login(page, creds.operator);
await openCadastros(page);
await page.getByLabel("Buscar").fill(anchorName);
await page.getByRole("button", { name: "Buscar" }).click();
await page.getByRole("link", { name: anchorName }).click();
await page.waitForURL(new RegExp(`/catalogs/counterparties/${anchor.id}$`));
const reloaded = await api(page.request, creds.operator, `/api/v1/catalogs/parties/${anchor.id}?companyId=${companyId}`);
if (reloaded.id !== anchor.id || reloaded.name !== anchorName) {
  fail("recarga real nao devolveu o mesmo ID");
}
await shot(page, 1280, "recarga-real", {
  expectedText: anchorName,
  expectedState: `reload de ${detailUrl} (ficou ${afterReload}); reautenticacao demo sem persistir token`,
  interaction: "clicked-reload-e-reabrir",
  partyId: anchor.id,
});

async function importMixed(width, validLineName, validLineDoc) {
  await page.setViewportSize({ width, height: width <= 400 ? 820 : 960 });
  await openCadastros(page);
  await page.getByRole("button", { name: "Importar arquivo" }).click();
  const csv = [
    "nome;relacao;tipo_pessoa;pais_documento;tipo_documento;documento",
    `${validLineName};FORNECEDOR;JURIDICA;BR;CNPJ;${validLineDoc}`,
    `${invalidName};FORNECEDOR;JURIDICA;BR;CNPJ;12.ABC.345/0001-95`,
    `${anchorName};FORNECEDOR;JURIDICA;BR;CNPJ;${anchorDoc}`,
  ].join("\n");
  await page.locator('input[type="file"]').setInputFiles({
    name: `misto-${width}-014.csv`,
    mimeType: "text/csv",
    buffer: Buffer.from(csv, "utf8"),
  });
  await page.getByRole("button", { name: "Validar arquivo" }).click();
  const cards = page.locator(".party-import-cards");
  await cards.getByText(validLineName, { exact: true }).waitFor();
  await cards.getByText("Inválido", { exact: true }).waitFor();
  const cardText = await cards.innerText();
  if (!cardText.includes("Possível duplicado") && !cardText.includes("Conflito")) {
    fail(`${width}: duplicidade/conflito ausente nos cartoes`);
  }
  if (!cardText.includes("dígitos verificadores") && !cardText.toLowerCase().includes("documento")) {
    fail(`${width}: motivo da linha invalida ausente`);
  }
  await cards.locator("li").first().scrollIntoViewIfNeeded();
  await shot(page, width, "importacao-mista-previa", {
    expectedText: "Inválido",
    expectedState: "cartoes com valida, invalida e duplicidade",
    interaction: "clicked-validar-csv",
    keepScroll: true,
  });
  const validBox = cards.getByRole("checkbox", { name: "Incluir linha 1" });
  const dupBox = cards.getByRole("checkbox", { name: "Incluir linha 3" });
  if (!(await validBox.isChecked())) {
    await validBox.check();
  }
  if (await dupBox.isChecked()) {
    await dupBox.uncheck();
  }
  if (await cards.getByRole("checkbox", { name: "Incluir linha 2" }).isEnabled()) {
    fail(`${width}: linha invalida selecionavel`);
  }
  await cards.locator("li").first().scrollIntoViewIfNeeded();
  await shot(page, width, "importacao-mista-selecao", {
    expectedText: "Confirmar linhas selecionadas",
    expectedState: "somente a valida marcada",
    interaction: "clicked-selecionar-apenas-valida",
    keepScroll: true,
  });
  const confirmPending = page.waitForResponse(
    (response) => response.url().includes("/party-imports/") && response.url().includes("/confirm") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Confirmar linhas selecionadas" }).click();
  const confirmed = await confirmPending.then((response) => response.json());
  if (!confirmed.report || confirmed.report.created !== 1) {
    fail(`${width}: confirmacao nao criou 1: ${JSON.stringify(confirmed.report)}`);
  }
  await cards.locator("li").first().scrollIntoViewIfNeeded();
  await shot(page, width, "importacao-mista-confirmada", {
    expectedText: "Criado",
    expectedState: "valida gravada; demais nao",
    interaction: "clicked-confirmar",
    keepScroll: true,
  });
  const created = await api(
    page.request,
    creds.operator,
    `/api/v1/catalogs/parties?companyId=${companyId}&q=${encodeURIComponent(validLineName)}`,
  );
  if (created.totalItems !== 1 || created.items[0].name !== validLineName) {
    fail(`${width}: valida nao persistiu`);
  }
  const invalidPage = await api(
    page.request,
    creds.operator,
    `/api/v1/catalogs/parties?companyId=${companyId}&q=${encodeURIComponent(invalidName)}`,
  );
  if (invalidPage.totalItems !== 0) {
    fail(`${width}: invalida foi gravada`);
  }
  const repeat = await api(page.request, creds.operator, `/api/v1/catalogs/party-imports/${confirmed.id}/confirm?companyId=${companyId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    data: {
      lines: confirmed.lines.map((line) => ({
        id: line.id,
        selected: line.classification === "NEW",
        resolution: "CREATE",
      })),
    },
  });
  if (repeat.report?.created !== 1) {
    fail(`${width}: repeticao do lote duplicou created=${repeat.report?.created}`);
  }
  const afterRepeat = await api(
    page.request,
    creds.operator,
    `/api/v1/catalogs/parties?companyId=${companyId}&q=${encodeURIComponent(validLineName)}`,
  );
  if (afterRepeat.totalItems !== 1) {
    fail(`${width}: repeticao criou segundo cadastro`);
  }
  return { batchId: confirmed.id, createdId: created.items[0].id };
}

const firstImport = await importMixed(360, validName, validDoc);
const secondImport = await importMixed(768, valid768, valid768Doc);

await page.setViewportSize({ width: 1280, height: 960 });
await openCadastros(page);
await page.getByRole("button", { name: "Importar arquivo" }).click();
await page.locator('input[type="file"]').setInputFiles({
  name: "desktop-014.csv",
  mimeType: "text/csv",
  buffer: Buffer.from(`nome;relacao\nSomente desktop ${runId};FORNECEDOR\n`, "utf8"),
});
await page.getByRole("button", { name: "Validar arquivo" }).click();
await page.locator(".desktop-table").getByText(`Somente desktop ${runId}`).waitFor();
await shot(page, 1280, "importacao-desktop", {
  expectedText: `Somente desktop ${runId}`,
  expectedState: "tabela desktop preservada",
  interaction: "clicked-validar-csv",
});

await browser.close();
const payload = {
  capturedAt: new Date().toISOString(),
  baseUrl,
  personalData: "synthetic-only",
  systemInfo: info,
  companyId,
  ids: {
    ancora: anchor.id,
    import360: firstImport.createdId,
    import768: secondImport.createdId,
    lote360: firstImport.batchId,
    lote768: secondImport.batchId,
  },
  files: journal,
};
await writeFile(join(evidence, "capturas.json"), JSON.stringify(payload, null, 2));
console.log(
  `captured=${journal.length} ancora=${anchor.id} import360=${firstImport.createdId} import768=${secondImport.createdId}`,
);
