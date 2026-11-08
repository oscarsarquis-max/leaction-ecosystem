/**
 * Capturas do GESTAO-007B (ambiente LOCAL, banco de demonstração).
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=demo GESTAO_PASS=... \
 *   GESTAO_OUT=docs/evidence/gestao-007b-local node scripts/capture-gestao-007b.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-007b-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
const requirePkg = createRequire(
  process.env.GESTAO_PUPPETEER ?? join(process.env.TEMP ?? "/tmp", "gestao-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

const larguras = (process.env.GESTAO_LARGURAS ?? "1280,390").split(",").map(Number);
mkdirSync(outDir, { recursive: true });
const linhas = [];
let falhas = 0;
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));
const estreito = (largura) => largura < 960;

function nota(arquivo, achados) {
  const resultado = achados.length ? achados.join("; ") : "OK";
  if (achados.length) falhas += 1;
  linhas.push(`| ${arquivo} | ${resultado} |`);
  console.log(arquivo, resultado);
}

async function problemas(page, largura) {
  return page.evaluate((minimo) => {
    const achados = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > window.innerWidth + 1) achados.push(`rolagem horizontal ${doc.scrollWidth}>${window.innerWidth}`);
    if (document.body.innerText.includes("Em dia")) achados.push("selo Em dia ainda aparece");
    const curtos = [...document.querySelectorAll("button, select, input:not([type=checkbox]):not([type=radio])")].filter((no) => {
      if (no.classList.contains("selo-corrigido")) return false;
      const r = no.getBoundingClientRect();
      const estilo = getComputedStyle(no);
      if (estilo.visibility === "hidden" || estilo.display === "none") return false;
      return r.width > 1 && r.height > 1 && r.height + 0.5 < minimo;
    });
    if (curtos.length) {
      achados.push(
        `controle abaixo de ${minimo}px: ${[...new Set(curtos.map((no) => `${no.tagName.toLowerCase()}.${String(no.className).split(" ")[0]}`))].slice(0, 6).join(", ")}`,
      );
    }
    return achados;
  }, estreito(largura) ? 44 : 40);
}

async function entrar(page) {
  await page.goto(`${base}/entrar`, { waitUntil: "networkidle0" });
  const formulario = await page.$('input[name="usuario"]');
  if (formulario) {
    await page.type('input[name="usuario"]', usuario);
    await page.type('input[name="senha"]', senha);
    await page.click('button[type="submit"]');
  }
  await page.waitForSelector(".gestao-topbar", { timeout: 15000 });
  await pausa(300);
}

async function capturar(page, largura, nome) {
  const arquivo = `${nome}-${largura}.png`;
  const atual = page.viewport();
  const altura = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewport({ ...atual, height: Math.max(atual.height, altura) });
  await pausa(200);
  await page.screenshot({ path: join(outDir, arquivo) });
  await page.setViewport(atual);
  nota(arquivo, await problemas(page, largura));
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ["--font-render-hinting=none"],
});

for (const largura of larguras) {
  const page = await browser.newPage();
  await page.setViewport({ width: largura, height: estreito(largura) ? 844 : 900, deviceScaleFactor: 1 });
  await entrar(page);

  await page.goto(`${base}/ingredientes`, { waitUntil: "networkidle0" });
  await page.waitForSelector("table.lista-ingredientes");
  await page.waitForFunction(() => document.body.innerText.includes("Fubá Orgânico"));
  await pausa(200);
  await capturar(page, largura, "lista");

  await page.click('button[aria-label="Mostrar lotes de Fubá Orgânico"]');
  await page.waitForSelector("table.lotes-ing");
  await page.waitForFunction(() => document.body.innerText.includes("custo corrigido"));
  if (!estreito(largura)) {
    await page.waitForFunction(() => document.body.innerText.includes("Item / Lote"));
  }
  await pausa(250);
  await capturar(page, largura, "expandida");
  await page.close();
}

await browser.close();
writeFileSync(
  join(outDir, "capturas.md"),
  `# Capturas locais GESTAO-007B\n\n| Arquivo | Checagem |\n|---|---|\n${linhas.join("\n")}\n`,
  "utf8",
);
if (falhas) process.exitCode = 1;
