/**
 * Capturas do GESTAO-013 no ambiente local.
 * Rendimento do Pão de Canela, "ver de onde vem" e Padrões › Perdas, nas seis larguras.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-013-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
if (!usuario || !senha) throw new Error("GESTAO_USER e GESTAO_PASS");
const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

mkdirSync(outDir, { recursive: true });
const linhas = [];
let falhas = 0;
const larguras = [320, 390, 768, 960, 1280, 1440];
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));

function nota(arquivo, achados) {
  const resultado = achados.length ? achados.join("; ") : "OK";
  if (achados.length) falhas += 1;
  linhas.push(`| ${arquivo} | ${resultado} |`);
  console.log(arquivo, resultado);
}

async function problemas(page, largura) {
  const minimo = largura < 960 ? 44 : 40;
  return page.evaluate((piso) => {
    const achados = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > window.innerWidth + 1) achados.push(`rolagem horizontal ${doc.scrollWidth}>${window.innerWidth}`);
    const curtos = [...document.querySelectorAll("button, select, textarea, input:not([type=checkbox])")].filter((no) => {
      if (no.classList.contains("ing-chip-x") || no.classList.contains("linha-menu-botao") || no.classList.contains("link-acao")) return false;
      const r = no.getBoundingClientRect();
      const estilo = getComputedStyle(no);
      if (estilo.visibility === "hidden" || estilo.display === "none") return false;
      return r.width > 1 && r.height > 1 && r.height + 0.5 < piso;
    });
    if (curtos.length) achados.push(`controle abaixo de ${piso}px`);
    return achados;
  }, minimo);
}

async function capturar(page, largura, nome) {
  const arquivo = `${nome}-${largura}.png`;
  await page.setViewport({ width: largura, height: 900, deviceScaleFactor: 1 });
  await pausa(250);
  const altura = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewport({ width: largura, height: Math.max(900, Math.min(altura, 2400)), deviceScaleFactor: 1 });
  await pausa(200);
  await page.screenshot({ path: join(outDir, arquivo) });
  nota(arquivo, await problemas(page, largura));
}

async function clicar(page, texto) {
  const ok = await page.evaluate((alvo) => {
    const botao = [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === alvo);
    botao?.click();
    return Boolean(botao);
  }, texto);
  if (!ok) throw new Error(`não achei o botão ${texto}`);
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage();
let csrf = "";
page.on("response", async (res) => {
  if (res.url().includes("/auth/entrar") && res.ok()) {
    try {
      csrf = (await res.json()).csrf;
    } catch {
      /* a página também lê o corpo */
    }
  }
});
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.goto(`${base}/`, { waitUntil: "networkidle0" });
await page.waitForSelector('input[name="usuario"]');
await page.type('input[name="usuario"]', usuario);
await page.type('input[name="senha"]', senha);
await page.click('button[type="submit"]');
await page.waitForSelector(".gestao-side", { timeout: 15000 });

const preparo = await page.evaluate(async (token) => {
  const cab = { "Content-Type": "application/json", "X-CSRF-Token": token };
  const pedir = async (method, caminho, corpo) => {
    const r = await fetch(`/api/v1${caminho}`, {
      method,
      headers: cab,
      credentials: "include",
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    const json = await r.json().catch(() => ({}));
    return { status: r.status, json };
  };
  const desejados = [
    ["Farinha de trigo", "Farinhas"],
    ["Água", "Líquidos"],
  ];
  const atuais = await pedir("GET", "/ingredientes?filtro=todos");
  const porNome = new Map((atuais.json.ingredientes || []).map((i) => [i.nome, i]));
  const ids = {};
  for (const [nome, categoria] of desejados) {
    const existe = porNome.get(nome);
    if (!existe) {
      const criado = await pedir("POST", "/ingredientes", { nome, unidade_base: "g", categoria, confirmado_inexistente: true });
      ids[nome] = criado.json.id;
    } else ids[nome] = existe.id;
  }
  const produtos = await pedir("GET", "/produtos?filtro=todos");
  let canela = (produtos.json.produtos || []).find((p) => p.nome.startsWith("Pão de Canela"));
  if (!canela) {
    const criado = await pedir("POST", "/produtos", {
      nome: "Pão de Canela",
      modalidade: "produzido",
      uso_venda: true,
      uso_componente: false,
      unidade_venda: "un",
    });
    canela = criado.json;
  }
  const receita = await pedir("PUT", `/receitas/${canela.id}`, {
    linhas: [
      { ingrediente_id: ids["Farinha de trigo"], quantidade: 1000, unidade: "g", funcao: "massa" },
      { ingrediente_id: ids["Água"], quantidade: 400, unidade: "g", funcao: "massa" },
    ],
    rendimento_quantidade: 1,
    rendimento_unidade: "un",
    peso_unidade_g: 500,
    perda_percentual: 0,
    modo_fazer: [],
    formato: "forma_enriquecida",
    unidades_desejadas: 10,
  });
  return { canela: canela.id, status: receita.status, perdas: receita.json.perdas, erro: receita.json.detail };
}, csrf);
if (preparo.status !== 200) throw new Error(`não gravei o rendimento ${JSON.stringify(preparo)}`);

await page.goto(`${base}/receitas/${preparo.canela}`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => document.body.innerText.includes("Pão de Canela"));
await clicar(page, "Rendimento");
await page.waitForFunction(() => document.body.innerText.includes("padrão da casa") && document.body.innerText.includes("568"), { timeout: 15000 });
for (const largura of larguras) await capturar(page, largura, "rendimento");

const abriu = await page.evaluate(() => {
  const botoes = [...document.querySelectorAll("button")].filter((b) => b.textContent.trim() === "ver de onde vem");
  botoes[1]?.click();
  return botoes.length >= 2;
});
if (!abriu) throw new Error("não achei ver de onde vem");
await page.waitForFunction(() => document.body.innerText.includes("Referência:"), { timeout: 10000 });
for (const largura of larguras) await capturar(page, largura, "rendimento-origem");

await page.goto(`${base}/gestao/padroes`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => [...document.querySelectorAll("button")].some((b) => b.textContent.trim() === "Perdas"));
await clicar(page, "Perdas");
await page.waitForFunction(() => document.body.innerText.includes("informado pelo Oscar") && document.body.innerText.includes("Referência"), { timeout: 15000 });
for (const largura of larguras) await capturar(page, largura, "padroes-perdas");

writeFileSync(
  join(outDir, "capturas.md"),
  `# Capturas locais GESTAO-013\n\n| Arquivo | Checagem |\n|---|---|\n${linhas.join("\n")}\n`,
  "utf8",
);
await browser.close();
if (falhas) process.exitCode = 1;
