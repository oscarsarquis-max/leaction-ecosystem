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
const outRel = process.env.P107_OUT || join("readme", "evidence", "prompt-107", "antes");
if (outRel.includes("..") || outRel.startsWith("/") || outRel.includes(":")) {
  throw new Error("P107_OUT tem de ficar dentro do repositório da loja");
}
const outDir = join(root, outRel);
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

  if (process.env.P107_DRAWER === "1") {
    await page.goto(`${origin}/`, { waitUntil: "domcontentloaded" });
    await settle();
    const gigioHome = await page.waitForSelector("button.gigio-launch", { timeout: 8000 }).catch(() => null);
    if (!gigioHome) {
      throw new Error("Gigio ausente na vitrine");
    }
    await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
    await settle();
    const gigioAdmin = await page.$("button.gigio-launch, .gigio-host");
    if (gigioAdmin) {
      throw new Error("Gigio apareceu no admin");
    }
    for (const width of [320, 390, 960, 1280, 1440]) {
      await page.setViewport({ width, height: 800 });
      await settle();
      const overflow = await page.evaluate(() => ({
        scroll: document.documentElement.scrollWidth,
        client: document.documentElement.clientWidth,
      }));
      if (overflow.scroll > overflow.client + 1) {
        throw new Error(`rolagem horizontal em ${width}px: ${overflow.scroll} > ${overflow.client}`);
      }
    }
    await page.setViewport({ width: 1280, height: 800 });
    const contrast = await page.evaluate(() => {
      const parse = (color) => {
        const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)(?:,\s*([\d.]+))?\)/);
        if (!match) {
          return null;
        }
        return {
          rgb: [Number(match[1]), Number(match[2]), Number(match[3])],
          alpha: match[4] === undefined ? 1 : Number(match[4]),
        };
      };
      const channel = (value) => {
        const scaled = value / 255;
        return scaled <= 0.03928 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4;
      };
      const luminance = (rgb) => 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2]);
      const ratio = (foreground, background) => {
        const left = luminance(foreground);
        const right = luminance(background);
        const lighter = Math.max(left, right);
        const darker = Math.min(left, right);
        return (lighter + 0.05) / (darker + 0.05);
      };
      const sample = (selector) => {
        const node = document.querySelector(selector);
        if (!node) {
          return { selector, missing: true };
        }
        const foreground = parse(getComputedStyle(node).color);
        let cursor = node;
        let background = null;
        while (cursor) {
          const parsed = parse(getComputedStyle(cursor).backgroundColor);
          if (parsed && parsed.alpha > 0.5) {
            background = parsed.rgb;
            break;
          }
          cursor = cursor.parentElement;
        }
        if (!foreground || !background) {
          return { selector, unparsed: true, color: getComputedStyle(node).color };
        }
        return { selector, ratio: Number(ratio(foreground.rgb, background).toFixed(2)) };
      };
      return [".admin-brand-name", ".ng", ".nl", ".nl.off", ".soon", ".admin-trail", ".admin-trail strong"].map(sample);
    });
    console.log(JSON.stringify(contrast));
    for (const item of contrast) {
      if (item.missing || item.unparsed || item.ratio < 4.5) {
        throw new Error(`contraste abaixo de 4.5: ${JSON.stringify(item)}`);
      }
    }
    await page.setViewport({ width: 390, height: 844 });
    await settle();
    const drawerButton = await page.waitForSelector("button.admin-menu-button", { timeout: 8000 });
    await drawerButton.click();
    await page.waitForFunction(
      () => document.querySelector("button.admin-menu-button")?.getAttribute("aria-expanded") === "true",
      { timeout: 4000 },
    );
    const drawerOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
    );
    if (!drawerOverflow) {
      throw new Error("rolagem horizontal com a gaveta aberta");
    }
    await page.screenshot({ path: join(outDir, "gaveta-aberta-390.png"), fullPage: false });
    await page.keyboard.press("Escape");
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
    const menu = await page.$("button.admin-menu-button");
    if (menu) {
      const expanded = await page.$eval("button.admin-menu-button", (node) => node.getAttribute("aria-expanded"));
      if (expanded !== "true") {
        await menu.click();
      }
      await settle();
    }
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
    let leaveHandle = await page.evaluateHandle(() =>
      [...document.querySelectorAll("[role=menuitem], button")].find((node) => node.textContent.trim() === "Sair"),
    );
    if (!leaveHandle.asElement()) {
      const again = await page.$("button.header-access-account");
      if (again) {
        await again.click();
        await settle();
      }
      leaveHandle = await page.evaluateHandle(() =>
        [...document.querySelectorAll("[role=menuitem], button")].find((node) => node.textContent.trim() === "Sair"),
      );
    }
    const leave = leaveHandle.asElement();
    if (leave) {
      await page.evaluate(() => {
        const node = [...document.querySelectorAll("[role=menuitem], button")].find((item) => item.textContent.trim() === "Sair");
        if (node instanceof HTMLElement) {
          node.click();
        }
      });
      await settle();
      await both("T-acesso-05-sair");
    }
  }
} finally {
  await browser.close();
}
console.log(outDir);
