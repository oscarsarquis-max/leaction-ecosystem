/**
 * 109E (1b): captura o formulário "Precisa de outra data?" a 390 px, com data vendável e com data fechada.
 * Banco de captura + Hub simulado (scripts/p109e-capture-server.py em :5176). Não envia nada.
 *   node scripts/p109e-form.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const origin = "http://127.0.0.1:5176";
const outDir = join(root, "readme", "evidence", "prompt-109e");
mkdirSync(outDir, { recursive: true });

const require = createRequire(
  process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Dias do calendário de captura: quarta é dia de produção aberto; quinta é fechada.
function nextIso(weekday) {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  while (d.getDay() !== weekday) d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}
const sellable = nextIso(3);
const closed = nextIso(4);

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-first-run", "--disable-extensions"] });
const page = await browser.newPage();
await page.setViewport({ width: 390, height: 900 });
const report = {};

async function setDate(value) {
  await page.evaluate((v) => {
    const input = document.querySelector(".bake-calendar-request input[type=date]");
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(input, v);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }, value);
  await sleep(1200);
}

async function snapshot(name, date) {
  await page.goto(`${origin}/#paes`, { waitUntil: "networkidle2" });
  await page.waitForSelector(".bake-calendar-request form", { timeout: 15000 });
  await setDate(date);
  const form = await page.$(".bake-calendar-request");
  await form.evaluate((el) => el.scrollIntoView({ block: "start" }));
  await sleep(300);
  const state = await page.evaluate(() => {
    const box = document.querySelector(".bake-calendar-request");
    const buttons = [...box.querySelectorAll("button")].map((b) => b.textContent.trim());
    return {
      mensagemDisponivel: box.innerText.includes("Esta data está disponível. Finalize o pedido pelo carrinho."),
      botoes: buttons,
      rolagemLateral: document.documentElement.scrollWidth > window.innerWidth + 1,
    };
  });
  report[name] = { data: date, ...state };
  await form.screenshot({ path: join(outDir, `${name}-390.png`) });
  console.log(name, JSON.stringify(report[name]));
}

await snapshot("formulario-data-vendavel", sellable);
await snapshot("formulario-data-fechada", closed);
await browser.close();
writeFileSync(join(outDir, "formulario-medidas.json"), JSON.stringify(report, null, 2), "utf8");
