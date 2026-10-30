/**
 * Captura e mede a casca e a fila de pedidos do 109. Só loopback.
 * node scripts/p109-check.mjs
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = "http://127.0.0.1:5175";
const outDir = join(root, "readme", "evidence", "prompt-109");
mkdirSync(outDir, { recursive: true });

const require = createRequire(
  process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const ids = JSON.parse(readFileSync(join(root, "readme", "evidence", "prompt-107", "capture-ids.json"), "utf8"));

const widths = [320, 390, 768, 960, 1280, 1440];
const routes = [
  ["admin", "/admin"],
  ["pedidos", "/admin/pedidos"],
  ["pedido", `/admin/pedidos/${ids.orders.pago}`],
  ["solicitacao", `/admin/pedidos/solicitacao/${ids.date_requests.pendente}`],
  ["produtos", "/admin/produtos"],
  ["produto-novo", "/admin/produtos/novo"],
  ["produto", `/admin/produtos/${ids.products.publicado}`],
  ["receitas", "/admin/produtos/receitas"],
  ["receita-nova", "/admin/produtos/receitas/nova"],
  ["gigio", "/admin/produtos/gigio"],
  ["harmonizacoes", "/admin/produtos/gigio/harmonizacoes"],
  ["complementos", "/admin/produtos/complementos"],
  ["agenda", "/admin/agenda"],
  ["fidelidade", "/admin/fidelidade"],
];

const measures = {};
const rows = [];

function record(file, measure) {
  measures[file] = measure;
  const left = `${measure.anchorLeft} / ${measure.contentLeft}`;
  const right = `${measure.accountRight} / ${measure.contentRight}`;
  const wrap = measure.wrapped ? "não" : "sim";
  const targets = measure.short.length || measure.playfair.length || measure.clipped.length
    ? [...measure.short, ...measure.playfair, ...measure.clipped].join("; ")
    : "ok";
  const scroll = measure.scroll ? `não (${measure.scrollWidth}>${measure.innerWidth})` : "sim";
  const note = measure.problems.length
    ? measure.problems.join("; ")
    : "casca OK; miolo: ver inventário";
  rows.push(`| ${file} | ${left} | ${right} | ${wrap} | ${targets} | ${scroll} | ${note} |`);
  console.log(file, note);
}

async function settle(page) {
  await page.waitForNetworkIdle({ idleTime: 300, timeout: 8000 }).catch(() => {});
}

async function measure(page, width) {
  return page.evaluate((viewport) => {
    const problems = [];
    const doc = document.documentElement;
    const strip = document.querySelector("[data-scroll-x]");
    const stripBox = strip?.getBoundingClientRect();
    const stripScrolls = Boolean(strip && strip.scrollWidth > strip.clientWidth + 1);
    let scroll = doc.scrollWidth > window.innerWidth + 1;
    if (scroll && stripScrolls && stripBox && stripBox.width <= window.innerWidth + 1) {
      const outside = [...document.querySelectorAll("body *")].some((node) => {
        if (node.closest("[data-scroll-x]")) return false;
        const rect = node.getBoundingClientRect();
        return rect.width > 1 && rect.right > window.innerWidth + 1;
      });
      if (!outside) scroll = false;
    }
    if (scroll) {
      problems.push(`rolagem ${doc.scrollWidth}>${window.innerWidth}`);
    }
    const bar = document.querySelector(".admin-topbar");
    const pageBox = document.querySelector(".admin-frame-main > .admin-page");
    const trail = document.querySelector(".admin-trail");
    const menu = document.querySelector("button.admin-menu-button");
    const account = document.querySelector(".admin-topbar .header-access-account");
    const lead = document.querySelector(".admin-topbar-lead");
    const actions = document.querySelector(".admin-topbar-actions");
    const barBox = bar?.getBoundingClientRect();
    const content = pageBox?.getBoundingClientRect();
    const style = pageBox ? getComputedStyle(pageBox) : null;
    const contentLeft = content && style ? Math.round(content.left + parseFloat(style.paddingLeft)) : null;
    const contentRight = content && style ? Math.round(content.right - parseFloat(style.paddingRight)) : null;
    const menuBox = menu?.getBoundingClientRect();
    const menuVisible = Boolean(menuBox && menuBox.width > 1 && menuBox.height > 1);
    const anchorLeft = menuVisible
      ? Math.round(menuBox.left)
      : trail
        ? Math.round(trail.getBoundingClientRect().left)
        : null;
    const accountRight = account ? Math.round(account.getBoundingClientRect().right) : null;
    const leftDelta = anchorLeft == null || contentLeft == null ? null : anchorLeft - contentLeft;
    const rightDelta = accountRight == null || contentRight == null ? null : accountRight - contentRight;
    if (leftDelta == null || Math.abs(leftDelta) > 1) {
      problems.push(`margem esquerda ${anchorLeft}≠${contentLeft}`);
    }
    if (rightDelta == null || Math.abs(rightDelta) > 1) {
      problems.push(`margem direita ${accountRight}≠${contentRight}`);
    }
    const barHeight = barBox ? Math.round(barBox.height) : 0;
    if (barHeight < 60) {
      problems.push(`barra ${barHeight}px`);
    }
    let wrapped = false;
    if (lead && actions) {
      const a = lead.getBoundingClientRect();
      const b = actions.getBoundingClientRect();
      const amid = a.top + a.height / 2;
      const bmid = b.top + b.height / 2;
      wrapped = Math.abs(amid - bmid) > 4 || b.top >= a.bottom;
      if (wrapped) {
        problems.push("barra quebrou");
      }
    }
    const min = viewport < 960 ? 44 : 40;
    const scope = [".admin-topbar a", ".admin-topbar button"];
    if (viewport < 960) {
      scope.push(".admin-side a", ".admin-side button");
    }
    const short = [...document.querySelectorAll(scope.join(","))].filter((node) => {
      if (node.closest(".header-account-menu")) {
        return false;
      }
      const rect = node.getBoundingClientRect();
      return rect.width > 1 && rect.height > 1 && rect.height + 0.5 < min;
    }).map((node) => `${node.getAttribute("aria-label") || node.textContent?.trim() || node.className} ${Math.round(node.getBoundingClientRect().height)}`);
    if (short.length) {
      problems.push(`altura ${short.join(", ")}`);
    }
    const clipped = [];
    if (bar) {
      for (const node of bar.querySelectorAll("*")) {
        const rect = node.getBoundingClientRect();
        if (rect.width < 2 || rect.height < 2) {
          continue;
        }
        const text = node.childNodes.length === 1 && node.childNodes[0].nodeType === Node.TEXT_NODE
          ? node.textContent?.trim()
          : "";
        if (!text) {
          continue;
        }
        const css = getComputedStyle(node);
        if (node.scrollWidth > node.clientWidth + 1 && css.textOverflow !== "ellipsis") {
          clipped.push(text.slice(0, 40));
        }
      }
    }
    if (clipped.length) {
      problems.push(`cortado ${clipped.join(", ")}`);
    }
    const playfair = [];
    const roots = [bar, viewport < 960 ? document.querySelector(".admin-side") : null].filter(Boolean);
    for (const rootNode of roots) {
      for (const node of rootNode.querySelectorAll("*")) {
        if (node.closest(".admin-brand-name")) {
          continue;
        }
        const family = getComputedStyle(node).fontFamily || "";
        if (/playfair/i.test(family)) {
          playfair.push((node.textContent || "").trim().slice(0, 40) || node.className);
        }
      }
    }
    if (playfair.length) {
      problems.push(`Playfair ${[...new Set(playfair)].slice(0, 4).join(", ")}`);
    }
    const blocks = [...document.querySelectorAll(".admin-frame-main > .admin-page > *")]
      .filter((node) => node.getBoundingClientRect().width > 1)
      .slice(0, 6)
      .map((node) => {
        const rect = node.getBoundingClientRect();
        const label = (node.getAttribute("aria-label") || node.querySelector("h1,h2")?.textContent || node.className || node.tagName)
          .toString()
          .trim()
          .slice(0, 40);
        return { label, left: Math.round(rect.left), right: Math.round(rect.right) };
      });
    const queue = document.querySelector(".admin-queue");
    const queueProblems = [];
    if (queue && contentLeft != null && contentRight != null) {
      const title = queue.querySelector("h1");
      const lenses = queue.querySelector(".queue-lenses");
      const filters = queue.querySelector(".queue-filters, .queue-filters-toggle");
      const table = queue.querySelector(".queue-table");
      const cards = queue.querySelector(".queue-cards");
      const refresh = queue.querySelector("[data-queue='refresh']");
      const edges = [
        ["título", title],
        ["lentes", lenses],
        ["filtros", filters],
        ["tabela", table],
        ["cartões", cards?.querySelector(".queue-card") || cards],
      ];
      for (const [name, node] of edges) {
        if (!node || node.getBoundingClientRect().width < 2) continue;
        const left = Math.round(node.getBoundingClientRect().left);
        if (Math.abs(left - contentLeft) > 1) queueProblems.push(`${name} esquerda ${left}≠${contentLeft}`);
      }
      for (const [name, node] of [
        ["Atualizar", refresh],
        ["tabela", table],
        ["cartões", cards],
      ]) {
        if (!node || node.getBoundingClientRect().width < 2) continue;
        const right = Math.round(node.getBoundingClientRect().right);
        if (Math.abs(right - contentRight) > 1) queueProblems.push(`${name} direita ${right}≠${contentRight}`);
      }
      const min = viewport < 960 ? 44 : 40;
      for (const node of queue.querySelectorAll(".queue-lens, .queue-filters input, .queue-filters select, .queue-filters .admin-btn, .queue-filters-toggle, [data-queue='refresh'], .queue-foot .admin-btn, .queue-card .admin-btn, .queue-action .admin-btn")) {
        const rect = node.getBoundingClientRect();
        if (rect.width < 2 || rect.height < 2) continue;
        if (rect.height + 0.5 < min) {
          queueProblems.push(`controle ${Math.round(rect.height)}px ${node.getAttribute("aria-label") || node.textContent?.trim().slice(0, 24)}`);
        }
      }
      for (const node of queue.querySelectorAll(".admin-chip, .admin-btn, .queue-lens")) {
        const rect = node.getBoundingClientRect();
        if (rect.width < 2 || rect.height < 2) continue;
        const text = (node.getAttribute("aria-label") || node.textContent || "").trim().slice(0, 32);
        if (node.getClientRects().length > 1) queueProblems.push(`quebra ${text}`);
        if (node.scrollWidth > node.clientWidth + 1) queueProblems.push(`cortado ${text}`);
      }
      if (table && table.scrollWidth > table.clientWidth + 1) {
        queueProblems.push(`tabela rola ${table.scrollWidth}>${table.clientWidth}`);
      }
      const queuePlayfair = [];
      for (const node of queue.querySelectorAll("*")) {
        if (/playfair/i.test(getComputedStyle(node).fontFamily || "")) {
          queuePlayfair.push((node.textContent || "").trim().slice(0, 24) || node.className);
        }
      }
      if (queuePlayfair.length) queueProblems.push(`Playfair na fila ${[...new Set(queuePlayfair)].slice(0, 3).join(", ")}`);
    }
    if (location.pathname === "/admin/pedidos" || location.pathname === "/admin") {
      problems.push(...queueProblems);
    }
    return {
      scroll,
      scrollWidth: doc.scrollWidth,
      innerWidth: window.innerWidth,
      barHeight,
      anchorLeft,
      contentLeft,
      accountRight,
      contentRight,
      leftDelta,
      rightDelta,
      wrapped,
      short,
      clipped,
      playfair: [...new Set(playfair)].slice(0, 8),
      problems,
      blocks,
      queueProblems,
    };
  }, width);
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ["--no-first-run", "--disable-extensions"],
});
const page = await browser.newPage();

try {
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(`${origin}/#acesso`, { waitUntil: "domcontentloaded" });
  await settle(page);
  const enter = await page.waitForSelector("button.header-access-local-enter", { timeout: 8000 });
  await enter.click();
  await page.waitForFunction(() => location.pathname.startsWith("/admin"), { timeout: 8000 });
  await settle(page);

  const recipeHref = await page.evaluate(async () => {
    const response = await fetch("/api/v1/admin/week-recipes", { credentials: "include" });
    if (!response.ok) {
      return null;
    }
    const body = await response.json();
    const first = body.items?.[0] || body.results?.[0];
    return first?.id ? `/admin/produtos/receitas/${first.id}` : null;
  });
  if (recipeHref) {
    routes.splice(9, 0, ["receita", recipeHref]);
  }

  for (const [name, path] of routes) {
    await page.goto(`${origin}${path}`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".admin-topbar", { timeout: 8000 });
    await settle(page);
    for (const width of widths) {
      await page.setViewport({ width, height: width < 960 ? 844 : 800 });
      await settle(page);
      const file = `${name}-${width}.png`;
      await page.screenshot({ path: join(outDir, file), fullPage: false });
      record(file, await measure(page, width));
    }
  }

  for (const width of [320, 390]) {
    await page.setViewport({ width, height: 844 });
    await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
    await settle(page);
    await page.click("button.admin-menu-button");
    await page.waitForFunction(
      () => document.querySelector("button.admin-menu-button")?.getAttribute("aria-expanded") === "true",
    );
    const file = `gaveta-${width}.png`;
    await page.screenshot({ path: join(outDir, file), fullPage: false });
    const result = await measure(page, width);
    const drawer = await page.evaluate(() => {
      const side = document.querySelector(".admin-side");
      if (!side) return { problems: ["gaveta ausente"] };
      const box = side.getBoundingClientRect();
      const texts = [...side.querySelectorAll(".ng, .nl")].map((node) => {
        const range = document.createRange();
        range.selectNodeContents(node);
        return Math.round(range.getBoundingClientRect().left);
      });
      const problems = [];
      if (new Set(texts).size > 1) problems.push(`textos da gaveta em ${[...new Set(texts)].join(", ")}`);
      const item = side.querySelector(".nl");
      if (item) {
        const rect = item.getBoundingClientRect();
        const left = Math.round(rect.left - box.left);
        const right = Math.round(box.right - rect.right);
        if (Math.abs(left - 16) > 1 || Math.abs(right - 16) > 1) {
          problems.push(`destaque ${left}px / ${right}px, esperado 16`);
        }
      }
      return { problems };
    });
    result.problems.push(...drawer.problems);
    const store = await page.$(".admin-drawer-store");
    const close = await page.$(".admin-drawer-close");
    if (!store) {
      result.problems.push("Ver a loja ausente na gaveta");
    }
    if (!close) {
      result.problems.push("X ausente na gaveta");
    }
    record(file, result);
    await page.keyboard.press("Escape");
  }

  for (const width of [390, 1280]) {
    await page.setViewport({ width, height: width < 960 ? 844 : 800 });
    await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
    await settle(page);
    await page.click("button.admin-notices-toggle");
    await page.waitForSelector("#admin-notices-panel", { timeout: 8000 });
    const file = `avisos-${width}.png`;
    await page.screenshot({ path: join(outDir, file), fullPage: false });
    record(file, await measure(page, width));
    await page.keyboard.press("Escape");
  }

  await page.setViewport({ width: 390, height: 844 });
  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await settle(page);
  await page.focus("button.admin-menu-button");
  await page.screenshot({ path: join(outDir, "foco-menu-390.png"), fullPage: false });
  record("foco-menu-390.png", await measure(page, 390));

  await page.click("button.admin-menu-button");
  await page.waitForSelector(".admin-drawer-close");
  await page.focus(".admin-drawer-close");
  await page.screenshot({ path: join(outDir, "foco-x-390.png"), fullPage: false });
  record("foco-x-390.png", await measure(page, 390));
  await page.keyboard.press("Escape");

  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await settle(page);
  await page.focus(".admin-side-nav a.nl");
  await page.screenshot({ path: join(outDir, "foco-link-1280.png"), fullPage: false });
  record("foco-link-1280.png", await measure(page, 1280));

  async function shotQueue(file, width, prepare) {
    await page.setViewport({ width, height: width < 960 ? 844 : 900 });
    if (prepare) await prepare();
    await settle(page);
    await page.screenshot({ path: join(outDir, file), fullPage: false });
    record(file, await measure(page, width));
  }

  for (const width of widths) {
    await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector(".queue-lens", { timeout: 8000 });
    await settle(page);
    await shotQueue(`pedidos-vigentes-${width}.png`, width, async () => {
      await page.evaluate(() => {
        const button = [...document.querySelectorAll(".queue-lens")].find((node) => node.textContent?.startsWith("Vigentes"));
        button?.click();
      });
    });
    await shotQueue(`pedidos-acao-${width}.png`, width, async () => {
      await page.evaluate(() => {
        const button = [...document.querySelectorAll(".queue-lens")].find((node) => node.textContent?.startsWith("Precisa de ação"));
        button?.click();
      });
      await settle(page);
    });
    await shotQueue(`pedidos-cancelados-${width}.png`, width, async () => {
      await page.evaluate(() => {
        const button = [...document.querySelectorAll(".queue-lens")].find((node) => node.textContent?.startsWith("Cancelados"));
        button?.click();
      });
      await settle(page);
    });
  }

  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".queue-lens");
  await settle(page);
  await page.focus(".queue-lens");
  await page.screenshot({ path: join(outDir, "foco-lente-1280.png"), fullPage: false });
  record("foco-lente-1280.png", await measure(page, 1280));
  const step = await page.$(".queue-action .admin-btn, .queue-card .admin-btn");
  if (step) {
    await step.focus();
    await page.screenshot({ path: join(outDir, "foco-passo-1280.png"), fullPage: false });
    record("foco-passo-1280.png", await measure(page, 1280));
  }

  async function withOrders(mode, file, width) {
    await page.setRequestInterception(true);
    const handler = (request) => {
      const url = request.url();
      const list = url.includes("/api/v1/admin/orders?") || url.endsWith("/api/v1/admin/orders");
      if (!list) {
        request.continue();
        return;
      }
      if (mode === "empty") {
        request.respond({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            items: [],
            total: 0,
            page: 1,
            page_size: 20,
            orders_error: null,
            date_requests_error: null,
            filter_label: null,
          }),
        });
        return;
      }
      if (mode === "error") {
        request.respond({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "falha de exemplo da captura" }) });
        return;
      }
      return;
    };
    page.on("request", handler);
    try {
      await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
      await page.waitForSelector(".admin-queue", { timeout: 8000 });
      if (mode === "loading") {
        await page.waitForSelector(".queue-skel", { timeout: 8000 });
      } else {
        await settle(page);
      }
      await page.setViewport({ width, height: width < 960 ? 844 : 900 });
      await page.screenshot({ path: join(outDir, file), fullPage: false });
      record(file, await measure(page, width));
    } finally {
      page.off("request", handler);
      await page.setRequestInterception(false);
    }
  }

  for (const width of [1280, 390]) {
    await withOrders("empty", `pedidos-vazio-${width}.png`, width);
    await withOrders("error", `pedidos-erro-${width}.png`, width);
    await withOrders("loading", `pedidos-carregando-${width}.png`, width);
  }

  await page.setViewport({ width: 390, height: 844 });
  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".queue-filters-toggle", { timeout: 8000 });
  await settle(page);
  await page.click(".queue-filters-toggle");
  await page.screenshot({ path: join(outDir, "pedidos-filtros-390.png"), fullPage: false });
  record("pedidos-filtros-390.png", await measure(page, 390));
} finally {
  await browser.close();
}

writeFileSync(join(outDir, "medidas.json"), JSON.stringify(measures, null, 2), "utf8");
const failed = rows.filter((row) => !row.includes("casca OK"));
const review = [
  "# Revisão visual — 109",
  "",
  "Medidas no Chrome, só em 127.0.0.1. A margem esquerda compara a trilha (ou o botão de menu) com o conteúdo de `.admin-page`, sem o padding. A margem direita compara o botão da conta com esse conteúdo. “sim” em barra e rolagem quer dizer que a barra ficou numa linha e a página não rolou na horizontal. A faixa de lentes com `data-scroll-x` não conta como rolagem da página. Nas rotas que não são a fila, o alinhamento de cada bloco fica em `medidas.json` e não reprova o script.",
  "",
  "| Captura | Margem esquerda (trilha ou menu / conteúdo) | Margem direita (conta / conteúdo) | Barra sem quebra | Alvos | Rolagem | Observação |",
  "|---|---|---|---|---|---|---|",
  ...rows,
  "",
  failed.length ? `Pendências da casca: ${failed.length}.` : "Nenhuma pendência da casca.",
  "",
].join("\n");
writeFileSync(join(outDir, "revisao-visual.md"), review, "utf8");
if (failed.length) {
  console.error(`casca com ${failed.length} pendência(s)`);
  process.exit(1);
}
console.log(outDir);
