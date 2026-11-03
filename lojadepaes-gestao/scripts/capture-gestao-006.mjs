/**
 * Capturas do GESTAO-006 (ambiente LOCAL, banco de demonstração; nada vai para produção).
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=... GESTAO_PASS=... \
 *   GESTAO_OUT=docs/evidence/gestao-006-local node scripts/capture-gestao-006.mjs
 *
 * Mostra, em 1280 e em 390 px:
 *  - a entrada: "Valor pago (R$)" com o custo calculado embaixo ("= R$ 45,98/kg" e, na embalagem,
 *    "= R$ 22,99/emb · R$ 45,98/kg") e o seletor "Valor pago ▾ | Preço por unidade";
 *  - o diálogo "Corrigir custo" (antes, depois, motivo) e, depois de gravar, a seção "Correções de custo";
 *  - "Trocar ingrediente" (o item ligado ao ingrediente errado) e o histórico depois da troca.
 * Confere: sem rolagem horizontal da página e controles com 40 px (44 no celular).
 * A senha vem só do ambiente do processo. Requer puppeteer-core (GESTAO_PUPPETEER) e o Chrome.
 * Rode antes `scripts/seed-demo-gestao-006.py` (dados de demonstração) num banco descartável.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-006-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
const requirePkg = createRequire(
  process.env.GESTAO_PUPPETEER ?? join(process.env.TEMP ?? "/tmp", "gestao-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

// A correção e a troca gravam no banco de demonstração: rode uma largura por vez, com o banco recém-semeado.
const larguras = (process.env.GESTAO_LARGURAS ?? "1280,390").split(",").map(Number);
const arquivoNotas = `capturas-${larguras.join("-")}.md`;
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

const sem = (s) => (s ?? "").replace(/\s+/g, " ").trim();

async function limparEDigitar(page, seletor, valor) {
  const campo = await page.waitForSelector(seletor);
  await campo.evaluate((no) => no.scrollIntoView({ block: "center" }));
  await pausa(120);
  await campo.click({ clickCount: 3 });
  await page.keyboard.press("Backspace");
  await page.keyboard.type(valor, { delay: 8 });
  return campo;
}

async function abrirEntrada(page) {
  await page.goto(`${base}/entradas/sem-nota`, { waitUntil: "networkidle0" });
  await page.waitForSelector(".gestao-topbar");
  await (await porNome(page, "button", "Compra sem nota")).click();
  await page.waitForSelector('input[aria-label="Item como comprado, linha 1"]');
  await pausa(300);
}

/** Texto cinza embaixo do campo de custo da linha n. */
const calculado = (page, n) =>
  page.evaluate((i) => {
    const campo = document.querySelector(`input[aria-label="Valor pago (R$), linha ${i}"]`);
    const alvo = campo?.closest("td, label, div")?.querySelector(".custo-calculado");
    return alvo ? alvo.textContent : "";
  }, n);

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-first-run"] });
try {
  for (const largura of larguras) {
    const celular = estreito(largura);

    // ---- 1) a entrada: valor pago com o custo calculado embaixo
    const page = await abrirPagina(browser, largura);
    await entrar(page);
    await abrirEntrada(page);

    await limparEDigitar(page, 'input[aria-label="Item como comprado, linha 1"]', "Farinha de trigo sarraceno 500 g");
    await limparEDigitar(page, 'input[aria-label="Quantidade, linha 1"]', "0,5");
    await page.select('select[aria-label="Unidade, linha 1"]', "kg");
    await limparEDigitar(page, 'input[aria-label="Valor pago (R$), linha 1"]', "22,99");
    await page.waitForFunction(
      () => document.querySelector('input[aria-label="Valor pago (R$), linha 1"]')?.closest("td, label, div")?.querySelector(".custo-calculado"),
      { timeout: 8000 },
    );
    const kg = sem(await calculado(page, 1));
    nota(`valor-pago-${largura}-kg`, /^= R\$\s*45,98\/kg$/.test(kg) ? [] : [`"${kg}"`], `0,5 kg por R$ 22,99 mostra “${kg}”`);

    if (celular) {
      await (await porNome(page, ".compacta-resumo", "Item sem nome")).click();
      await pausa(250);
    }
    await limparEDigitar(page, 'input[aria-label="Item como comprado, linha 2"]', "Fermento biológico seco 500 g");
    await limparEDigitar(page, 'input[aria-label="Quantidade, linha 2"]', "1");
    await page.select('select[aria-label="Unidade, linha 2"]', "emb");
    await limparEDigitar(page, 'input[aria-label="Conteúdo da embalagem, linha 2"]', "500");
    await limparEDigitar(page, 'input[aria-label="Valor pago (R$), linha 2"]', "22,99");
    // o "por kg" da embalagem aparece quando o ingrediente (a unidade do conteúdo) está confirmado
    await page.waitForSelector(".ing-confirmar", { timeout: 8000 }).catch(() => {});
    for (const botao of await page.$$(".ing-confirmar")) await botao.click().catch(() => {});
    await pausa(700);
    await page.waitForFunction(
      () => document.querySelector('input[aria-label="Valor pago (R$), linha 2"]')?.closest("td, label, div")?.querySelector(".custo-calculado"),
      { timeout: 8000 },
    );
    const emb = sem(await calculado(page, 2));
    nota(
      `valor-pago-${largura}-embalagem`,
      /^= R\$\s*22,99\/emb · R\$\s*45,98\/kg$/.test(emb) ? [] : [`"${emb}"`],
      `1 embalagem de 500 g por R$ 22,99 mostra “${emb}”`,
    );
    const rotuloEmb = await page.$eval('select[aria-label="Unidade, linha 2"]', (no) => [...no.options].map((o) => o.textContent));
    nota(`valor-pago-${largura}-rotulo-embalagem`, rotuloEmb.includes("embalagem") ? [] : [JSON.stringify(rotuloEmb)], "a unidade se chama “embalagem”");
    await capturar(page, largura, "entrada-valor-pago", { fullPage: true });

    // o seletor do cabeçalho: o preço por unidade ainda existe, e a escolha vale para a entrada toda
    await page.select('select[aria-label="Como informar o custo"]', "preco_unidade");
    await pausa(500);
    const rotulos = await page.$$eval('input[aria-label^="Custo R$"]', (nos) => nos.map((n) => n.getAttribute("aria-label")));
    nota(
      `preco-unidade-${largura}`,
      rotulos.length >= (celular ? 1 : 2) ? [] : [JSON.stringify(rotulos)], // no celular só a linha aberta aparece
      `no modo “Preço por unidade” os campos viram: ${rotulos.slice(0, 2).join(" | ")}`,
    );
    await capturar(page, largura, "entrada-preco-por-unidade", { fullPage: true });
    await page.select('select[aria-label="Como informar o custo"]', "valor_pago");
    await page.close();

    // ---- 2) Corrigir custo (no detalhe da entrada)
    const p2 = await abrirPagina(browser, largura);
    await entrar(p2);
    await p2.goto(`${base}/entradas`, { waitUntil: "networkidle0" });
    await (await porNome(p2, ".fluxo-linha", "Compra sem nota")).click();
    await p2.waitForSelector('[role="dialog"]');
    await p2.waitForFunction(() => document.querySelector('[role="dialog"] .painel-item'), { timeout: 8000 });
    await pausa(300);
    const pagos = sem(await p2.$eval('[role="dialog"] .painel-item', (no) => no.innerText));
    nota(`detalhe-${largura}-pagos`, /pagos/.test(pagos) ? [] : [pagos], `a linha diz o valor pago e o custo por kg: “${pagos.slice(-60)}”`);
    await capturar(p2, largura, "entrada-detalhe", { checar: true });
    await (await porNome(p2, '[role="dialog"] button', "Corrigir custo")).click();
    await p2.waitForSelector('[role="dialog"] form.corrigir-custo');
    await limparEDigitar(p2, '[role="dialog"] form.corrigir-custo input[type="text"]', "20");
    await limparEDigitar(p2, '[role="dialog"] form.corrigir-custo label:last-of-type input', "Erro de digitação na compra");
    await pausa(250);
    const antesDepois = sem(await p2.$eval('[role="dialog"] .antes-depois', (no) => no.innerText));
    nota(
      `corrigir-${largura}-antes-depois`,
      /Antes\s*R\$\s*45,98\/kg\s*Depois\s*R\$\s*40,00\/kg/.test(antesDepois) ? [] : [antesDepois],
      `mostra “${antesDepois}”`,
    );
    await p2.$eval('[role="dialog"] form.corrigir-custo', (no) => no.scrollIntoView({ block: "center" }));
    await pausa(200);
    await capturar(p2, largura, "corrigir-custo-dialogo");
    await (await porNome(p2, '[role="dialog"] button', "Gravar correção")).click();
    await p2.waitForFunction(() => !document.querySelector('[role="dialog"] form.corrigir-custo'), { timeout: 8000 });
    await p2.close();

    // ---- 3) o painel do ingrediente: custo do lote, correções, e Trocar ingrediente
    const p3 = await abrirPagina(browser, largura);
    await entrar(p3);
    await p3.goto(`${base}/ingredientes`, { waitUntil: "networkidle0" });
    await (await porNome(p3, ".fluxo-linha", "Farinha de trigo especial")).click();
    await p3.waitForSelector('[role="dialog"]');
    await p3.waitForFunction(() => document.querySelector('[role="dialog"] #pi-lotes'), { timeout: 8000 });
    await pausa(300);
    const painelTexto = sem(await p3.$eval('[role="dialog"]', (no) => no.innerText));
    nota(
      `ingrediente-${largura}-correcoes`,
      /Correções de custo/.test(painelTexto) && /R\$\s*45,98\/kg\s*→\s*R\$\s*40,00\/kg/.test(painelTexto) ? [] : [painelTexto.slice(0, 300)],
      "o painel traz o custo do lote e as “Correções de custo” (antes → depois, quem, motivo)",
    );
    await capturar(p3, largura, "ingrediente-custo-e-correcoes", { fullPage: false });

    await (await porNome(p3, '[role="dialog"] button', "Trocar ingrediente")).click();
    await p3.waitForSelector('[role="dialog"] form[aria-label^="Trocar o ingrediente"]');
    await pausa(300);
    const campo = await p3.waitForSelector('[role="dialog"] input[aria-label="Novo ingrediente do item"]');
    await campo.click();
    await p3.keyboard.type("sarraceno", { delay: 20 });
    await p3.waitForSelector('[role="listbox"]');
    await pausa(700);
    await (await porNome(p3, '[role="option"]', "Farinha de trigo sarraceno")).click();
    await pausa(300);
    await limparEDigitar(p3, '[role="dialog"] form[aria-label^="Trocar o ingrediente"] label input[type="text"]', "Estava ligado à farinha errada");
    await p3.$eval('[role="dialog"] form[aria-label^="Trocar o ingrediente"]', (no) => no.scrollIntoView({ block: "center" }));
    await pausa(250);
    await capturar(p3, largura, "trocar-ingrediente-dialogo");
    await (await porNome(p3, '[role="dialog"] button[type="submit"]', "Trocar ingrediente")).click();
    await p3.waitForFunction(
      () => /Troca de ingrediente|sarraceno/i.test(document.querySelector('[role="dialog"]')?.innerText ?? "") && !document.querySelector('form[aria-label^="Trocar o ingrediente"]'),
      { timeout: 10000 },
    );
    await pausa(500);
    const depois = sem(await p3.$eval('[role="dialog"]', (no) => no.innerText));
    nota(
      `trocar-${largura}-resultado`,
      /Farinha de trigo sarraceno/.test(depois) && /Trigo Sarraceno/.test(depois) ? [] : [depois.slice(0, 300)],
      "abre o ingrediente certo, com o item, o lote e o saldo que vieram junto",
    );
    await capturar(p3, largura, "trocar-ingrediente-resultado");
    await p3.close();
  }
} catch (erro) {
  // ajuda a achar o que travou: uma imagem de cada página aberta
  let n = 0;
  for (const contexto of browser.browserContexts()) {
    for (const aberta of await contexto.pages()) {
      await aberta.screenshot({ path: join(outDir, `erro-${(n += 1)}.png`) }).catch(() => {});
    }
  }
  throw erro;
} finally {
  await browser.close();
}
writeFileSync(join(outDir, arquivoNotas), `| Captura | Resultado |\n|---|---|\n${linhas.join("\n")}\n`);
console.log(falhas ? `${falhas} captura(s) com achado(s)` : "todas as capturas OK");
