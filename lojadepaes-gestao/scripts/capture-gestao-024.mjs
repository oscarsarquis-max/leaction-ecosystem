/**
 * Captura aba Rendimento (1280).
 *   GESTAO_PRODUTO=<uuid> GESTAO_SHOT=rendimento-n1-1280 GESTAO_USER=... GESTAO_PASS=... node scripts/capture-gestao-024.mjs
 */
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:5185";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-024-local";
const nome = process.env.GESTAO_SHOT ?? "rendimento-n1-1280";
const produto = process.env.GESTAO_PRODUTO ?? "";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!usuario || !senha || !produto) throw new Error("GESTAO_USER, GESTAO_PASS e GESTAO_PRODUTO");

const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);
mkdirSync(outDir, { recursive: true });
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.goto(`${base}/`, { waitUntil: "networkidle0" });
await page.waitForSelector('input[name="usuario"]');
await page.type('input[name="usuario"]', usuario);
await page.type('input[name="senha"]', senha);
await page.click('button[type="submit"]');
await page.waitForSelector(".gestao-side", { timeout: 20000 });
await page.goto(`${base}/receitas/${produto}`, { waitUntil: "networkidle0" });
await page.waitForSelector('[role="group"][aria-label="Partes da receita"]', { timeout: 20000 });
await page.evaluate(() => {
  const g = document.querySelector('[role="group"][aria-label="Partes da receita"]');
  const b = g && [...g.querySelectorAll("button")].find((x) => (x.textContent || "").trim() === "Rendimento");
  if (b) b.click();
});
await page.waitForFunction(() => /A receita faz|Peças de|Peso final/i.test(document.body.innerText), { timeout: 20000 });
await pausa(500);
const h = await page.evaluate(() => document.documentElement.scrollHeight);
await page.setViewport({ width: 1280, height: Math.max(900, Math.min(h, 2200)), deviceScaleFactor: 1 });
await page.screenshot({ path: join(outDir, `${nome}.png`) });
console.log(nome, "OK");
await browser.close();
