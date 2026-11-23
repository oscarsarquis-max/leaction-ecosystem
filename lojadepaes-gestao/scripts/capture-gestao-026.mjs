/**
 * Captura local GESTAO-026: campo Ingrediente da receita com "nuvola".
 *   GESTAO_PRODUTO=<uuid> GESTAO_USER=... GESTAO_PASS=... node scripts/capture-gestao-026.mjs
 */
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:5185";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const produto = process.env.GESTAO_PRODUTO ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-026-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
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
await page.waitForFunction(() => /Receita|Ingrediente|linhas/i.test(document.body.innerText), { timeout: 20000 });
await pausa(500);

// abre / foca o campo de busca de ingrediente
const campo = await page.evaluateHandle(() => {
  const inputs = [...document.querySelectorAll("input")];
  return (
    inputs.find((i) => /ingrediente|buscar|nome/i.test(i.getAttribute("placeholder") || "")) ||
    inputs.find((i) => /ingrediente/i.test(i.getAttribute("aria-label") || "")) ||
    inputs.find((i) => i.offsetParent !== null && i.type === "search") ||
    inputs.find((i) => i.offsetParent !== null && !i.name)
  );
});
if (!campo.asElement()) throw new Error("campo de ingrediente não achado");
await campo.asElement().click({ clickCount: 3 });
await page.keyboard.type("nuvola", { delay: 40 });
await pausa(800);
await page.waitForFunction(() => /Farinha de trigo tipo 0|Nuvola|também chamado/i.test(document.body.innerText), {
  timeout: 10000,
});
await pausa(400);
await page.screenshot({ path: join(outDir, "busca-nuvola-receita-1280.png") });
console.log("busca-nuvola-receita-1280 OK");
await browser.close();
