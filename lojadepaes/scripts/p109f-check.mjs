/**
 * Captura e mede as telas do 109F no banco de captura (dados de exemplo). SÃ³ loopback.
 * node scripts/p109f-check.mjs   (precisa de scripts/p109f-seed-capture.py antes)
 * NÃ£o aciona o encerramento: sÃ³ fotografa a tela da solicitaÃ§Ã£o e a fila.
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = "http://127.0.0.1:5175";
const outDir = join(root, "readme", "evidence", "prompt-109f");
mkdirSync(outDir, { recursive: true });
const ids = JSON.parse(readFileSync(join(outDir, "capture-ids.json"), "utf8"));

const require = createRequire(
  process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const widths = [390, 1440];
const measures = {};
const rows = [];

async function settle(page) {
  await page.waitForNetworkIdle({ idleTime: 300, timeout: 8000 }).catch(() => {});
}

async function measure(page, width, scopeSelector) {
  return page.evaluate(
    (viewport, scopeSel) => {
      const problems = [];
      const doc = document.documentElement;
      const scroll = doc.scrollWidth > window.innerWidth + 1;
      if (scroll) problems.push(`rolagem ${doc.scrollWidth}>${window.innerWidth}`);
      const scope = document.querySelector(scopeSel) || document.querySelector("main") || document.body;
      const min = viewport < 960 ? 44 : 40;
      const controls = [...scope.querySelectorAll("input:not([type=checkbox]):not([type=radio]), select, textarea, button")].filter(
        (n) => {
          const r = n.getBoundingClientRect();
          return r.width > 1 && r.height > 1;
        },
      );
      const short = controls
        .filter((n) => n.getBoundingClientRect().height + 0.5 < min)
        .map((n) => `${(n.textContent || n.getAttribute("aria-label") || n.tagName).trim().slice(0, 28)} ${Math.round(n.getBoundingClientRect().height)}`);
      if (short.length) problems.push(`altura ${short.join(", ")}`);
      const overlaps = [];
      for (let i = 0; i < controls.length; i += 1) {
        for (let j = i + 1; j < controls.length; j += 1) {
          const a = controls[i].getBoundingClientRect();
          const b = controls[j].getBoundingClientRect();
          const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
          const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
          if (w > 1 && h > 1 && !controls[i].contains(controls[j]) && !controls[j].contains(controls[i])) {
            overlaps.push(`${(controls[i].textContent || "").trim().slice(0, 16)} Ã— ${(controls[j].textContent || "").trim().slice(0, 16)}`);
          }
        }
      }
      if (overlaps.length) problems.push(`sobreposiÃ§Ã£o ${overlaps.slice(0, 3).join("; ")}`);
      const outside = [];
      for (const n of scope.querySelectorAll("button, input, select, textarea, label, p, h1, h2")) {
        const r = n.getBoundingClientRect();
        if (!n.closest(".queue-lenses") && r.width > 1 && (r.right > window.innerWidth + 1 || r.left < -1)) {
          outside.push((n.textContent || n.tagName).trim().slice(0, 20));
        }
      }
      if (outside.length) problems.push(`fora da tela ${outside.slice(0, 3).join(", ")}`);
      const buttons = controls.map((n) => ({
        text: (n.textContent || "").trim().slice(0, 48),
        cls: n.className,
        h: Math.round(n.getBoundingClientRect().height),
      }));
      return { scroll, scrollWidth: doc.scrollWidth, innerWidth: window.innerWidth, controls: controls.length, buttons, problems };
    },
    width,
    scopeSelector,
  );
}

function record(file, m) {
  measures[file] = m;
  const note = m.problems.length ? m.problems.join("; ") : "ok";
  rows.push(`| ${file} | ${m.controls} | ${m.scroll ? `sim (${m.scrollWidth}>${m.innerWidth})` : "nÃ£o"} | ${note} |`);
  console.log(file, note);
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-first-run", "--disable-extensions"] });
const page = await browser.newPage();

async function shot(name, width, scope) {
  await page.setViewport({ width, height: width < 960 ? 900 : 1000 });
  await settle(page);
  const file = `${name}-${width}.png`;
  await page.screenshot({ path: join(outDir, file), fullPage: true });
  record(file, await measure(page, width, scope));
}

function ref(id) {
  return `SD${id.replace(/-/g, "").slice(0, 8).toUpperCase()}`;
}

async function searchQueue(page, text) {
  await page.evaluate(() => {
    const toggle = document.querySelector(".queue-filters-toggle");
    if (toggle && toggle.getAttribute("aria-expanded") === "false") toggle.click();
  });
  await new Promise((r) => setTimeout(r, 200));
  const input = await page.waitForSelector(".queue-f-search input");
  await input.click({ clickCount: 3 });
  await input.type(text);
  await page.keyboard.press("Enter");
  await settle(page);
  await new Promise((r) => setTimeout(r, 600));
}
async function open(path, width) {
  await page.setViewport({ width, height: width < 960 ? 900 : 1000 });
  await page.goto(`${origin}${path}`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".admin-topbar", { timeout: 8000 });
  await settle(page);
  await new Promise((r) => setTimeout(r, 500));
}

try {
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto(`${origin}/#acesso`, { waitUntil: "domcontentloaded" });
  await settle(page);
  const enter = await page.waitForSelector("button.header-access-local-enter", { timeout: 8000 });
  await enter.click();
  await page.waitForFunction(() => location.pathname.startsWith("/admin"), { timeout: 8000 });
  await settle(page);

  for (const width of widths) {
    await open(`/admin/pedidos/solicitacao/${ids.date_request_mesma}`, width);
    await shot("solicitacao-mesma-data", width, ".admin-warning");
    await open(`/admin/pedidos/solicitacao/${ids.date_request_outra}`, width);
    await shot("solicitacao-data-diferente", width, ".admin-warning");
    await open("/admin/pedidos", width);
    await searchQueue(page, ref(ids.date_request_mesma));
    await shot("fila-solicitacao-atendida", width, "main");
    await open("/admin/pedidos", width);
    await searchQueue(page, ref(ids.date_request_outra));
    await shot("fila-solicitacao-data-diferente", width, "main");
  }
} finally {
  await browser.close();
}

writeFileSync(join(outDir, "medidas.json"), JSON.stringify(measures, null, 2));
writeFileSync(
  join(outDir, "revisao-visual.md"),
  ["| arquivo | controles | rolagem horizontal | achados |", "|---|---|---|---|", ...rows, ""].join("\n"),
);
