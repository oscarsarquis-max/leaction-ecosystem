/**
 * Capturas locais GESTAO-019: Produtos (1280/390) e editor em rascunho (1280).
 *   GESTAO_BASE_URL=http://127.0.0.1:5185 GESTAO_USER=demo GESTAO_PASS=... node scripts/capture-gestao-019.mjs
 */
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:5185";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-019-local";
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
if (!csrf) throw new Error("csrf vazio após login");

async function pedir(method, caminho, corpo) {
  return page.evaluate(
    async (method, caminho, corpo, token) => {
      const r = await fetch(`/api/v1${caminho}`, {
        method,
        headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
        credentials: "include",
        body: corpo ? JSON.stringify(corpo) : undefined,
      });
      return { status: r.status, json: await r.json().catch(() => ({})) };
    },
    method,
    caminho,
    corpo,
    csrf,
  );
}

async function produto(nome, extra = {}) {
  const r = await pedir("POST", "/produtos", {
    nome,
    modalidade: "produzido",
    uso_venda: true,
    uso_componente: false,
    unidade_venda: "un",
    confirmado_inexistente: true,
    ...extra,
  });
  if (r.status !== 201) throw new Error(`produto ${nome}: ${r.status} ${JSON.stringify(r.json)}`);
  return r.json;
}

const farinha = await pedir("POST", "/ingredientes", {
  nome: "Farinha de trigo captura",
  unidade_base: "g",
  categoria: "Farinhas",
  confirmado_inexistente: true,
});
if (farinha.status !== 201) {
  console.log("farinha", farinha.status, JSON.stringify(farinha.json).slice(0, 400));
  throw new Error("sem farinha");
}
const farinhaId = farinha.json.id;

const pub = await produto("Pão publicado captura");
await pedir("PUT", `/receitas/${pub.id}`, {
  linhas: [{ ingrediente_id: farinhaId, quantidade: 500, unidade: "g" }],
  rendimento_quantidade: 1,
  rendimento_unidade: "un",
  perda_percentual: 0,
  modo_fazer: [],
});
await pedir("POST", `/receitas/${pub.id}/publicar`, { confirmar_sem_fermento: true });

const rasc = await produto("Pão rascunho captura");
await pedir("PUT", `/receitas/${rasc.id}`, {
  linhas: [{ ingrediente_id: farinhaId, quantidade: 400, unidade: "g" }],
  rendimento_quantidade: 1,
  rendimento_unidade: "un",
  perda_percentual: 0,
  modo_fazer: [],
});

await produto("Pão sem linhas captura");

await page.goto(`${base}/produtos`, { waitUntil: "networkidle0" });
await page.waitForSelector("table, .lista-produtos, .produtos", { timeout: 15000 }).catch(() => {});
await pausa(800);
await capturar(page, 1280, "produtos-1280");
await capturar(page, 390, "produtos-390", 844);

await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.goto(`${base}/receitas/${rasc.id}`, { waitUntil: "networkidle0" });
await pausa(1000);
await capturar(page, 1280, "editor-rascunho-1280");

await browser.close();
console.log("capturas em", outDir);
