/**
 * Capturas locais do GESTAO-014A.
 * Painel da Focaccia, Levain sem foto, modal com prévia e lista com miniatura.
 */
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-014a-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const foto = process.env.GESTAO_FOTO ?? "C:\\Temp\\gestao-014a-levain.jpg";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
if (!usuario || !senha) throw new Error("GESTAO_USER e GESTAO_PASS");
const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

mkdirSync(outDir, { recursive: true });
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));

async function problemas(page, largura) {
  const minimo = largura < 960 ? 44 : 40;
  return page.evaluate((piso) => {
    const achados = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > window.innerWidth + 1) achados.push(`rolagem horizontal ${doc.scrollWidth}>${window.innerWidth}`);
    const curtos = [...document.querySelectorAll("button, select, textarea, input:not([type=checkbox]):not([type=file])")].filter((no) => {
      if (no.classList.contains("linha-menu-botao") || no.classList.contains("ing-chip-x") || no.classList.contains("link-acao")) return false;
      const r = no.getBoundingClientRect();
      const estilo = getComputedStyle(no);
      if (estilo.visibility === "hidden" || estilo.display === "none" || no.hidden) return false;
      return r.width > 1 && r.height > 1 && r.height + 0.5 < piso;
    });
    if (curtos.length) achados.push(`controle abaixo de ${piso}px (${curtos.length})`);
    return achados;
  }, minimo);
}

async function capturar(page, largura, nome, alturaMin = 900) {
  await page.setViewport({ width: largura, height: alturaMin, deviceScaleFactor: 1 });
  await pausa(300);
  const altura = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewport({ width: largura, height: Math.max(alturaMin, Math.min(altura, 2200)), deviceScaleFactor: 1 });
  await pausa(200);
  await page.screenshot({ path: join(outDir, `${nome}.png`) });
  const achados = await problemas(page, largura);
  console.log(nome, achados.length ? achados.join("; ") : "OK");
  return achados;
}

async function sobreposicao(page) {
  return page.evaluate(() => {
    const quadro = document.querySelector(".foto-quadro");
    const img = document.querySelector(".foto-quadro img");
    const origem = document.querySelector(".foto-origem");
    const titulo = [...document.querySelectorAll("h3")].find((h) => h.textContent === "Estrutura");
    if (!quadro || !img || !origem || !titulo) return "faltou quadro, foto, origem ou Estrutura";
    const q = quadro.getBoundingClientRect();
    const i = img.getBoundingClientRect();
    const o = origem.getBoundingClientRect();
    const t = titulo.getBoundingClientRect();
    const dentro = i.top >= q.top - 1 && i.left >= q.left - 1 && i.bottom <= q.bottom + 1 && i.right <= q.right + 1;
    const ordem = o.top >= q.bottom - 1 && t.top >= o.bottom - 1;
    const natural = img.naturalWidth;
    if (!dentro) return `foto fora da caixa ${Math.round(i.width)}x${Math.round(i.height)} caixa ${Math.round(q.width)}x${Math.round(q.height)}`;
    if (!ordem) return "origem ou Estrutura sobre a foto";
    if (natural < 100) return "foto ainda não carregou";
    return "OK";
  });
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

const csrf = await page.evaluate(async () => {
  const r = await fetch("/api/v1/auth/sessao?rotacionar=true", { credentials: "include" });
  return (await r.json()).csrf;
});

async function pedir(method, caminho, corpo) {
  return page.evaluate(async (method, caminho, corpo, token) => {
    const r = await fetch(`/api/v1${caminho}`, {
      method,
      headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
      credentials: "include",
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    return { status: r.status, json: await r.json().catch(() => ({})) };
  }, method, caminho, corpo, csrf);
}

const lista = await pedir("GET", "/produtos?filtro=todos", null);
let focaccia = (lista.json.produtos || []).find((p) => p.nome.startsWith("Focaccia"));
if (!focaccia) throw new Error("Focaccia não está na demo local");
let levain = (lista.json.produtos || []).find((p) => p.nome === "Levain (fermento natural líquido)");
if (!levain) {
  const criado = await pedir("POST", "/produtos", {
    nome: "Levain (fermento natural líquido)",
    modalidade: "produzido",
    uso_venda: true,
    uso_componente: true,
    unidade_venda: "un",
    unidade_base: "g",
    confirmado_inexistente: true,
  });
  if (criado.status !== 201) throw new Error(`não criei o Levain: ${criado.status}`);
  levain = criado.json;
}

async function abrir(id) {
  await page.goto(`${base}/produtos`, { waitUntil: "networkidle0" });
  await page.evaluate((alvo) => {
    const botao = [...document.querySelectorAll("button.ing-nome")].find((b) => (b.textContent || "").includes(alvo));
    botao?.click();
  }, id);
  await page.waitForSelector(".foto-quadro", { timeout: 10000 });
  await pausa(800);
}

await abrir("Focaccia");
await page.waitForFunction(() => {
  const img = document.querySelector(".foto-quadro img");
  return img && img.complete && img.naturalWidth > 100;
}, { timeout: 15000 });
let falhas = 0;
for (const largura of [1280, 1920]) {
  const achados = await capturar(page, largura, `focaccia-${largura}`, largura === 1920 ? 1080 : 900);
  const posicao = await sobreposicao(page);
  console.log(`focaccia-${largura}-caixa`, posicao);
  if (achados.length || posicao !== "OK") falhas += 1;
}

await abrir("Levain");
await page.waitForFunction(() => document.body.innerText.includes("Adicionar foto"));
const vazio = await capturar(page, 1280, "levain-vazio-1280");
if (vazio.length) falhas += 1;

await page.evaluate(() => {
  const botao = [...document.querySelectorAll("button")].find((b) => (b.textContent || "").trim() === "Adicionar foto");
  botao?.click();
});
await page.waitForSelector(".gestao-modal");
const [chooser] = await Promise.all([
  page.waitForFileChooser(),
  page.evaluate(() => {
    const botao = [...document.querySelectorAll(".gestao-modal button")].find((b) => (b.textContent || "").trim() === "Escolher arquivo");
    botao?.click();
  }),
]);
await chooser.accept([foto]);
try {
  await page.waitForFunction(() => {
    const img = document.querySelector(".gestao-modal .foto-quadro img");
    return img && img.complete && img.naturalWidth > 10;
  }, { timeout: 8000 });
} catch (erro) {
  const texto = await page.evaluate(() => document.querySelector(".gestao-modal")?.innerText ?? "sem modal");
  console.log("MODAL", texto);
  await page.screenshot({ path: join(outDir, "debug-modal.png") });
  throw erro;
}
const modal = await capturar(page, 1280, "modal-previa-1280");
if (modal.length) falhas += 1;

await page.evaluate(() => {
  const botao = [...document.querySelectorAll(".gestao-modal button")].find((b) => (b.textContent || "").trim() === "Salvar");
  botao?.click();
});
await page.waitForFunction(() => document.body.innerText.includes("Foto enviada em"), { timeout: 15000 });

await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
await page.goto(`${base}/produtos`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => document.body.innerText.includes("Levain"));
const lista390 = await capturar(page, 390, "levain-lista-390", 844);
await page.evaluate(() => {
  const botao = [...document.querySelectorAll("button.ing-nome")].find((b) => (b.textContent || "").includes("Levain"));
  botao?.click();
});
await page.waitForSelector(".foto-quadro img", { timeout: 10000 });
await page.waitForFunction(() => document.body.innerText.includes("Foto enviada em"));
const painel390 = await capturar(page, 390, "levain-foto-390", 844);
if (lista390.length || painel390.length) falhas += 1;

await browser.close();
if (falhas) process.exit(1);
