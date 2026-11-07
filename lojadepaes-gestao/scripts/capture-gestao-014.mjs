/**
 * Capturas do GESTAO-014 no ambiente local.
 * Semana, dia, programações e comanda (A4 e 80 mm), nas seis larguras.
 * A comanda também sai em PDF pelo Chrome local.
 */
import { spawnSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-014-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const python = process.env.GESTAO_PYTHON ?? "C:\\Projetos\\lojadepaes-gestao\\backend\\.venv\\Scripts\\python.exe";
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
    if (curtos.length) achados.push(`controle abaixo de ${piso}px (${curtos.length})`);
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
    const botao = [...document.querySelectorAll("button")].find((b) => (b.textContent || "").trim() === alvo);
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
  const ingredientes = await pedir("GET", "/ingredientes?filtro=todos");
  const porNome = new Map((ingredientes.json.ingredientes || []).map((i) => [i.nome, i.id]));
  const garantir = async (nome, categoria) => {
    if (porNome.get(nome)) return porNome.get(nome);
    const criado = await pedir("POST", "/ingredientes", { nome, unidade_base: "g", categoria, confirmado_inexistente: true });
    return criado.json.id;
  };
  const farinha = await garantir("Farinha de trigo", "Farinhas");
  const agua = await garantir("Água", "Líquidos");
  const fermento = await garantir("Fermento", "Fermentos");
  const produtos = await pedir("GET", "/produtos?filtro=todos");
  let pao = (produtos.json.produtos || []).find((p) => p.nome === "Pãozinho do calendário");
  if (!pao) {
    const criado = await pedir("POST", "/produtos", {
      nome: "Pãozinho do calendário",
      modalidade: "produzido",
      uso_venda: true,
      uso_componente: false,
      unidade_venda: "un",
      confirmado_inexistente: true,
    });
    if (!criado.json.id) return { erro: "produto", detalhe: criado };
    pao = criado.json;
  }
  const salva = await pedir("PUT", `/receitas/${pao.id}`, {
    linhas: [
      { ingrediente_id: farinha, quantidade: 1000, unidade: "g", funcao: "massa" },
      { ingrediente_id: agua, quantidade: 620, unidade: "g", funcao: "massa" },
      { ingrediente_id: fermento, quantidade: 12, unidade: "g", funcao: "massa" },
    ],
    peso_unidade_g: 500,
    perda_percentual: 0,
    modo_fazer: ["misturar", "dividir os pãezinhos", "assar"],
    formato: "forma_enriquecida",
    unidades_desejadas: 10,
  });
  if (salva.status !== 200) return { erro: "receita", detalhe: salva };
  if (salva.json.situacao !== "publicada") {
    const publicada = await pedir("POST", `/receitas/${pao.id}/publicar`);
    if (publicada.status !== 200) return { erro: "publicar", detalhe: publicada };
  }
  const fornadas = await pedir("GET", "/producao/fornadas");
  const ids = (fornadas.json.fornadas || []).map((f) => f.id);
  const programacoes = await pedir("GET", "/producao/programacoes");
  const ja = (programacoes.json.programacoes || []).find((p) => p.produto_id === pao.id && p.ativa);
  const corpo = {
    produto_id: pao.id,
    quantidade_por_fornada: 100,
    fornada_ids: ids,
    dias_semana: [0, 1, 2, 3, 4, 5],
    ativa: true,
  };
  const gravada = ja
    ? await pedir("PATCH", `/producao/programacoes/${ja.id}`, corpo)
    : await pedir("POST", "/producao/programacoes", corpo);
  if (gravada.status >= 300) return { erro: "programacao", detalhe: gravada };
  const semana = await pedir("GET", "/producao");
  return { produto_id: pao.id, hoje: semana.json.hoje, de: semana.json.de, ate: semana.json.ate, manha: (fornadas.json.fornadas || [])[0]?.id };
}, csrf);
console.log("preparo", JSON.stringify(preparo));
if (preparo.erro) {
  await browser.close();
  throw new Error(preparo.erro);
}

const semeado = spawnSync(python, ["-c", `
import os, uuid
from datetime import date
import psycopg
assert "127.0.0.1" in os.environ["GESTAO_DEMO_URL"] and "127.0.0.1" in os.environ["GESTAO_LOJA_URL"]
produto = "${preparo.produto_id}"
hoje = date.fromisoformat("${preparo.hoje}")
loja_id = uuid.uuid4()
with psycopg.connect(os.environ["GESTAO_DEMO_URL"]) as g:
    g.execute("UPDATE organizacoes SET fonte_loja = true WHERE nome_curto = 'demo'")
    g.execute("UPDATE produtos SET origem_loja_id = %s WHERE id = %s", (loja_id, produto))
    g.commit()
with psycopg.connect(os.environ["GESTAO_LOJA_URL"]) as loja:
    loja.execute("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE public_reference LIKE 'cap014-%')")
    loja.execute("DELETE FROM orders WHERE public_reference LIKE 'cap014-%'")
    loja.execute("DELETE FROM product_variants WHERE product_id IN (SELECT id FROM products WHERE slug = 'cap014-vitrine')")
    loja.execute("DELETE FROM products WHERE slug = 'cap014-vitrine'")
    loja.execute("DELETE FROM dough_types WHERE slug = 'cap014-criador'")
    loja.execute("DELETE FROM bread_shapes WHERE slug LIKE 'cap014-%'")
    base = uuid.uuid4()
    loja.execute("DELETE FROM recipe_bases WHERE code = 'cap014'")
    loja.execute("INSERT INTO recipe_bases (id, code, name, is_active) VALUES (%s, 'cap014', 'Base captura', true)", (base,))
    loja.execute("INSERT INTO products (id, name, slug, recipe_base_id, featured_image_caption, fidelity_eligible) VALUES (%s, 'Pao da vitrine', 'cap014-vitrine', %s, '', false)", (loja_id, base))
    variante = uuid.uuid4()
    loja.execute("INSERT INTO product_variants (id, product_id, display_name, presentation_type, units_per_pack, physical_units, price_cents, currency, is_active, sort_order) VALUES (%s, %s, 'Unidade', 'pack', 1, 1, 1000, 'BRL', true, 0)", (variante, loja_id))
    pedido = uuid.uuid4()
    loja.execute("INSERT INTO orders (id, public_reference, status, customer_note, currency, holds_capacity, production_local_date, customer_name, customer_email) VALUES (%s, 'cap014-1', 'confirmed', '', 'BRL', true, %s, 'NOME-SINTETICO', 'sintetico@example.invalid')", (pedido, hoje))
    loja.execute("INSERT INTO order_items (id, order_id, product_id, product_variant_id, quantity, physical_units, unit_price_cents, line_total_cents, recipe_base_id) VALUES (%s, %s, %s, %s, 12, 12, 1000, 12000, %s)", (uuid.uuid4(), pedido, loja_id, variante, base))
    massa = uuid.uuid4()
    loja.execute("INSERT INTO dough_types (id, name, slug, short_description, sort_order, is_active, recipe_base_id) VALUES (%s, 'Crie seu pão', 'cap014-criador', '', 0, true, %s)", (massa, base))
    forma = uuid.uuid4()
    loja.execute("INSERT INTO bread_shapes (id, name, slug, description, crust_crumb_notes, image_ref, sort_order, is_active) VALUES (%s, 'Bola', 'cap014-bola', '', '', '', 0, true)", (forma,))
    avulso = uuid.uuid4()
    loja.execute("INSERT INTO orders (id, public_reference, status, customer_note, currency, holds_capacity, production_local_date, customer_name, customer_email) VALUES (%s, 'cap014-2', 'confirmed', '', 'BRL', true, %s, 'NOME-SINTETICO', 'sintetico@example.invalid')", (avulso, hoje))
    loja.execute("INSERT INTO order_items (id, order_id, dough_type_id, bread_shape_id, quantity, physical_units, dough_name_snapshot, shape_name_snapshot, unit_price_cents, line_total_cents, recipe_base_id) VALUES (%s, %s, %s, %s, 2, 2, 'Crie seu pão', 'Bola', 1000, 2000, %s)", (uuid.uuid4(), avulso, massa, forma, base))
    loja.commit()
print("semeado")
`], {
  env: {
    ...process.env,
    GESTAO_DEMO_URL: "postgresql://gestao_app:app_test_pw@127.0.0.1:55440/gestao",
    GESTAO_LOJA_URL: "postgresql://postgres:pg_test_root@127.0.0.1:55440/lojadepaes_test",
  },
});
if (semeado.status !== 0) {
  console.log(semeado.stdout?.toString());
  console.log(semeado.stderr?.toString());
  await browser.close();
  throw new Error("semeadura local falhou");
}

await page.goto(`${base}/producao`, { waitUntil: "networkidle0" });
await clicar(page, "Trazer pedidos da Loja");
await page.waitForFunction(() => document.body.innerText.includes("Loja"), { timeout: 10000 });
await pausa(400);

for (const largura of larguras) await capturar(page, largura, "semana");

await page.goto(`${base}/producao/dia?data=${preparo.hoje}`, { waitUntil: "networkidle0" });
await page.waitForSelector("table.lista-producao", { timeout: 10000 });
for (const largura of larguras) await capturar(page, largura, "dia");

await page.goto(`${base}/producao/programacoes`, { waitUntil: "networkidle0" });
await page.waitForSelector("table.lista-producao", { timeout: 10000 });
for (const largura of larguras) await capturar(page, largura, "programacoes");
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await clicar(page, "Nova programação");
await page.waitForSelector(".gestao-side-panel, dialog, aside", { timeout: 5000 }).catch(() => {});
await pausa(300);
await capturar(page, 1280, "programacoes-modal");

await page.goto(`${base}/producao/comanda?data=${preparo.hoje}&fornada=${preparo.manha}`, { waitUntil: "networkidle0" });
await page.waitForSelector(".comanda-folha", { timeout: 10000 });
await page.evaluate(() => { window.print = () => {}; });
const botaoImpressao = await page.evaluate(() => {
  const botao = [...document.querySelectorAll("button")].find((b) => ["Imprimir", "Reimprimir"].includes((b.textContent || "").trim()));
  botao?.click();
  return Boolean(botao);
});
if (!botaoImpressao) throw new Error("não achei Imprimir");
await page.waitForFunction(() => document.body.innerText.includes("impressa em"), { timeout: 10000 });
for (const largura of larguras) await capturar(page, largura, "comanda-a4");
await page.pdf({
  path: join(outDir, "comanda-a4.pdf"),
  format: "A4",
  printBackground: true,
  margin: { top: "12mm", bottom: "12mm", left: "12mm", right: "12mm" },
});
nota("comanda-a4.pdf", []);
await clicar(page, "80 mm");
await pausa(200);
for (const largura of larguras) await capturar(page, largura, "comanda-80");
await page.pdf({
  path: join(outDir, "comanda-80.pdf"),
  width: "80mm",
  height: "420mm",
  printBackground: true,
  margin: { top: "4mm", bottom: "4mm", left: "4mm", right: "4mm" },
});
nota("comanda-80.pdf", []);

await page.goto(`${base}/`, { waitUntil: "networkidle0" });
await page.waitForFunction(() => document.body.innerText.includes("Produção de hoje"), { timeout: 10000 });
for (const largura of [1280, 390]) await capturar(page, largura, "hoje");

await browser.close();
console.log(`falhas=${falhas}`);
if (falhas) process.exit(1);
