/**
 * Capturas “antes” do backoffice. Só loopback.
 * Reexecutar: node scripts/p107-capture-backoffice.mjs
 * Playwright não está nas dependências do frontend; o script usa o mesmo
 * puppeteer-core + Chrome dos scripts/p86-capture.mjs, com origem local.
 */
import { mkdirSync, readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = process.env.P107_ORIGIN || "http://127.0.0.1:5175";
if (!/^http:\/\/(127\.0\.0\.1|localhost):5175$/.test(origin)) {
  throw new Error("recusando captura fora do Vite local :5175");
}
const outDir = join(root, "readme", "evidence", "prompt-107", "antes");
mkdirSync(outDir, { recursive: true });

const require = createRequire(
  process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const shots = [
  ["T-acesso-01", "entrada", "/#acesso"],
  ["T-pedidos-01", "home", "/admin/pedidos"],
  ["T-produtos-01", "lista", "/admin/produtos"],
  ["T-produtos-02", "novo", "/admin/produtos/novo"],
  ["T-produtos-06", "lista", "/admin/produtos/receitas"],
  ["T-produtos-08", "nova", "/admin/produtos/receitas/nova"],
  ["T-produtos-10", "notas", "/admin/produtos/gigio"],
  ["T-produtos-11", "lista", "/admin/produtos/gigio/harmonizacoes"],
  ["T-produtos-12", "lista", "/admin/produtos/complementos"],
  ["T-agenda-01", "semana", "/admin/agenda"],
  ["T-fidelidade-01", "participantes", "/admin/fidelidade"],
];

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ["--no-first-run", "--disable-extensions"],
});
const page = await browser.newPage();

async function settle() {
  await page.waitForNetworkIdle({ idleTime: 400, timeout: 8000 }).catch(() => {});
}

try {
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(`${origin}/#acesso`, { waitUntil: "domcontentloaded" });
  await settle();
  await page.screenshot({ path: join(outDir, "T-acesso-01-entrada-1280.png"), fullPage: true });
  await page.setViewport({ width: 390, height: 844 });
  await settle();
  await page.screenshot({ path: join(outDir, "T-acesso-01-entrada-390.png"), fullPage: true });
  await page.setViewport({ width: 1280, height: 800 });

  const loggedOut = await browser.createBrowserContext();
  const denied = await loggedOut.newPage();
  await denied.setViewport({ width: 1280, height: 800 });
  await denied.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await denied.waitForNetworkIdle({ idleTime: 400, timeout: 8000 }).catch(() => {});
  await denied.screenshot({ path: join(outDir, "T-acesso-02-sem-sessao-1280.png"), fullPage: true });
  await denied.setViewport({ width: 390, height: 844 });
  await denied.screenshot({ path: join(outDir, "T-acesso-02-sem-sessao-390.png"), fullPage: true });
  await loggedOut.close();

  const enter = await page.waitForSelector("button.header-access-local-enter", { timeout: 8000 });
  if (enter) {
    await enter.click();
    await page.waitForFunction(() => location.pathname.startsWith("/admin") || document.body.innerText.includes("Pedidos"), {
      timeout: 8000,
    }).catch(() => {});
    await settle();
  }

  for (const [id, state, path] of shots) {
    if (id === "T-acesso-01") {
      continue;
    }
    await page.goto(`${origin}${path}`, { waitUntil: "domcontentloaded" });
    await settle();
    await page.screenshot({ path: join(outDir, `${id}-${state}-1280.png`), fullPage: true });
    await page.setViewport({ width: 390, height: 844 });
    await settle();
    await page.screenshot({ path: join(outDir, `${id}-${state}-390.png`), fullPage: true });
    await page.setViewport({ width: 1280, height: 800 });
  }

  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await settle();
  const notices = await page.$("button.admin-notices-toggle");
  if (notices) {
    await notices.click();
    await settle();
    await page.screenshot({ path: join(outDir, "T-acesso-03-painel-1280.png"), fullPage: true });
    await page.setViewport({ width: 390, height: 844 });
    await page.screenshot({ path: join(outDir, "T-acesso-03-painel-390.png"), fullPage: true });
    await page.setViewport({ width: 1280, height: 800 });
  }

  const ids = JSON.parse(
    readFileSync(join(root, "readme", "evidence", "prompt-107", "capture-ids.json"), "utf8"),
  );

  async function both(name) {
    await settle();
    await page.setViewport({ width: 1280, height: 800 });
    await page.screenshot({ path: join(outDir, `${name}-1280.png`), fullPage: true });
    await page.setViewport({ width: 390, height: 844 });
    await settle();
    await page.screenshot({ path: join(outDir, `${name}-390.png`), fullPage: true });
    await page.setViewport({ width: 1280, height: 800 });
  }

  async function openOrder(id) {
    await page.goto(`${origin}/admin/pedidos/${id}`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => document.body.innerText.includes("Cliente Exemplo"), { timeout: 8000 }).catch(() => {});
    await settle();
  }

  async function chooseLens(value) {
    await page.evaluate((next) => {
      const select = [...document.querySelectorAll("select")].find((node) =>
        [...node.options].some((option) => option.value === next),
      );
      if (!select) {
        return;
      }
      select.value = next;
      select.dispatchEvent(new Event("change", { bubbles: true }));
    }, value);
    await page.click("form.admin-filters button.admin-primary");
    await settle();
  }

  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await settle();
  await chooseLens("all");
  await page.waitForFunction(() => document.body.innerText.includes("Todos os estados"), { timeout: 8000 }).catch(() => {});
  await both("T-pedidos-04-lista");
  await chooseLens("stage:paid");
  await both("T-pedidos-04-lente");

  const stages = [
    "aberto",
    "aceito",
    "pago",
    "em-producao",
    "pronto",
    "entregue",
    "finalizado",
    "cancelado",
    "endereco-pendente",
    "verificacao",
    "varias-linhas",
  ];
  for (const stage of stages) {
    await openOrder(ids.orders[stage]);
    await both(`T-pedidos-05-${stage}`);
  }
  await openOrder(ids.orders.aberto);
  await both("T-pedidos-13-adaptacao");
  await both("T-pedidos-14-notas");
  await openOrder(ids.orders.proposta);
  await both("T-pedidos-12-proposta");
  await openOrder(ids.orders.excecao);
  await both("T-pedidos-05-excecao");

  await openOrder(ids.orders.aceito);
  const start = await page.evaluateHandle(() =>
    [...document.querySelectorAll("button")].find((node) => node.textContent.includes("Iniciar produção")),
  );
  if (start) {
    await start.click();
    await page.waitForSelector("[role=dialog]", { timeout: 8000 }).catch(() => {});
    await both("T-pedidos-07-excecao");
    const back = await page.$("[role=dialog] button.admin-secondary");
    if (back) {
      await back.click();
    }
  }

  await openOrder(ids.orders["dialogo-cancelamento"]);
  const cancel = await page.$("button.admin-danger");
  if (cancel) {
    await cancel.click();
    await settle();
    await both("T-pedidos-11-sem-motivo");
    await page.type("form.admin-cancel textarea", "cliente de exemplo desistiu na captura");
    await both("T-pedidos-11-com-motivo");
    await page.click("form.admin-cancel button.admin-danger");
    await page.waitForFunction(() => document.body.innerText.includes("Cancelado"), { timeout: 8000 }).catch(() => {});
    await both("T-pedidos-11-resultado");
  }

  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await settle();
  await chooseLens("date_pending");
  await both("T-pedidos-16-lista");
  for (const [state, id] of Object.entries(ids.date_requests)) {
    await page.goto(`${origin}/admin/pedidos/solicitacao/${id}`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => document.body.innerText.includes("Cliente Exemplo"), { timeout: 8000 }).catch(() => {});
    await both(`T-pedidos-16-${state}`);
  }
  await page.goto(`${origin}/admin/pedidos/solicitacao/${ids.date_requests.pendente}`, {
    waitUntil: "domcontentloaded",
  });
  await settle();
  const propose = await page.evaluateHandle(() =>
    [...document.querySelectorAll("button")].find((node) => node.textContent.includes("Propor outra data")),
  );
  if (propose) {
    await propose.asElement().click();
    await settle();
    await both("T-pedidos-17-propor");
  }
  await page.goto(`${origin}/admin/pedidos/solicitacao/${ids.date_requests.proposta}`, {
    waitUntil: "domcontentloaded",
  });
  await settle();
  await both("T-pedidos-17-resultado");
  await page.goto(`${origin}/admin/pedidos/solicitacao/${ids.date_requests.complemento}`, {
    waitUntil: "domcontentloaded",
  });
  await settle();
  await both("T-pedidos-18-complemento");
  await page.goto(`${origin}/admin/pedidos/solicitacao/${ids.date_requests.encerrada}`, {
    waitUntil: "domcontentloaded",
  });
  await settle();
  await both("T-pedidos-19-encerrada");
  await page.goto(`${origin}/admin/pedidos/solicitacao/${ids.date_requests.pendente}`, {
    waitUntil: "domcontentloaded",
  });
  await page.waitForFunction(() => document.body.innerText.includes("Prévia"), { timeout: 8000 }).catch(() => {});
  await both("T-pedidos-20-previa");
  await page.goto(`${origin}/admin/pedidos/solicitacao/${ids.date_requests.convertida}`, {
    waitUntil: "domcontentloaded",
  });
  await settle();
  await both("T-pedidos-20-resultado");

  await page.goto(`${origin}/admin/produtos/${ids.products.publicado}`, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => document.body.innerText.includes("Pão Exemplo"), { timeout: 8000 }).catch(() => {});
  await both("T-produtos-03-editor");
  await page.goto(`${origin}/admin/produtos/${ids.products.rascunho}`, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => document.body.innerText.includes("Apagar"), { timeout: 8000 }).catch(() => {});
  await both("T-produtos-04-acoes");

  await page.goto(`${origin}/admin/agenda`, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => document.body.innerText.includes("viagem de exemplo"), { timeout: 8000 }).catch(() => {});
  await both("T-agenda-03-fechamento");
  const reopen = await page.evaluateHandle(() =>
    [...document.querySelectorAll("button")].find((node) => node.textContent.includes("Reabrir este bloqueio")),
  );
  const reopenButton = reopen.asElement();
  if (reopenButton) {
    await reopenButton.click();
    await settle();
    await both("T-agenda-04-confirmacao");
    const confirmHandle = await page.evaluateHandle(() =>
      [...document.querySelectorAll("button")].find((node) => node.textContent.includes("Confirmar reabertura")),
    );
    const confirm = confirmHandle.asElement();
    if (confirm) {
      await confirm.click();
      await settle();
      await both("T-agenda-04-resultado");
    }
  }

  await page.goto(`${origin}/admin/fidelidade`, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => document.body.innerText.includes("Cliente Exemplo Fidelidade"), { timeout: 8000 }).catch(() => {});
  const participantHandle = await page.evaluateHandle(() =>
    [...document.querySelectorAll("button")].find((node) => node.textContent.trim() === "Ver detalhes"),
  );
  const participant = participantHandle.asElement();
  if (participant) {
    await participant.click();
    await page.waitForFunction(() => document.body.innerText.includes("Ajuste manual"), { timeout: 8000 }).catch(() => {});
    await both("T-fidelidade-02-ajuste");
  }

  const account = await page.$("button.header-access-account");
  if (account) {
    await account.click();
    await settle();
    await both("T-acesso-05-menu");
    const leaveHandle = await page.evaluateHandle(() =>
      [...document.querySelectorAll("[role=menuitem], button")].find((node) => node.textContent.trim() === "Sair"),
    );
    const leave = leaveHandle.asElement();
    if (leave) {
      await leave.click();
      await settle();
      await both("T-acesso-05-sair");
    }
  }
} finally {
  await browser.close();
}
console.log(outDir);
