/**
 * Capturas do GESTAO-010 (ambiente LOCAL). Não grava em produção.
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=demo GESTAO_PASS=... \
 *   GESTAO_OUT=docs/evidence/gestao-010-local node scripts/capture-gestao-010.mjs
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-010-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
if (!usuario || !senha) throw new Error("GESTAO_USER e GESTAO_PASS");
const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

const LARGURAS = [320, 390, 768, 960, 1280, 1440];
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
    const curtos = [...document.querySelectorAll("button, select, input:not([type=checkbox]):not([type=radio])")].filter((no) => {
      if (no.classList.contains("ing-chip-x") || no.classList.contains("linha-menu-botao")) return false;
      if (no.closest(".ing-lista") || no.closest(".linha-menu-lista")) return false;
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

async function capturar(page, largura, nome) {
  const arquivo = `${nome}-${largura}.png`;
  const atual = page.viewport();
  const altura = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewport({ ...atual, height: Math.max(atual.height, Math.min(altura, 1600)) });
  await pausa(250);
  await page.screenshot({ path: join(outDir, arquivo) });
  await page.setViewport(atual);
  nota(arquivo, await problemas(page, largura));
}

async function porTexto(page, texto) {
  const achou = await page.evaluate((alvo) => {
    const botao = [...document.querySelectorAll("button")].find((el) => el.textContent.trim() === alvo);
    botao?.click();
    return Boolean(botao);
  }, texto);
  if (!achou) throw new Error(`não achei o botão ${texto}`);
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });

await page.goto(`${base}/`, { waitUntil: "networkidle0" });
await page.waitForSelector(".gestao-login-brand");
await page.evaluate(() => {
  const marca = document.querySelector(".gestao-login-brand");
  const sub = document.createElement("span");
  sub.className = "gestao-brand-sub";
  sub.textContent = "Gestão";
  marca.appendChild(sub);
});
await pausa(200);
await capturar(page, 1280, "login-antes");
await page.evaluate(() => document.querySelector(".gestao-brand-sub")?.remove());
await pausa(200);
await capturar(page, 1280, "login-depois");

await page.type('input[name="usuario"]', usuario);
await page.type('input[name="senha"]', senha);
await page.click('button[type="submit"]');
await page.waitForSelector(".gestao-side", { timeout: 15000 });
await pausa(400);

await page.evaluate(() => {
  const marca = document.querySelector(".gestao-brand-link");
  const sub = document.createElement("span");
  sub.className = "gestao-brand-sub";
  sub.textContent = "Gestão";
  marca.appendChild(sub);
});
await pausa(200);
await capturar(page, 1280, "menu-antes");
await page.reload({ waitUntil: "networkidle0" });
await page.waitForSelector(".gestao-side");
await pausa(300);
await capturar(page, 1280, "menu-depois");

await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
await page.goto(`${base}/`, { waitUntil: "networkidle0" });
await page.waitForSelector('button[aria-label*="Abrir a lista"]');
await page.click('button[aria-label*="Abrir a lista"]');
await page.waitForSelector(".gestao-drawer-head");
await page.evaluate(() => {
  const marca = document.querySelector(".gestao-drawer-head .gestao-brand-link");
  const sub = document.createElement("span");
  sub.className = "gestao-brand-sub";
  sub.textContent = "Gestão";
  marca.appendChild(sub);
});
await pausa(200);
await capturar(page, 390, "menu-celular-antes");
await page.evaluate(() => document.querySelector(".gestao-brand-sub")?.remove());
await pausa(200);
await capturar(page, 390, "menu-celular-depois");

await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.goto(`${base}/produtos`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => document.body.innerText.includes("Cobertura de chocolate"));
await page.evaluate(() => {
  const botao = [...document.querySelectorAll("button.ing-nome")].find((el) => el.textContent.includes("Cobertura de chocolate"));
  botao?.click();
});
await page.waitForSelector(".gestao-painel");
await page.waitForFunction(() => [...document.querySelectorAll("button")].some((el) => el.textContent.trim() === "Editar"), { timeout: 8000 });
await porTexto(page, "Editar");
await page.waitForFunction(() => document.body.innerText.includes("Unidade base do preparo"));
await page.evaluate(() => {
  const rotulo = [...document.querySelectorAll("label")].find((el) => el.textContent.includes("Unidade base do preparo"));
  const select = rotulo.querySelector("select");
  const definir = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, "value").set;
  definir.call(select, "g");
  select.dispatchEvent(new Event("change", { bubbles: true }));
});
await porTexto(page, "Salvar");
await page.waitForFunction(() => document.body.innerText.includes("Ver em Ingredientes"), { timeout: 8000 });
await pausa(300);

const preparado = await page.evaluate(async () => {
  const sessao = await fetch("/api/v1/auth/sessao").then((r) => r.json());
  const csrf = sessao.csrf;
  async function api(method, rota, corpo) {
    const r = await fetch(`/api/v1${rota}`, {
      method,
      headers: { Accept: "application/json", "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    });
    const json = await r.json();
    return { status: r.status, json };
  }
  const produtos = (await api("GET", "/produtos")).json.produtos;
  const cobertura = produtos.find((p) => p.nome === "Cobertura de chocolate");
  const bolo = produtos.find((p) => p.nome === "Bolo de chocolate");
  const detalheCob = await api("GET", `/produtos/${cobertura.id}`);
  const ingredientes = (await api("GET", "/ingredientes")).json.ingredientes;
  const farinha = ingredientes.find((i) => i.nome === "Farinha de trigo" && i.categoria === "Farinhas");
  const sal = ingredientes.find((i) => i.nome === "Sal");
  const receitaCob = await api("PUT", `/receitas/${cobertura.id}`, {
    linhas: [{ ingrediente_id: farinha.id, quantidade: 200, unidade: "g" }],
    rendimento_quantidade: 200,
    rendimento_unidade: "g",
    perda_percentual: 0,
    modo_fazer: ["Derreta e misture."],
  });
  const publicada = await api("POST", `/receitas/${cobertura.id}/publicar`);
  const receitaBolo = await api("PUT", `/receitas/${bolo.id}`, {
    linhas: [
      { ingrediente_id: farinha.id, quantidade: 500, unidade: "g" },
      { ingrediente_id: detalheCob.json.ingrediente_id, quantidade: 200, unidade: "g" },
      { ingrediente_id: sal.id, quantidade: 10, unidade: "g" },
    ],
    rendimento_quantidade: 10,
    rendimento_unidade: "un",
    perda_percentual: 0,
    modo_fazer: ["Misture a farinha.", "Cubra com a cobertura."],
  });
  return {
    unidade: detalheCob.json.unidade_base,
    cob: `${receitaCob.status}/${publicada.status}`,
    bolo: receitaBolo.status,
    componente: (receitaBolo.json.linhas ?? []).some((l) => l.componente),
  };
});
console.log("preparado", JSON.stringify(preparado));
if (preparado.unidade !== "g" || preparado.bolo !== 200 || !preparado.componente) {
  throw new Error(`preparo incompleto ${JSON.stringify(preparado)}`);
}

const abas = [
  ["ingredientes", "Ingredientes", "receita-ingredientes"],
  ["modo", "Modo de fazer", "receita-modo"],
  ["rendimento", "Rendimento", "receita-rendimento"],
  ["revisar", "Revisar", "receita-revisar"],
];

for (const largura of LARGURAS) {
  await page.setViewport({ width: largura, height: largura < 960 ? 844 : 900, deviceScaleFactor: 1 });
  await page.goto(`${base}/receitas`, { waitUntil: "networkidle0" });
  await page.waitForFunction(() => document.body.innerText.includes("Bolo de chocolate"), { timeout: 8000 });
  await pausa(300);
  await capturar(page, largura, "receitas-lista");

  await page.evaluate(() => {
    const botao = [...document.querySelectorAll("button.ing-nome")].find((el) => el.textContent.includes("Bolo de chocolate"));
    botao?.click();
  });
  await page.waitForFunction(() => document.body.innerText.includes("% do padeiro") || document.body.innerText.includes("Colar da planilha"), { timeout: 8000 });
  await pausa(400);
  for (const [, rotulo, nome] of abas) {
    if (rotulo !== "Ingredientes") {
      await porTexto(page, rotulo);
      await pausa(500);
    }
    await capturar(page, largura, nome);
  }
}

await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.goto(`${base}/produtos`, { waitUntil: "networkidle0" });
await page.evaluate(() => {
  const botao = [...document.querySelectorAll("button.ing-nome")].find((el) => el.textContent.includes("Bolo de chocolate"));
  botao?.click();
});
await page.waitForFunction(() => document.body.innerText.includes("Montar receita") && document.body.innerText.includes("Cobertura de chocolate"), { timeout: 8000 });
await pausa(300);
await capturar(page, 1280, "produto-estrutura");

await page.goto(`${base}/entradas/sem-nota`, { waitUntil: "networkidle0" });
await page.waitForSelector(".entrada-pagina, .entrada-grade", { timeout: 8000 });
await pausa(300);
await capturar(page, 1280, "entrada-sem-nota");

await page.setViewport({ width: 2560, height: 1100, deviceScaleFactor: 1 });
const entrada = readFileSync(join(outDir, "entrada-sem-nota-1280.png")).toString("base64");
const editor = readFileSync(join(outDir, "receita-ingredientes-1280.png")).toString("base64");
const html = `<!doctype html><meta charset="utf-8"><title>Entrada e receita</title>
<style>
  body { margin: 0; display: flex; gap: 16px; background: #e7ece8; font-family: sans-serif; }
  figure { margin: 0; background: #fff; }
  figcaption { padding: 8px 12px; font-weight: 700; }
  img { display: block; width: 1280px; height: auto; }
</style>
<figure><figcaption>Entrada sem nota · 1280</figcaption><img src="data:image/png;base64,${entrada}"></figure>
<figure><figcaption>Receita · Ingredientes · 1280</figcaption><img src="data:image/png;base64,${editor}"></figure>`;
await page.setContent(html, { waitUntil: "load" });
await pausa(400);
await page.screenshot({ path: join(outDir, "lado-a-lado-1280.png") });
nota("lado-a-lado-1280.png", []);

await page.close();
await browser.close();
writeFileSync(
  join(outDir, "capturas.md"),
  `# Capturas locais GESTAO-010\n\n| Arquivo | Checagem |\n|---|---|\n${linhas.join("\n")}\n`,
  "utf8",
);
if (falhas) process.exitCode = 1;
