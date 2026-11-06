/**
 * Capturas do GESTAO-012 no ambiente local, com o gateway falso.
 * Não grava em produção.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-012-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const larguras = [320, 390, 768, 960, 1280, 1440];
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

async function problemas(page, largura) {
  const minimo = largura < 960 ? 44 : 40;
  return page.evaluate((piso) => {
    const achados = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > window.innerWidth + 1) achados.push(`rolagem horizontal ${doc.scrollWidth}>${window.innerWidth}`);
    const curtos = [...document.querySelectorAll("button, select, textarea, input:not([type=checkbox])")].filter((no) => {
      if (no.classList.contains("ing-chip-x") || no.classList.contains("linha-menu-botao")) return false;
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
  const pedir = (method, caminho, corpo) =>
    fetch(`/api/v1${caminho}`, { method, headers: cab, credentials: "include", body: corpo ? JSON.stringify(corpo) : undefined }).then((r) => r.json());
  const lista = await pedir("GET", "/produtos?filtro=todos");
  const nomes = new Set((lista.produtos || []).map((p) => p.nome));
  async function ingrediente(nome, categoria) {
    const atuais = await pedir("GET", "/ingredientes?filtro=todos");
    if ((atuais.ingredientes || []).some((i) => i.nome === nome)) return;
    await pedir("POST", "/ingredientes", { nome, unidade_base: "g", categoria, confirmado_inexistente: true });
  }
  await ingrediente("Farinha de trigo", "Farinhas");
  await ingrediente("Água", "Líquidos");
  await ingrediente("Açúcar", "Outros");
  await ingrediente("Canela", "Outros");
  await ingrediente("Manteiga", "Outros");
  if (!nomes.has("Massa sovada")) {
    await pedir("POST", "/produtos", {
      nome: "Massa sovada",
      modalidade: "produzido",
      uso_venda: false,
      uso_componente: true,
      unidade_venda: "un",
      unidade_base: "g",
    });
  }
  const canela = (lista.produtos || []).find((p) => p.nome.startsWith("Pão de Canela"));
  if (canela) {
    await pedir("PUT", `/receitas/${canela.id}`, {
      linhas: [],
      rendimento_quantidade: null,
      rendimento_unidade: null,
      peso_unidade_g: null,
      perda_percentual: 0,
      modo_fazer: [],
    });
  }
  return { id: canela ? canela.id : "", nomes: [...nomes] };
}, csrf);
const produtoId = preparo.id;
if (!produtoId) throw new Error(`não achei o Pão de Canela (${(preparo.nomes || []).join(", ")})`);

await page.goto(`${base}/receitas/${produtoId}`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => [...document.querySelectorAll("button")].some((b) => b.textContent.includes("Sugerir com o Gigio")));
await page.evaluate(() => {
  [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Sugerir com o Gigio"))?.click();
});
await page.waitForFunction(() => document.body.innerText.includes("Conte ao Gigio"));
await page.waitForFunction(() => [...document.querySelectorAll('[role="dialog"] option')].some((o) => o.textContent.includes("Massa sovada")), { timeout: 10000 });
await page.type("textarea", "Pão de canela sobre a massa sovada. A canela eu não medi.");
const massaOk = await page.evaluate(() => {
  const painel = document.querySelector('[role="dialog"]');
  const opcao = [...(painel?.querySelectorAll("option") ?? [])].find((o) => o.textContent.includes("Massa sovada"));
  const select = painel?.querySelector("select");
  if (!opcao || !select) return false;
  const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, "value")?.set;
  setter?.call(select, opcao.value);
  select.dispatchEvent(new Event("change", { bubbles: true }));
  return select.value === opcao.value;
});
if (!massaOk) throw new Error("não achei a massa sovada no painel");

for (const largura of larguras) await capturar(page, largura, "gigio-passo1");

await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.evaluate(() => {
  [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "Pedir sugestão")?.click();
});
await page.waitForFunction(() => document.body.innerText.includes("Sugestão do Gigio"), { timeout: 15000 });
await pausa(300);
for (const largura of larguras) await capturar(page, largura, "gigio-passo3");

await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.evaluate(() => {
  [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Aplicar ao rascunho"))?.click();
});
await page.waitForFunction(() => document.body.innerText.includes("estimado"), { timeout: 15000 });
await pausa(400);
for (const largura of larguras) await capturar(page, largura, "receita-estimado");

writeFileSync(join(outDir, "capturas.md"), `# Capturas locais GESTAO-012\n\n| Arquivo | Checagem |\n|---|---|\n${linhas.join("\n")}\n`, "utf8");
await browser.close();
if (falhas) process.exitCode = 1;
