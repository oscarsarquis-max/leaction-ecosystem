/**
 * Captura e mede a casca do 108B. Só loopback.
 * node scripts/p108b-check-shell.mjs
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = "http://127.0.0.1:5175";
const outDir = join(root, "readme", "evidence", "prompt-108b");
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
    const scroll = doc.scrollWidth > window.innerWidth + 1;
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
} finally {
  await browser.close();
}

writeFileSync(join(outDir, "medidas.json"), JSON.stringify(measures, null, 2), "utf8");
const failed = rows.filter((row) => !row.includes("casca OK"));
const review = [
  "# Revisão visual — 108B",
  "",
  "Medidas da casca no Chrome. A margem esquerda compara a trilha (ou o botão de menu) com o conteúdo de `.admin-page`, sem o padding. A margem direita compara o botão da conta com esse conteúdo. “sim” em barra e rolagem quer dizer que a barra ficou numa linha e a página não rolou na horizontal.",
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
