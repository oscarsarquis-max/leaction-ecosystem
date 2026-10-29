/**
 * Revisão visual da barra do 108A. Só loopback.
 * node scripts/p108a-capture-bar.mjs
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = "http://127.0.0.1:5175";
const outDir = join(root, "readme", "evidence", "prompt-108a");
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

const lines = [];

function note(file, text) {
  lines.push(`| ${file} | ${text} |`);
  console.log(file, text);
}

async function settle(page) {
  await page.waitForNetworkIdle({ idleTime: 300, timeout: 8000 }).catch(() => {});
}

async function assertShell(page, width) {
  return page.evaluate((min) => {
    const problems = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > window.innerWidth + 1) {
      problems.push(`rolagem ${doc.scrollWidth}>${window.innerWidth}`);
    }
    const bar = document.querySelector(".admin-topbar");
    const main = document.querySelector(".admin-frame-main");
    if (!bar || !main) {
      problems.push("barra ausente");
      return problems;
    }
    const box = bar.getBoundingClientRect();
    const column = main.getBoundingClientRect();
    if (Math.abs(box.width - column.width) > 2 || Math.abs(box.left - column.left) > 2) {
      problems.push(`barra ${Math.round(box.width)} em coluna ${Math.round(column.width)}`);
    }
    if (getComputedStyle(bar).borderBottomWidth !== "1px") {
      problems.push("borda inferior ausente");
    }
    const lead = bar.querySelector(".admin-topbar-lead");
    const actions = bar.querySelector(".admin-topbar-actions");
    if (lead && actions) {
      const leadBox = lead.getBoundingClientRect();
      const actionsBox = actions.getBoundingClientRect();
      const leadMid = leadBox.top + leadBox.height / 2;
      const actionsMid = actionsBox.top + actionsBox.height / 2;
      if (Math.abs(leadMid - actionsMid) > 4 || actionsBox.top >= leadBox.bottom) {
        problems.push("trilha e ações quebraram de linha");
      }
    }
    const menu = bar.querySelector("button.admin-menu-button");
    if (menu) {
      const menuBox = menu.getBoundingClientRect();
      if (menuBox.width > 1 && (Math.abs(menuBox.width - 44) > 1 || Math.abs(menuBox.height - 44) > 1)) {
        problems.push(`menu ${Math.round(menuBox.width)}x${Math.round(menuBox.height)}`);
      }
    }
    const short = [...bar.querySelectorAll("a, button"), ...document.querySelectorAll(".admin-drawer-store")].filter((node) => {
      const rect = node.getBoundingClientRect();
      return rect.width > 1 && rect.height > 1 && rect.height + 0.5 < min;
    });
    if (short.length) {
      problems.push(`altura ${short.map((node) => Math.round(node.getBoundingClientRect().height)).join(",")}`);
    }
    return problems;
  }, width < 960 ? 44 : 40);
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
    routes.splice(8, 0, ["receita", recipeHref]);
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
      const problems = await assertShell(page, width);
      if (problems.length) {
        note(file, problems.join("; "));
        throw new Error(`${file}: ${problems.join("; ")}`);
      }
      note(file, "OK");
    }
  }

  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await page.setViewport({ width: 390, height: 844 });
  await settle(page);
  await page.click("button.admin-menu-button");
  await page.waitForFunction(
    () => document.querySelector("button.admin-menu-button")?.getAttribute("aria-expanded") === "true",
  );
  await page.screenshot({ path: join(outDir, "gaveta-390.png"), fullPage: false });
  const drawerProblems = await assertShell(page, 390);
  const storeInDrawer = await page.evaluate(() => Boolean(document.querySelector(".admin-drawer-store")));
  if (!storeInDrawer) {
    drawerProblems.push("Ver a loja ausente na gaveta");
  }
  if (drawerProblems.length) {
    note("gaveta-390.png", drawerProblems.join("; "));
    throw new Error(drawerProblems.join("; "));
  }
  note("gaveta-390.png", "OK");
  await page.keyboard.press("Escape");

  for (const width of [1280, 390]) {
    await page.setViewport({ width, height: width < 960 ? 844 : 800 });
    await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
    await settle(page);
    await page.click("button.admin-notices-toggle");
    await page.waitForSelector("#admin-notices-panel", { timeout: 8000 });
    const file = `avisos-${width}.png`;
    await page.screenshot({ path: join(outDir, file), fullPage: false });
    const problems = await assertShell(page, width);
    if (problems.length) {
      note(file, problems.join("; "));
      throw new Error(`${file}: ${problems.join("; ")}`);
    }
    note(file, "OK");
    await page.click("button.admin-notices-toggle");
  }

  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await settle(page);
  await page.focus("button.admin-notices-toggle");
  await page.screenshot({ path: join(outDir, "foco-botao-1280.png"), fullPage: false });
  note("foco-botao-1280.png", "OK");
  await page.focus(".admin-side-nav a.nl");
  await page.screenshot({ path: join(outDir, "foco-link-1280.png"), fullPage: false });
  note("foco-link-1280.png", "OK");
} finally {
  await browser.close();
}

const review = [
  "# Revisão visual — 108A",
  "",
  "Checagem no Chrome: a barra ocupa a coluna de conteúdo, tem borda inferior, trilha e ações na mesma linha, e os controles da barra têm a altura mínima. A página não rolou na horizontal.",
  "",
  "| Captura | Resultado |",
  "|---|---|",
  ...lines,
  "",
].join("\n");
writeFileSync(join(outDir, "revisao-visual.md"), review, "utf8");
console.log(outDir);
