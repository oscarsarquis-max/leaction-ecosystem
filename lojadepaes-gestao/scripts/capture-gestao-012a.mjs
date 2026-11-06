/**
 * Capturas do GESTAO-012A no ambiente local, com o gateway falso.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-012a-local";
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
  await pedir("PUT", `/receitas/${massa.id}`, {
    linhas: [
      { ingrediente_id: ids["Farinha de trigo"], quantidade: 500, unidade: "g" },
      { ingrediente_id: ids["Água"], quantidade: 300, unidade: "g" },
      { ingrediente_id: ids["Água residual"], quantidade: 30, unidade: "g" },
    ],
    rendimento_quantidade: 830,
    rendimento_unidade: "g",
    peso_unidade_g: null,
    perda_percentual: 0,
    modo_fazer: ["Misture a farinha com a água."],
  });
  const publicada = await pedir("POST", `/receitas/${massa.id}/publicar`);
  const canela = (produtos.json.produtos || []).find((p) => p.nome.startsWith("Pão de Canela"));
  await pedir("PUT", `/receitas/${canela.id}`, {
    linhas: [{ ingrediente_id: ids.Sal, quantidade: 10, unidade: "g" }],
    rendimento_quantidade: 1,
    rendimento_unidade: "un",
    peso_unidade_g: null,
    perda_percentual: 0,
    modo_fazer: [],
  });
  return { canela: canela.id, publicar: publicada.status };
}, csrf);
if (!preparo.canela) throw new Error("não achei o Pão de Canela");

await page.goto(`${base}/receitas/${preparo.canela}`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => [...document.querySelectorAll("button")].some((b) => b.textContent.includes("Sugerir com o Gigio")));
await page.evaluate(() => {
  [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Sugerir com o Gigio"))?.click();
});
await page.waitForFunction(() => document.body.innerText.includes("Conte ao Gigio"));
await page.waitForFunction(() => [...document.querySelectorAll('[role="dialog"] option')].some((o) => o.textContent.includes("Massa sovada")));
await page.type("textarea", "Pão de canela sobre a massa sovada. A canela eu não medi.");
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
await page.waitForFunction(() => document.body.innerText.includes("Sal"));

for (const largura of [390, 1280]) await capturar(page, largura, "gigio-passo1");

await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.evaluate(() => {
  [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "Pedir sugestão")?.click();
});
await page.waitForFunction(() => document.body.innerText.includes("Sugestão do Gigio"), { timeout: 15000 });
await pausa(300);
for (const largura of [390, 960, 1280]) await capturar(page, largura, "gigio-passo3");

await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await page.evaluate(() => {
  [...document.querySelectorAll("button")].find((b) => b.textContent.includes("Aplicar ao rascunho"))?.click();
});
await page.waitForFunction(() => document.body.innerText.includes("estimado"), { timeout: 15000 });
await pausa(400);
const duplicou = await page.evaluate(() => {
  const texto = document.body.innerText;
  return texto.includes("Farinha de trigo") || texto.includes("\nÁgua\n");
});
if (duplicou) throw new Error("a receita duplicou a farinha ou a água da base");
for (const largura of [390, 1280]) await capturar(page, largura, "receita-sem-duplicar");

await page.evaluate(() => {
  [...document.querySelectorAll("button")].find((b) => b.textContent.trim() === "Rendimento")?.click();
});
await page.waitForFunction(() => document.body.innerText.includes("Custo parcial"));
await capturar(page, 1280, "rendimento-parcial");

await page.goto(`${base}/receitas`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => document.body.innerText.includes("parcial"));
await capturar(page, 1280, "lista-parcial");

await page.goto(`${base}/gestao/padroes`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => document.body.innerText.includes("Hidratação"));
for (const largura of [390, 1280]) await capturar(page, largura, "padroes");

writeFileSync(join(outDir, "capturas.md"), `# Capturas locais GESTAO-012A\n\n| Arquivo | Checagem |\n|---|---|\n${linhas.join("\n")}\n`, "utf8");
await browser.close();
if (falhas) process.exitCode = 1;
