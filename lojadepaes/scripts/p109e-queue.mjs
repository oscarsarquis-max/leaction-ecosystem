/**
 * 109E (4): mede e fotografa a fila de pedidos: linha de filtros-pílula a 960 px e botão "Filtros" aberto no celular.
 * Banco de captura (:5176, scripts/p109e-capture-server.py). Só leitura.
 *   node scripts/p109e-queue.mjs [sufixo]
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = "http://127.0.0.1:5176";
const outDir = join(root, "readme", "evidence", "prompt-109e");
mkdirSync(outDir, { recursive: true });
const suffix = process.argv[2] || "";

const require = createRequire(
  process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-first-run", "--disable-extensions"] });
const page = await browser.newPage();
await page.setViewport({ width: 1440, height: 900 });
await page.goto(`${origin}/#acesso`, { waitUntil: "domcontentloaded" });
const enter = await page.waitForSelector("button.header-access-local-enter", { timeout: 8000 });
await enter.click();
await page.waitForFunction(() => location.pathname.startsWith("/admin"), { timeout: 8000 });
await sleep(800);

const report = {};

async function lensState(width) {
  return page.evaluate(() => {
    const box = document.querySelector(".queue-lenses");
    if (!box) return null;
    const boxRect = box.getBoundingClientRect();
    const pills = [...box.querySelectorAll(".queue-lens")].map((el) => {
      const r = el.getBoundingClientRect();
      return {
        text: el.textContent.replace(/\s+/g, " ").trim(),
        left: Math.round(r.left),
        right: Math.round(r.right),
        top: Math.round(r.top - boxRect.top),
        visible: r.left >= boxRect.left - 1 && r.right <= boxRect.right + 1,
      };
    });
    const rows = new Set(pills.map((p) => p.top)).size;
    return {
      clientWidth: box.clientWidth,
      scrollWidth: box.scrollWidth,
      overflows: box.scrollWidth > box.clientWidth + 1,
      rows,
      hidden: pills.filter((p) => !p.visible).map((p) => p.text),
      pills: pills.map((p) => p.text),
    };
  });
}

for (const width of [960, 1100, 1280, 1440, 390]) {
  await page.setViewport({ width, height: 900 });
  await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(".queue-lenses", { timeout: 10000 });
  await sleep(1200);
  for (const segment of ["Em andamento", "Histórico"]) {
    await page.evaluate((name) => {
      const seg = [...document.querySelectorAll(".queue-segment")].find((b) => b.textContent.includes(name));
      seg?.click();
    }, segment);
    await sleep(700);
    const state = await lensState(width);
    report[`${width}-${segment}`] = state;
    console.log(width, segment, JSON.stringify({ ...state, pills: undefined }));
    if (width === 960 && segment === "Em andamento") {
      const box = await page.$(".queue-lens-block");
      if (box) await box.screenshot({ path: join(outDir, `fila-filtros-960${suffix}.png`) });
    }
  }
}

// Botão "Filtros" aberto no celular: fundo muda?
await page.setViewport({ width: 390, height: 900 });
await page.goto(`${origin}/admin/pedidos`, { waitUntil: "domcontentloaded" });
await page.waitForSelector(".queue-filters-toggle", { timeout: 10000 });
await sleep(1000);
const toggleState = async () =>
  page.evaluate(() => {
    const t = document.querySelector(".queue-filters-toggle");
    const s = getComputedStyle(t);
    return { expanded: t.getAttribute("aria-expanded"), bg: s.backgroundColor, color: s.color, border: s.borderColor, cls: t.className };
  });
report.filtrosFechado = await toggleState();
await page.evaluate(() => document.querySelector(".queue-filters-toggle").click());
await sleep(500);
report.filtrosAberto = await toggleState();
console.log("Filtros fechado", JSON.stringify(report.filtrosFechado));
console.log("Filtros aberto", JSON.stringify(report.filtrosAberto));
const filtersBox = await page.$(".queue-filters-toggle");
await page.evaluate(() => document.querySelector(".queue-filters-toggle").scrollIntoView({ block: "center" }));
await page.screenshot({ path: join(outDir, `fila-filtros-aberto-390${suffix}.png`), fullPage: false });
void filtersBox;

writeFileSync(join(outDir, `fila-medidas${suffix}.json`), JSON.stringify(report, null, 2), "utf8");
await browser.close();
