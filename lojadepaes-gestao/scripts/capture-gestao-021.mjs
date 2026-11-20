/**
 * Capturas locais GESTAO-021: /gestao/custos em 1280 e 390 + painel de produto.
 *   GESTAO_BASE_URL=http://127.0.0.1:5185 GESTAO_USER=... GESTAO_PASS=... node scripts/capture-gestao-021.mjs
 */
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:5185";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-021-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
if (!usuario || !senha) throw new Error("GESTAO_USER e GESTAO_PASS");

const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

mkdirSync(outDir, { recursive: true });
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));

async function capturar(page, largura, nome, alturaMin = 900) {
  await page.setViewport({ width: largura, height: alturaMin, deviceScaleFactor: 1 });
  await pausa(400);
  const altura = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewport({
    width: largura,
    height: Math.max(alturaMin, Math.min(altura, 2200)),
    deviceScaleFactor: 1,
  });
  await pausa(200);
  await page.screenshot({ path: join(outDir, `${nome}.png`) });
  console.log(nome, "OK");
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage();
let csrf = "";
page.on("response", async (res) => {
  if (res.url().includes("/auth/entrar") && res.ok()) {
    try {
      csrf = (await res.json()).csrf;
    } catch {
      /* ignore */
    }
  }
});
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.goto(`${base}/`, { waitUntil: "networkidle0" });
await page.waitForSelector('input[name="usuario"]');
await page.type('input[name="usuario"]', usuario);
await page.type('input[name="senha"]', senha);
await page.click('button[type="submit"]');
await page.waitForSelector(".gestao-side", { timeout: 20000 });
await pausa(500);
if (!csrf) {
  const eu = await page.evaluate(async () => {
    const r = await fetch("/api/v1/auth/eu", { credentials: "include" });
    return { status: r.status, json: await r.json().catch(() => ({})) };
  });
  csrf = eu.json?.csrf || "";
}
if (!csrf) throw new Error("csrf vazio após login");

await page.goto(`${base}/gestao/custos`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => !/Não foi possível carregar|Carregando/.test(document.body.innerText), {
  timeout: 20000,
});
await page.waitForSelector("button.custos-produto, .custos-fixos, .hoje-tabela", { timeout: 15000 });
await pausa(600);
await capturar(page, 1280, "custos-1280");
await capturar(page, 390, "custos-390", 800);

await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.goto(`${base}/gestao/custos`, { waitUntil: "networkidle0" });
await page.waitForSelector("button.custos-produto", { timeout: 15000 });
await page.click("button.custos-produto");
await page.waitForSelector(".painel-fatos.custos-fatos", { timeout: 10000 });
await pausa(500);
await capturar(page, 1280, "painel-produto-1280");

await browser.close();
console.log("capturas em", outDir);
