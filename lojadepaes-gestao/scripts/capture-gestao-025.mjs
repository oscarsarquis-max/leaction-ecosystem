/**
 * Capturas locais GESTAO-025: painel com Excluir e confirmação (1280).
 *   GESTAO_BASE_URL=http://127.0.0.1:5185 GESTAO_USER=... GESTAO_PASS=... node scripts/capture-gestao-025.mjs
 */
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:5185";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-025-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const nome = process.env.GESTAO_INGREDIENTE ?? "Farinha de Trigo Especial Nuvola";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
if (!usuario || !senha) throw new Error("GESTAO_USER e GESTAO_PASS");

const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

mkdirSync(outDir, { recursive: true });
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));

async function capturar(page, largura, arquivo, alturaMin = 900) {
  await page.setViewport({ width: largura, height: alturaMin, deviceScaleFactor: 1 });
  await pausa(400);
  const altura = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewport({
    width: largura,
    height: Math.max(alturaMin, Math.min(altura, 2600)),
    deviceScaleFactor: 1,
  });
  await pausa(200);
  await page.screenshot({ path: join(outDir, `${arquivo}.png`) });
  console.log(arquivo, "OK");
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
await pausa(500);

await page.goto(`${base}/ingredientes`, { waitUntil: "networkidle0" });
await page.waitForFunction((n) => document.body.innerText.includes(n), { timeout: 20000 }, nome);
await pausa(400);

const botao = await page.evaluateHandle((n) => {
  const botoes = [...document.querySelectorAll("button")];
  return botoes.find((b) => b.textContent && b.textContent.trim().startsWith(n)) || null;
}, nome);
if (!botao.asElement()) throw new Error(`não achou ${nome}`);
await botao.asElement().click();
await page.waitForFunction((n) => [...document.querySelectorAll("[role=dialog]")].some((d) => d.getAttribute("aria-label") === n || d.textContent?.includes("Excluir")), { timeout: 15000 }, nome);
await pausa(500);
await capturar(page, 1280, "excluir-painel-1280");

const excluir = await page.evaluateHandle(() => {
  const dialogs = [...document.querySelectorAll("[role=dialog]")];
  const painel = dialogs[dialogs.length - 1];
  return [...painel.querySelectorAll("button")].find((b) => b.textContent?.trim() === "Excluir") || null;
});
if (!excluir.asElement()) throw new Error("botão Excluir sumiu");
await excluir.asElement().click();
await page.waitForFunction(() => [...document.querySelectorAll("[role=dialog]")].some((d) => /Excluir ingrediente/i.test(d.getAttribute("aria-label") || d.textContent || "")), { timeout: 10000 });
await pausa(400);
await capturar(page, 1280, "excluir-confirma-1280");

await browser.close();
console.log("capturas em", outDir);
