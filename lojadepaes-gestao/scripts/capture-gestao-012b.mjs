/**
 * Capturas do GESTAO-012B no ambiente local, com o gateway falso.
 * Passo 3, aba Revisar e a tela Padrões, em 1280 e 390.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-012b-local";
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
    ["Água residual", "Líquidos"],
    ["Açúcar", "Açúcares e mel"],
    ["Canela", "Sal e temperos"],
    ["Manteiga", "Gorduras"],
    ["Sal", "Sal e temperos"],
  ];
  const atuais = await pedir("GET", "/ingredientes?filtro=todos");
  const porNome = new Map((atuais.json.ingredientes || []).map((i) => [i.nome, i]));
  const ids = {};
  for (const [nome, categoria] of desejados) {
    const existe = porNome.get(nome);
    if (!existe) {
      const criado = await pedir("POST", "/ingredientes", { nome, unidade_base: "g", categoria, confirmado_inexistente: true });
      ids[nome] = criado.json.id;
    } else {
      ids[nome] = existe.id;
      if (existe.categoria !== categoria) {
        await pedir("PATCH", `/ingredientes/${existe.id}`, { categoria });
      }
    }
  }
  const produtos = await pedir("GET", "/produtos?filtro=todos");
  let massa = (produtos.json.produtos || []).find((p) => p.nome === "Massa sovada");
  if (!massa) {
    const criado = await pedir("POST", "/produtos", {
      nome: "Massa sovada",
      modalidade: "produzido",
      uso_venda: false,
      uso_componente: true,
      unidade_venda: "un",
      unidade_base: "g",
    });
    massa = criado.json;
  }
  const deNovo = await pedir("GET", "/ingredientes?filtro=todos");
  const ingMassa = (deNovo.json.ingredientes || []).find((i) => i.nome === "Massa sovada");
  const receitaMassa = await pedir("PUT", `/receitas/${massa.id}`, {
    linhas: [
      { ingrediente_id: ids["Farinha de trigo"], quantidade: 500, unidade: "g" },
      { ingrediente_id: ids["Água"], quantidade: 300, unidade: "g" },
      { ingrediente_id: ids["Água residual"], quantidade: 30, unidade: "g" },
      { ingrediente_id: ids.Sal, quantidade: 10, unidade: "g" },
    ],
    rendimento_quantidade: 840,
    rendimento_unidade: "g",
    peso_unidade_g: null,
    perda_percentual: 0,
    modo_fazer: ["Misture a farinha com a água."],
  });
  const publicada = await pedir("POST", `/receitas/${massa.id}/publicar`);
  const canela = (produtos.json.produtos || []).find((p) => p.nome.startsWith("Pão de Canela"));
  const receitaCanela = await pedir("PUT", `/receitas/${canela.id}`, {
    linhas: [
      { ingrediente_id: ingMassa?.id, quantidade: 500, unidade: "g" },
      { ingrediente_id: ids.Sal, quantidade: 10, unidade: "g" },
    ],
    rendimento_quantidade: 1,
    rendimento_unidade: "un",
    peso_unidade_g: null,
    perda_percentual: 0,
    modo_fazer: [],
  });
  return {
    canela: canela?.id,
    massaIngrediente: ingMassa?.id,
    sal: ids.Sal,
    publicar: publicada.status,
    receitaMassa: receitaMassa.status,
    receitaCanela: receitaCanela.status,
  };
}, csrf);
if (!preparo.canela || !preparo.massaIngrediente) throw new Error(`preparo incompleto ${JSON.stringify(preparo)}`);
if (preparo.publicar !== 200 || preparo.receitaCanela !== 200) throw new Error(`gravação ${JSON.stringify(preparo)}`);

await page.goto(`${base}/receitas/${preparo.canela}`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => document.body.innerText.includes("Massa sovada") && document.body.innerText.includes("Sal"));
await clicar(page, "Revisar");
await page.waitForFunction(() => document.body.innerText.includes("Falta o fermento"), { timeout: 15000 });
await page.waitForFunction(() => document.body.innerText.includes("Massa sovada"));
for (const largura of [1280, 390]) await capturar(page, largura, "revisar");

const enxuta = await page.evaluate(async (id, sal) => {
  const sessao = await fetch("/api/v1/auth/sessao?rotacionar=true", { credentials: "include" });
  const token = (await sessao.json()).csrf;
  const r = await fetch(`/api/v1/receitas/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": token },
    credentials: "include",
    body: JSON.stringify({
      linhas: [{ ingrediente_id: sal, quantidade: 10, unidade: "g" }],
      rendimento_quantidade: 1,
      rendimento_unidade: "un",
      peso_unidade_g: null,
      perda_percentual: 0,
      modo_fazer: [],
    }),
  });
  return r.status;
}, preparo.canela, preparo.sal);
if (enxuta !== 200) throw new Error(`não limpei a receita do pão (${enxuta})`);

await page.goto(`${base}/receitas/${preparo.canela}`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => [...document.querySelectorAll("button")].some((b) => b.textContent.includes("Sugerir com o Gigio")));
await page.evaluate(() => {
  [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Sugerir com o Gigio"))?.click();
});
await page.waitForFunction(() => document.body.innerText.includes("Conte ao Gigio"));
await page.waitForFunction(() => [...document.querySelectorAll('[role="dialog"] option')].some((o) => o.textContent.includes("Massa sovada")));
await page.type("textarea", "Pão meio integral, levemente adocicado no miolo. A canela eu não medi.");
const massaOk = await page.evaluate(() => {
  const painel = document.querySelector('[role="dialog"]');
  const opcao = [...(painel?.querySelectorAll("option") ?? [])].find((o) => o.textContent.includes("Massa sovada"));
  const select = painel?.querySelector("select");
  if (!opcao || !select) return false;
  const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, "value")?.set;
  setter?.call(select, opcao.value);
  select.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
});
if (!massaOk) throw new Error("não achei a massa sovada");
await page.waitForSelector('[aria-label="Peso da massa"]');
await page.type('[aria-label="Peso da massa"]', "500");
await page.waitForFunction(() => {
  const botao = [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "Pedir sugestão");
  return Boolean(botao && !botao.disabled);
});
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await clicar(page, "Pedir sugestão");
await page.waitForFunction(() => document.body.innerText.includes("Altera a massa-base"), { timeout: 15000 });
await page.waitForFunction(() => /já está na Massa sovada|O sal está/.test(document.body.innerText));
const vazou = await page.evaluate(() => document.body.innerText.includes("Descrição do padeiro"));
if (vazou) throw new Error("o texto de contexto vazou no passo 3");
for (const largura of [1280, 390]) await capturar(page, largura, "gigio-passo3");

await page.goto(`${base}/gestao/padroes`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => {
  const texto = document.body.innerText.toLocaleLowerCase("pt-BR");
  return texto.includes("novo padrão") && texto.includes("observação");
});
for (const largura of [1280, 390]) await capturar(page, largura, "padroes");

writeFileSync(join(outDir, "capturas.md"), `# Capturas locais GESTAO-012B\n\n| Arquivo | Checagem |\n|---|---|\n${linhas.join("\n")}\n`, "utf8");
await browser.close();
if (falhas) process.exitCode = 1;
