/**
 * Capturas do GESTAO-011 (ambiente LOCAL). Não grava em produção.
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=demo GESTAO_PASS=... \
 *   node scripts/capture-gestao-011.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-011-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
if (!usuario || !senha) throw new Error("GESTAO_USER e GESTAO_PASS");
const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

mkdirSync(outDir, { recursive: true });
const linhas = [];
let falhas = 0;
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));

function nota(arquivo, achados) {
  const resultado = achados.length ? achados.join("; ") : "OK";
  if (achados.length) falhas += 1;
  linhas.push(`| ${arquivo} | ${resultado} |`);
  console.log(arquivo, resultado);
}

async function problemas(page, largura, contarMinis) {
  const minimo = largura < 960 ? 44 : 40;
  return page.evaluate((piso, contar) => {
    const achados = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > window.innerWidth + 1) achados.push(`rolagem horizontal ${doc.scrollWidth}>${window.innerWidth}`);
    const curtos = [...document.querySelectorAll("button, select, input:not([type=checkbox])")].filter((no) => {
      if (no.classList.contains("ing-chip-x") || no.classList.contains("linha-menu-botao")) return false;
      const r = no.getBoundingClientRect();
      const estilo = getComputedStyle(no);
      if (estilo.visibility === "hidden" || estilo.display === "none") return false;
      return r.width > 1 && r.height > 1 && r.height + 0.5 < piso;
    });
    if (curtos.length) achados.push(`controle abaixo de ${piso}px`);
    if (contar) {
      const fotos = document.querySelectorAll(".foto-mini");
      if (fotos.length < 10) achados.push(`miniaturas ${fotos.length}`);
    }
    return achados;
  }, minimo, contarMinis);
}

async function capturar(page, largura, nome, extra, contarMinis = false) {
  const arquivo = `${nome}-${largura}.png`;
  await page.setViewport({ width: largura, height: 900, deviceScaleFactor: 1 });
  await pausa(300);
  const altura = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewport({ width: largura, height: Math.max(900, Math.min(altura, 2200)), deviceScaleFactor: 1 });
  await pausa(200);
  await page.screenshot({ path: join(outDir, arquivo) });
  nota(arquivo, [...(await problemas(page, largura, contarMinis)), ...(extra ? await extra(page) : [])]);
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.goto(`${base}/`, { waitUntil: "networkidle0" });
await page.waitForSelector('input[name="usuario"]');
await page.type('input[name="usuario"]', usuario);
await page.type('input[name="senha"]', senha);
await page.click('button[type="submit"]');
await page.waitForSelector(".gestao-side", { timeout: 15000 });
await page.goto(`${base}/produtos`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => document.body.innerText.includes("Focaccia Alta"));
await page.waitForFunction(() => {
  const imgs = [...document.querySelectorAll(".foto-mini")];
  return imgs.length >= 10 && imgs.every((img) => img.complete && img.naturalWidth > 0);
}, { timeout: 30000 });

await capturar(page, 1280, "produtos-lista", null, true);
await capturar(page, 390, "produtos-lista", null, true);

await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.evaluate(() => {
  const botao = [...document.querySelectorAll("button.ing-nome")].find((el) => el.textContent.includes("Focaccia Alta"));
  botao?.click();
});
await page.waitForSelector(".foto-quadro img", { timeout: 10000 });
await page.waitForFunction(() => {
  const img = document.querySelector(".foto-quadro img");
  return img && img.complete && img.naturalWidth > 0;
});
await page.waitForFunction(() => document.body.innerText.includes("Importado da Loja"));
const fotoOk = async (pagina) => {
  const ok = await pagina.evaluate(() => {
    const img = document.querySelector(".foto-quadro img");
    const texto = document.body.innerText.includes("Importado da Loja em");
    return img && img.naturalWidth > 0 && texto ? [] : ["foto ou data da importação ausente"];
  });
  return ok;
};
await capturar(page, 1280, "produto-painel", fotoOk);
await capturar(page, 390, "produto-painel", fotoOk);

writeFileSync(join(outDir, "capturas.md"), `# Capturas locais GESTAO-011\n\n| Arquivo | Checagem |\n|---|---|\n${linhas.join("\n")}\n`, "utf8");
await browser.close();
if (falhas) process.exitCode = 1;
