/**
 * Captura local GESTAO-022: painel Hoje com lote vencido (1280).
 *   GESTAO_BASE_URL=http://127.0.0.1:5185 GESTAO_USER=... GESTAO_PASS=... node scripts/capture-gestao-022.mjs
 */
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:5185";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-022-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
if (!usuario || !senha) throw new Error("GESTAO_USER e GESTAO_PASS");

const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

mkdirSync(outDir, { recursive: true });
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));

async function capturar(page, largura, nome, alturaMin = 900) {
  await page.setViewport({ width: largura, height: alturaMin, deviceScaleFactor: 1 });
  await pausa(500);
  const altura = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewport({
    width: largura,
    height: Math.max(alturaMin, Math.min(altura, 2600)),
    deviceScaleFactor: 1,
  });
  await pausa(200);
  await page.screenshot({ path: join(outDir, `${nome}.png`) });
  console.log(nome, "OK");
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.goto(`${base}/`, { waitUntil: "networkidle0" });
await page.waitForSelector('input[name="usuario"]');
await page.type('input[name="usuario"]', usuario);
await page.type('input[name="senha"]', senha);
await page.click('button[type="submit"]');
await page.waitForSelector(".gestao-side", { timeout: 20000 });
await pausa(600);

await page.goto(`${base}/`, { waitUntil: "networkidle0" });
await page.waitForFunction(
  () => /Vencido|lote vencido|Lotes vencidos/i.test(document.body.innerText),
  { timeout: 20000 },
);
await pausa(800);
await capturar(page, 1280, "hoje-lote-vencido-1280");

await browser.close();
console.log("capturas em", outDir);
