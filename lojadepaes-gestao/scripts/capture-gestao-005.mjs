/**
 * Capturas do GESTAO-005 (ambiente LOCAL, banco de demonstração; nada vai para produção).
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=... GESTAO_PASS=... \
 *   GESTAO_OUT=docs/evidence/gestao-005-local node scripts/capture-gestao-005.mjs
 *
 * Mostra, em 1280 e em 390 px:
 *  - a busca do campo Ingrediente aberta (Sugeridos para o item / Na sua padaria / Do catálogo / Não encontrei);
 *  - a linha com a sugestão pendente (e o contador "a decidir");
 *  - o diálogo "Cadastrar novo ingrediente" com os existentes parecidos antes dos campos;
 *  - Ingredientes com o filtro de categoria.
 * Confere: sem rolagem horizontal da página e controles com 40 px (44 no celular).
 * A senha vem só do ambiente do processo. Requer puppeteer-core (GESTAO_PUPPETEER = package.json que o contém) e o Chrome.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-005-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
const requirePkg = createRequire(
  process.env.GESTAO_PUPPETEER ?? join(process.env.TEMP ?? "/tmp", "gestao-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

mkdirSync(outDir, { recursive: true });
const linhas = [];
let falhas = 0;
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));
const estreito = (largura) => largura < 960;

function nota(arquivo, achados, info = "OK") {
  const resultado = achados.length ? achados.join("; ") : info;
  if (achados.length) falhas += 1;
  linhas.push(`| ${arquivo} | ${resultado} |`);
  console.log(arquivo, resultado);
}

async function problemas(page, largura) {
  return page.evaluate(
    (minimo) => {
      const achados = [];
      const doc = document.documentElement;
      if (doc.scrollWidth > window.innerWidth + 1) achados.push(`rolagem horizontal ${doc.scrollWidth}>${window.innerWidth}`);
      const curtos = [...document.querySelectorAll("button, select, input:not([type=checkbox]):not([type=radio])")].filter((no) => {
        if (no.tabIndex === -1 && no.classList.contains("ing-confirmar")) return false;
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
    },
    estreito(largura) ? 44 : 40,
  );
}

async function abrirPagina(browser, largura) {
  const contexto = await browser.createBrowserContext();
  const page = await contexto.newPage();
  await page.setViewport({ width: largura, height: estreito(largura) ? 844 : 900, deviceScaleFactor: 1 });
  return page;
}

async function entrar(page) {
  await page.goto(`${base}/entrar`, { waitUntil: "networkidle0" });
  await page.waitForSelector('input[name="usuario"]');
  await page.type('input[name="usuario"]', usuario);
  await page.type('input[name="senha"]', senha);
  await page.click('button[type="submit"]');
  await page.waitForSelector(".gestao-topbar", { timeout: 15000 });
  await page.waitForNetworkIdle({ idleTime: 400, timeout: 15000 }).catch(() => {});
  await pausa(300);
}

async function capturar(page, largura, nome, { fullPage = false, checar = true } = {}) {
  const arquivo = `${nome}-${largura}.png`;
  if (fullPage) {
    const atual = page.viewport();
    const altura = await page.evaluate(() => document.documentElement.scrollHeight);
    await page.setViewport({ ...atual, height: Math.max(atual.height, altura) });
    await pausa(250);
    await page.screenshot({ path: join(outDir, arquivo) });
    await page.setViewport(atual);
    await pausa(150);
  } else {
    await page.screenshot({ path: join(outDir, arquivo) });
  }
  nota(arquivo, checar ? await problemas(page, largura) : []);
}

const porNome = async (page, seletor, texto) => {
  for (const alvo of await page.$$(seletor)) {
    const t = await alvo.evaluate((no) => (no.textContent ?? "").trim());
    if (t.includes(texto)) return alvo;
  }
  throw new Error(`não achei ${seletor} com "${texto}"`);
};

const texto = (page, seletor) => page.$eval(seletor, (no) => no.innerText.replace(/\s+/g, " ").trim()).catch(() => "");

async function digitarNoItem(page, valor) {
  const campo = await page.waitForSelector('input[aria-label="Item como comprado, linha 1"]');
  await campo.evaluate((no) => no.scrollIntoView({ block: "center" }));
  await pausa(150);
  await campo.click();
  await page.keyboard.down("Control");
  await page.keyboard.press("KeyA");
  await page.keyboard.up("Control");
  await page.keyboard.press("Backspace");
  await page.keyboard.type(valor, { delay: 8 });
  await campo.evaluate((no) => no.blur());
}

async function abrirEntrada(page) {
  await page.goto(`${base}/entradas/sem-nota`, { waitUntil: "networkidle0" });
  await page.waitForSelector(".gestao-topbar");
  await (await porNome(page, "button", "Compra sem nota")).click();
  await page.waitForSelector('input[aria-label="Item como comprado, linha 1"]');
  await pausa(300);
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-first-run"] });
try {
  for (const largura of [1280, 390]) {
    const page = await abrirPagina(browser, largura);
    await entrar(page);

    // ---- a linha com a sugestão pendente (item novo: o ingrediente vem sugerido, ninguém escolheu ainda)
    await abrirEntrada(page);
    await digitarNoItem(page, "Fermento fresco 500 g");
    await page.waitForSelector(".ing-confirmar", { timeout: 8000 });
    await pausa(300);
    const pendente = await page.$eval(".ing-campo.com-pendente input", (no) => no.placeholder);
    nota(
      `sugestao-pendente-${largura}-texto`,
      pendente === "Fermento biológico fresco" ? [] : [`sugestão "${pendente}"`],
      `sugestão pendente: ${pendente}`,
    );
    const rodape = await texto(page, ".entrada-rodape");
    nota(`a-decidir-${largura}`, /1 a decidir/.test(rodape) ? [] : [`rodapé "${rodape}"`], rodape);
    await capturar(page, largura, "linha-com-sugestao-pendente");

    // ---- busca aberta: Sugeridos / Na sua padaria / Do catálogo / Não encontrei
    await digitarNoItem(page, "Fermento biológico seco 500 g");
    await page.waitForFunction(() => document.querySelector(".ing-campo.com-pendente input")?.placeholder.length > 0, { timeout: 8000 });
    await pausa(500);
    const campoIng = await page.$('input[aria-label^="Ingrediente"]');
    await campoIng.evaluate((no) => no.scrollIntoView({ block: "start" }));
    await pausa(150);
    await campoIng.click();
    await page.waitForSelector('[role="listbox"]');
    await pausa(500);
    const lista = await texto(page, '[role="listbox"]');
    const esperado = ["Sugeridos para", "Na sua padaria", "Não encontrei, cadastrar novo"];
    nota(
      `busca-aberta-${largura}-secoes`,
      esperado.filter((t) => !lista.includes(t)).map((t) => `falta "${t}"`),
      lista.slice(0, 160),
    );
    await capturar(page, largura, "busca-aberta");
    // digitando: mostra também o catálogo
    await page.keyboard.type("fermento", { delay: 20 });
    await pausa(700);
    const lista2 = await texto(page, '[role="listbox"]');
    nota(
      `busca-catalogo-${largura}`,
      lista2.includes("Do catálogo") && lista2.includes("Fermento biológico seco") ? [] : [`lista "${lista2.slice(0, 200)}"`],
      "Do catálogo: Fermento biológico seco",
    );
    await capturar(page, largura, "busca-aberta-digitando");

    // ---- diálogo "Cadastrar novo"
    await (await porNome(page, '[role="option"]', "cadastrar novo")).click();
    await page.waitForSelector('[role="dialog"]');
    await pausa(900);
    const dialogo = await texto(page, '[role="dialog"]');
    const posExistentes = dialogo.indexOf("Estes já existem");
    const posCampos = dialogo.indexOf("Nome genérico");
    nota(
      `dialogo-novo-${largura}-ordem`,
      posExistentes >= 0 && posCampos > posExistentes && /Usar/.test(dialogo) && /Confirmo que não existe, cadastrar/.test(dialogo)
        ? []
        : [`diálogo "${dialogo.slice(0, 220)}"`],
      "existentes parecidos antes dos campos; botão “Confirmo que não existe, cadastrar”",
    );
    await capturar(page, largura, "dialogo-cadastrar-novo");
    await (await porNome(page, '[role="dialog"] button', "Cancelar")).click();
    await page.close();

    // ---- Ingredientes com o filtro de categoria
    const p2 = await abrirPagina(browser, largura);
    await entrar(p2);
    await p2.goto(`${base}/ingredientes`, { waitUntil: "networkidle0" });
    await p2.waitForSelector(".gestao-topbar");
    await pausa(500);
    await capturar(p2, largura, "ingredientes-todos", { fullPage: true });
    await p2.select(".filtro-categoria select", "Farinhas");
    await pausa(500);
    const visiveis = await p2.$$eval(".ingrediente-linha", (nos) => nos.map((no) => no.innerText.replace(/\s+/g, " ").trim()));
    nota(
      `ingredientes-filtro-${largura}`,
      visiveis.length === 2 && visiveis.every((t) => /Farinha/.test(t) && /Farinhas/.test(t)) ? [] : [`linhas ${JSON.stringify(visiveis)}`],
      `${visiveis.length} ingredientes em Farinhas`,
    );
    await capturar(p2, largura, "ingredientes-filtro-categoria", { fullPage: true });
    await p2.close();
  }
} finally {
  await browser.close();
}
writeFileSync(join(outDir, "capturas.md"), `| Captura | Resultado |\n|---|---|\n${linhas.join("\n")}\n`);
console.log(falhas ? `${falhas} captura(s) com achado(s)` : "todas as capturas OK");
