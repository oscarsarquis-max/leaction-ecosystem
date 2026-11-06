/**
 * Capturas do GESTAO-013A no ambiente local.
 * Rendimento com ajuste manual, Padrões › Perdas e as provas do item 0, em 1280 e 390.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-013a-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
if (!usuario || !senha) throw new Error("GESTAO_USER e GESTAO_PASS");
const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

mkdirSync(outDir, { recursive: true });
const linhas = [];
let falhas = 0;
const larguras = [1280, 390];
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
    ["Açúcar", "Açúcares e mel"],
    ["Sal", "Sal e temperos"],
  ];
  const atuais = await pedir("GET", "/ingredientes?filtro=todos");
  const porNome = new Map((atuais.json.ingredientes || []).map((i) => [i.nome, i]));
  const ids = {};
  for (const [nome, categoria] of desejados) {
    const existe = porNome.get(nome);
    if (!existe) {
      const criado = await pedir("POST", "/ingredientes", { nome, unidade_base: "g", categoria, confirmado_inexistente: true });
      if (!criado.json.id) return { erro: `ingrediente ${nome}`, detalhe: criado };
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
    peso_unidade_g: 500,
    perda_percentual: 0,
    modo_fazer: [],
    formato: "forma_enriquecida",
    unidades_desejadas: 10,
  });

  const lista = produtos.json.produtos || [];
  let base = lista.find((p) => p.nome === "Massa com açúcar");
  if (!base) {
    const criado = await pedir("POST", "/produtos", {
      nome: "Massa com açúcar",
      modalidade: "produzido",
      uso_venda: false,
      uso_componente: true,
      unidade_venda: "un",
    });
    if (!criado.json.id) return { erro: "base", detalhe: criado };
    base = criado.json;
  }
  const gravada = await pedir("PUT", `/receitas/${base.id}`, {
    linhas: [
      { ingrediente_id: ids["Farinha de trigo"], quantidade: 300, unidade: "g", funcao: "massa" },
      { ingrediente_id: ids["Açúcar"], quantidade: 20, unidade: "g", funcao: "massa" },
      { ingrediente_id: ids["Sal"], quantidade: 6, unidade: "g", funcao: "massa" },
    ],
    rendimento_quantidade: 326,
    rendimento_unidade: "g",
    perda_percentual: 0,
    modo_fazer: [],
  });
  const publicada = await pedir("POST", `/receitas/${base.id}/publicar`, { confirmar_sem_fermento: true });
  const deNovo = await pedir("GET", "/ingredientes?filtro=todos");
  const componente = (deNovo.json.ingredientes || []).find((i) => i.nome === "Massa com açúcar");
  let pao = (produtos.json.produtos || []).find((p) => p.nome === "Pão com calda");
  if (!pao) {
    const criado = await pedir("POST", "/produtos", {
      nome: "Pão com calda",
      modalidade: "produzido",
      uso_venda: true,
      uso_componente: false,
      unidade_venda: "un",
    });
    if (!criado.json.id) return { erro: "pao", detalhe: criado };
    pao = criado.json;
  }
  const montada = await pedir("PUT", `/receitas/${pao.id}`, {
    linhas: [
      { ingrediente_id: componente?.id, quantidade: 326, unidade: "g", funcao: "massa" },
      { ingrediente_id: ids["Sal"], quantidade: 10.2, unidade: "g", funcao: "massa" },
      { ingrediente_id: ids["Açúcar"], quantidade: 40, unidade: "g", funcao: "cobertura" },
    ],
    rendimento_quantidade: 1,
    rendimento_unidade: "un",
    perda_percentual: 0,
    modo_fazer: [],
  });
  const avisos = (montada.json.verificacoes?.avisos || []).map((a) => a.mensagem);
  const pendencias = (montada.json.verificacoes?.pendencias || []).map((a) => a.mensagem);
  const funcoes = (montada.json.linhas || []).map((l) => `${l.funcao}:${l.nome}`);
  return {
    canela: canela.id,
    canelaStatus: receita.status,
    perdas: receita.json.perdas,
    rendimento: receita.json.rendimento,
    pao: pao.id,
    baseStatus: gravada.status,
    publicada: publicada.status,
    montada: montada.status,
    funcoes,
    avisos,
    pendencias,
    erro: receita.json.detail || gravada.json.detail || publicada.json.detail || montada.json.detail || null,
  };
}, csrf);
if (preparo.canelaStatus !== 200 || preparo.montada !== 200) {
  throw new Error(`não preparei as receitas ${JSON.stringify(preparo)}`);
}
console.log("preparo", JSON.stringify({ rendimento: preparo.rendimento, perdas: preparo.perdas, funcoes: preparo.funcoes, avisos: preparo.avisos, pendencias: preparo.pendencias }));

await page.goto(`${base}/receitas/${preparo.canela}`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => document.body.innerText.includes("Pão de Canela"));
await clicar(page, "Rendimento");
await page.waitForFunction(
  () => document.body.innerText.includes("padrão da casa") && document.body.innerText.includes("Peças de 568 g") && document.body.innerText.includes("divida a massa assim"),
  { timeout: 15000 },
);
const camposAntigos = await page.evaluate(() => {
  const rotulos = [...document.querySelectorAll(".rendimento-campos span, .rendimento-campos label")].map((n) => n.textContent.trim());
  return rotulos.filter((t) => t === "Quantidade" || t === "Unidade");
});
if (camposAntigos.length) throw new Error(`campos antigos ainda na tela: ${camposAntigos.join(", ")}`);
await page.evaluate(() => {
  const input = document.querySelector('input[aria-label="Perda de processo"]');
  const definir = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  definir.call(input, "8");
  input.dispatchEvent(new Event("input", { bubbles: true }));
});
await page.waitForFunction(() => document.body.innerText.includes("ajuste manual") && document.body.innerText.includes("referência · forma enriquecida"));
await page.type('input[aria-label="Motivo do ajuste, Perda de processo"]', "Forno da casa");
for (const largura of larguras) await capturar(page, largura, "rendimento");

await page.goto(`${base}/gestao/padroes`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => [...document.querySelectorAll("button")].some((b) => b.textContent.trim() === "Perdas"));
await clicar(page, "Perdas");
await page.waitForFunction(() => document.body.innerText.includes("Forma enriquecida") && document.body.innerText.includes("Busby's Bakery"), { timeout: 15000 });
const fonte = await page.evaluate(() => {
  const link = [...document.querySelectorAll("a")].find((a) => a.textContent.trim() === "Busby's Bakery");
  return link ? { texto: link.textContent.trim(), title: link.getAttribute("title") } : null;
});
if (!fonte?.title?.includes("How Much Weight")) throw new Error(`fonte curta sem o título inteiro: ${JSON.stringify(fonte)}`);
for (const largura of larguras) await capturar(page, largura, "padroes-perdas");

await page.goto(`${base}/receitas/${preparo.pao}`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => {
  const texto = document.body.innerText.toLocaleLowerCase("pt-BR");
  return texto.includes("cobertura") && texto.includes("açúcar") && texto.includes("massa com açúcar");
}, { timeout: 15000 });
for (const largura of larguras) await capturar(page, largura, "editor-funcoes");

await clicar(page, "Revisar");
await page.waitForFunction(
  () => document.body.innerText.includes("Sal total 5,4 %") && document.body.innerText.includes("Publicar mesmo assim, sem fermento"),
  { timeout: 15000 },
);
const antes = await page.evaluate(() => {
  const botao = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Publicar versão"));
  return Boolean(botao?.disabled);
});
await page.click('input[type="checkbox"]');
await page.waitForFunction(() => {
  const botao = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Publicar versão"));
  return botao && !botao.disabled;
});
await page.click('input[type="checkbox"]');
await page.waitForFunction(() => {
  const botao = [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Publicar versão"));
  return botao && botao.disabled;
});
const publicar = { antes, marcou: true, desmarcou: true };
if (!antes) throw new Error("o Publicar já estava habilitado antes da confirmação");
for (const largura of larguras) await capturar(page, largura, "revisar");

writeFileSync(
  join(outDir, "capturas.md"),
  `# Capturas locais GESTAO-013A\n\n| Arquivo | Checagem |\n|---|---|\n${linhas.join("\n")}\n\nPublicar desabilitado sem a confirmação, e habilitado ao marcar: ${JSON.stringify(publicar)}.\n`,
  "utf8",
);
await browser.close();
if (falhas) process.exitCode = 1;
