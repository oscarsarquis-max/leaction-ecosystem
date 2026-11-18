/**
 * Capturas do GESTAO-005A (ambiente LOCAL, banco de demonstração; nada vai para produção).
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=... GESTAO_PASS=... \
 *   GESTAO_OUT=docs/evidence/gestao-005a-local node scripts/capture-gestao-005a.mjs
 *
 * Mostra, em 1280 e em 390 px:
 *  - o caso do fermento: "Fermento biológico seco 500 g" sugere SECO em destaque (do catálogo) e não sugere
 *    "fresco" (que a padaria já tem e que continua na busca, em "Na sua padaria");
 *  - o caso dos dois candidatos próximos: "Farinha 5 kg" não tem certeza, nada vem em destaque
 *    ("Escolha o ingrediente" e as sugestões à mão, sem nada marcado);
 *  - o diálogo "Cadastrar novo" com o candidato do catálogo ("do catálogo · Usar") e o nome e a categoria dele.
 * Confere: sem rolagem horizontal da página e controles com 40 px (44 no celular).
 * A senha vem só do ambiente do processo. Requer puppeteer-core (GESTAO_PUPPETEER) e o Chrome.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-005a-local";
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
        if (no.tabIndex === -1 && (no.classList.contains("ing-confirmar") || no.classList.contains("ing-ver"))) return false;
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

    // ---- 1) o caso do fermento: seco em destaque, fresco fora das sugestões
    await abrirEntrada(page);
    await digitarNoItem(page, "Fermento biológico seco 500 g");
    await page.waitForSelector(".ing-confirmar", { timeout: 8000 });
    await pausa(300);
    const pendente = await page.$eval(".ing-campo.com-pendente input", (no) => no.placeholder);
    nota(
      `fermento-${largura}-destaque`,
      pendente === "Fermento biológico seco" ? [] : [`destaque "${pendente}"`],
      `em destaque: ${pendente}`,
    );
    await capturar(page, largura, "fermento-seco-em-destaque");
    const campoIng = await page.$('input[aria-label^="Ingrediente"]');
    await campoIng.evaluate((no) => no.scrollIntoView({ block: "start" }));
    await pausa(150);
    await campoIng.click();
    await page.waitForSelector('[role="listbox"]');
    await pausa(600);
    const sugeridos = await page.$$eval('[role="group"][aria-label="Sugeridos"] .ing-opcao-nome strong', (nos) => nos.map((n) => n.textContent));
    const naPadaria = await page.$$eval('[role="listbox"] .ing-categoria .ing-opcao-nome strong', (nos) => nos.map((n) => n.textContent));
    nota(
      `fermento-${largura}-sugeridos`,
      sugeridos[0] === "Fermento biológico seco" && !sugeridos.some((n) => /fresco/i.test(n ?? "")) ? [] : [`sugeridos ${JSON.stringify(sugeridos)}`],
      `Sugeridos: ${sugeridos.join(", ")}`,
    );
    nota(
      `fermento-${largura}-busca-ainda-tem-fresco`,
      naPadaria.includes("Fermento biológico fresco") ? [] : [`Na sua padaria: ${JSON.stringify(naPadaria)}`],
      "“Fermento biológico fresco” segue em “Na sua padaria”",
    );
    await capturar(page, largura, "fermento-busca-aberta");

    // ---- 2) dois candidatos próximos: nada em destaque
    await page.keyboard.press("Escape");
    await digitarNoItem(page, "Farinha 5 kg");
    await page.waitForFunction(() => document.querySelector(".ing-campo.sem-certeza"), { timeout: 8000 });
    await pausa(300);
    const semCerteza = await page.$eval(".ing-campo.sem-certeza input", (no) => ({ ph: no.placeholder, pendente: Boolean(document.querySelector(".ing-confirmar")) }));
    nota(
      `dois-candidatos-${largura}-campo`,
      semCerteza.ph === "Escolha o ingrediente" && !semCerteza.pendente ? [] : [JSON.stringify(semCerteza)],
      "“Escolha o ingrediente”, nada em destaque, botão ▾ para ver as sugestões",
    );
    await capturar(page, largura, "dois-candidatos-sem-destaque");
    const ver = await page.$(".ing-ver");
    await ver.click();
    await page.waitForSelector('[role="listbox"]');
    await pausa(600);
    const marcadas = await page.$$eval('[role="option"][aria-selected="true"]', (nos) => nos.length);
    const sugeridos2 = await page.$$eval('[role="group"][aria-label="Sugeridos"] .ing-opcao-nome strong', (nos) => nos.map((n) => n.textContent));
    nota(
      `dois-candidatos-${largura}-lista`,
      marcadas === 0 && sugeridos2.length >= 2 ? [] : [`marcadas ${marcadas}, sugeridos ${JSON.stringify(sugeridos2)}`],
      `Sugeridos sem nada marcado: ${sugeridos2.join(", ")}`,
    );
    await capturar(page, largura, "dois-candidatos-lista-aberta");
    await page.keyboard.press("Enter");
    await pausa(300);
    const escolheu = await page.$('[role="group"][aria-label^="Ingrediente"]');
    nota(`dois-candidatos-${largura}-enter`, escolheu ? ["o Enter escolheu sozinho"] : [], "o Enter não escolhe ninguém");
    await page.close();

    // ---- 3) diálogo "Cadastrar novo" com o candidato do catálogo
    const p2 = await abrirPagina(browser, largura);
    await entrar(p2);
    await abrirEntrada(p2);
    await digitarNoItem(p2, "Fermento biológico seco 500 g");
    await p2.waitForSelector(".ing-confirmar", { timeout: 8000 });
    const c2 = await p2.$('input[aria-label^="Ingrediente"]');
    await c2.evaluate((no) => no.scrollIntoView({ block: "start" }));
    await pausa(150);
    await c2.click();
    await p2.keyboard.type("fermento", { delay: 20 });
    await pausa(700);
    await (await porNome(p2, '[role="option"]', "cadastrar novo")).click();
    await p2.waitForSelector('[role="dialog"]');
    await p2.waitForFunction(() => document.querySelector('[role="dialog"] input[type="text"]')?.value === "Fermento biológico seco", { timeout: 8000 });
    await pausa(900);
    const dados = await p2.evaluate(() => {
      const d = document.querySelector('[role="dialog"]');
      const campos = d.querySelectorAll("select");
      return {
        nome: d.querySelector('input[type="text"]').value,
        categoria: campos[0].value,
        texto: d.innerText.replace(/\s+/g, " "),
      };
    });
    nota(
      `dialogo-${largura}-prefill`,
      dados.nome === "Fermento biológico seco" && dados.categoria === "Fermentos" ? [] : [JSON.stringify(dados)],
      `nome “${dados.nome}”, categoria “${dados.categoria}”`,
    );
    nota(
      `dialogo-${largura}-lista`,
      /Fermento biológico seco\s*Fermentos · do catálogo/.test(dados.texto) && /Fermento biológico fresco/.test(dados.texto) ? [] : [dados.texto.slice(0, 260)],
      "a lista traz o do catálogo (“do catálogo · Usar”) e o que já existe",
    );
    await capturar(p2, largura, "dialogo-cadastrar-novo-catalogo");
    await p2.close();
  }
} finally {
  await browser.close();
}
writeFileSync(join(outDir, "capturas.md"), `| Captura | Resultado |\n|---|---|\n${linhas.join("\n")}\n`);
console.log(falhas ? `${falhas} captura(s) com achado(s)` : "todas as capturas OK");
