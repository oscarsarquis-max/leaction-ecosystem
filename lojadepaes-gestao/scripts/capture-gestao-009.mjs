/**
 * Capturas do GESTAO-009 (ambiente LOCAL). Não grava em produção.
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=demo GESTAO_PASS=... \
 *   GESTAO_OUT=docs/evidence/gestao-009-local node scripts/capture-gestao-009.mjs
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-009-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
if (!usuario || !senha) throw new Error("GESTAO_USER e GESTAO_PASS");
const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

const LARGURAS = [320, 390, 768, 960, 1280, 1440];
const COMPONENTE = "Cobertura de chocolate";
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
    const dialogo = document.querySelector(".gestao-modal");
    if (dialogo) {
      const caixa = dialogo.querySelector(".gestao-modal-caixa");
      if (caixa) {
        const c = caixa.getBoundingClientRect();
        if (c.left < -1 || c.right > window.innerWidth + 1) {
          achados.push(`caixa passa da borda ${Math.round(c.left)}..${Math.round(c.right)}`);
        }
        for (const campo of caixa.querySelectorAll("input, select")) {
          const r = campo.getBoundingClientRect();
          if (r.width > 1 && r.right > window.innerWidth + 1) {
            achados.push(`campo passa da borda ${campo.getAttribute("aria-label") || campo.placeholder || "input"}`);
          }
        }
      }
    }
    const curtos = [...document.querySelectorAll("button, select, input:not([type=checkbox]):not([type=radio])")].filter((no) => {
      if (no.classList.contains("selo-corrigido") || no.classList.contains("ing-confirmar") || no.classList.contains("ing-chip-x") || no.classList.contains("ing-ver")) return false;
      if (no.closest(".ing-lista")) return false;
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
  await page.goto(`${base}/`, { waitUntil: "networkidle0" });
  const formulario = await page.$('input[name="usuario"]');
  if (formulario) {
    await page.type('input[name="usuario"]', usuario);
    await page.type('input[name="senha"]', senha);
    await page.click('button[type="submit"]');
  }
  await page.waitForSelector(".gestao-topbar", { timeout: 15000 });
  await pausa(400);
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

async function preparar(page) {
  const texto = await page.evaluate(async (componente) => {
    const sessao = await fetch("/api/v1/auth/sessao").then((r) => r.json());
    const csrf = sessao.csrf;
    async function api(method, rota, corpo) {
      const r = await fetch(`/api/v1${rota}`, {
        method,
        headers: { Accept: "application/json", "Content-Type": "application/json", "X-CSRF-Token": csrf },
        body: corpo === undefined ? undefined : JSON.stringify(corpo),
      });
      const cru = await r.text();
      let json = null;
      try {
        json = cru ? JSON.parse(cru) : null;
      } catch {
        json = cru;
      }
      return { status: r.status, json };
    }
    const familias = await api("GET", "/familias");
    let familiaId = (familias.json.familias ?? []).find((f) => f.nome === "Coberturas e recheios")?.id;
    if (!familiaId) {
      const criada = await api("POST", "/familias", { nome: "Coberturas e recheios" });
      familiaId = criada.json.id;
    }
    const itens = await api("GET", "/produtos/itens?q=");
    const item = (itens.json.itens ?? [])[0];
    const lista = await api("GET", "/produtos");
    const nomes = new Set((lista.json.produtos ?? []).map((p) => p.nome));
    async function garantir(corpo) {
      if (nomes.has(corpo.nome)) return corpo.nome;
      const r = await api("POST", "/produtos", corpo);
      if (r.status !== 201) return `${corpo.nome} falhou ${r.status} ${JSON.stringify(r.json)}`;
      return corpo.nome;
    }
    const feitos = [];
    feitos.push(
      await garantir({
        nome: componente,
        modalidade: "produzido",
        uso_venda: true,
        uso_componente: true,
        familia_id: familiaId,
        unidade_venda: "un",
        confirmado_inexistente: true,
      }),
    );
    feitos.push(
      await garantir({
        nome: "Bolo de chocolate",
        modalidade: "produzido",
        uso_venda: true,
        uso_componente: false,
        unidade_venda: "un",
        confirmado_inexistente: true,
      }),
    );
    if (item) {
      feitos.push(
        await garantir({
          nome: "Chocolate em barra",
          modalidade: "comprado",
          uso_venda: true,
          uso_componente: false,
          unidade_venda: "un",
          item_estoque_id: item.id,
          confirmado_inexistente: true,
        }),
      );
    }
    feitos.push(
      await garantir({
        nome: "Pão de queijo congelado",
        modalidade: "comprado",
        uso_venda: true,
        uso_componente: false,
        unidade_venda: "un",
        confirmado_inexistente: true,
      }),
    );
    return feitos.join(" | ");
  }, COMPONENTE);
  console.log("preparado", texto);
  if (texto.includes("falhou")) throw new Error(texto);
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ["--no-sandbox"],
});
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await entrar(page);
await preparar(page);

for (const largura of LARGURAS) {
  await page.setViewport({ width: largura, height: largura < 960 ? 844 : 900, deviceScaleFactor: 1 });
  await page.goto(`${base}/produtos`, { waitUntil: "networkidle0" });
  await page.waitForFunction((nome) => document.body.innerText.includes(nome), { timeout: 8000 }, COMPONENTE);
  await pausa(300);
  await capturar(page, largura, "produtos-lista");

  await page.evaluate((nome) => {
    const botao = [...document.querySelectorAll("button.ing-nome")].find((el) => el.textContent.includes(nome));
    botao?.click();
  }, COMPONENTE);
  await page.waitForFunction(() => document.body.innerText.includes("Receita ainda vazia"), { timeout: 8000 });
  await pausa(300);
  await capturar(page, largura, "produtos-painel");
  await page.click('button[aria-label="Fechar"]');
  await pausa(200);

  await page.click("button.gestao-btn.is-primary");
  await page.waitForSelector(".gestao-modal");
  await page.evaluate(() => {
    const modal = document.querySelector(".gestao-modal");
    const rotulo = [...modal.querySelectorAll("label")].find((el) => el.textContent.trim() === "Comprado");
    rotulo?.querySelector("input")?.click();
  });
  await page.waitForSelector('input[placeholder="Buscar item de estoque"]', { timeout: 8000 });
  await pausa(300);
  await capturar(page, largura, "produtos-novo");
  await page.keyboard.press("Escape");
  await pausa(200);
}

await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.goto(`${base}/ingredientes`, { waitUntil: "networkidle0" });
await page.waitForSelector("table.lista-ingredientes, .fluxo-vazio");
await pausa(300);
await capturar(page, 1280, "ingredientes-lista");

await page.evaluate(() => {
  const botao = [...document.querySelectorAll("button")].find((el) => el.textContent.trim() === "Novo ingrediente");
  botao?.click();
});
await page.waitForSelector('[aria-label="Buscar ingrediente"]');
await page.evaluate(() => {
  const input = document.querySelector('[aria-label="Buscar ingrediente"]');
  const definir = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  definir.call(input, "Cobertura");
  input.dispatchEvent(new Event("input", { bubbles: true }));
});
await page.waitForFunction(
  () => document.body.innerText.includes("Preparos da casa") && document.body.innerText.includes("Cobertura de chocolate"),
  { timeout: 8000 },
);
await pausa(400);
await capturar(page, 1280, "ingredientes-busca");

await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
await page.goto(`${base}/ingredientes`, { waitUntil: "networkidle0" });
await page.waitForSelector("button.ing-nome");
await page.evaluate(() => {
  const botao = [...document.querySelectorAll("button.ing-nome")].find((el) => el.textContent.includes("tipo 00"));
  botao?.click();
});
await page.waitForSelector(".gestao-painel");
await page.waitForSelector('button[aria-label^="Ações de"]', { timeout: 8000 });
await page.click('button[aria-label^="Ações de"]');
await page.waitForSelector('[role="menuitem"]');
await page.evaluate(() => {
  const item = [...document.querySelectorAll('[role="menuitem"]')].find((el) => el.textContent.includes("Trocar ingrediente"));
  item?.click();
});
await page.waitForSelector('[aria-label="Novo ingrediente do item"]', { timeout: 8000 });
await pausa(400);
await capturar(page, 390, "trocar-destino");

await page.setViewport({ width: 2560, height: 1100, deviceScaleFactor: 1 });
const ing = readFileSync(join(outDir, "ingredientes-lista-1280.png")).toString("base64");
const prod = readFileSync(join(outDir, "produtos-lista-1280.png")).toString("base64");
const html = `<!doctype html><meta charset="utf-8"><title>Ingredientes e Produtos</title>
<style>
  body { margin: 0; display: flex; gap: 16px; background: #e7ece8; font-family: sans-serif; }
  figure { margin: 0; background: #fff; }
  figcaption { padding: 8px 12px; font-weight: 700; }
  img { display: block; width: 1280px; height: auto; }
</style>
<figure><figcaption>Ingredientes · 1280</figcaption><img src="data:image/png;base64,${ing}"></figure>
<figure><figcaption>Produtos · 1280</figcaption><img src="data:image/png;base64,${prod}"></figure>`;
await page.setContent(html, { waitUntil: "load" });
await pausa(400);
await page.screenshot({ path: join(outDir, "lado-a-lado-1280.png") });
nota("lado-a-lado-1280.png", []);

await page.close();
await browser.close();
writeFileSync(
  join(outDir, "capturas.md"),
  `# Capturas locais GESTAO-009\n\n| Arquivo | Checagem |\n|---|---|\n${linhas.join("\n")}\n`,
  "utf8",
);
if (falhas) process.exitCode = 1;
