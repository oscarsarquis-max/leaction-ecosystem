/**
 * Capturas do GESTAO-004 (ambiente LOCAL: a entrada é só digitada, nunca gravada, mas o seed escreve no banco local).
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=... GESTAO_PASS=... \
 *   GESTAO_OUT=docs/evidence/gestao-004-local node scripts/capture-gestao-004.mjs
 *
 * Mostra: Entrada sem nota com 20 linhas (uma parecida, uma sem validade) em 1280 e em 390 px; a tabela em 1024 e 1440;
 * o cabeçalho fixo ao rolar; Tab/Enter; os contadores do rodapé; Ingredientes com o aviso de parecidos.
 * Confere em 320, 390, 768, 960, 1024, 1280 e 1440: sem rolagem horizontal da página e controles com 40 px (44 no celular).
 * A senha vem só do ambiente do processo. Requer puppeteer-core (GESTAO_PUPPETEER = package.json que o contém) e o Chrome.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-004-local";
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

function dataEm(dias) {
  const d = new Date(Date.now() + dias * 86400000);
  return d.toISOString().slice(0, 10);
}

/** 20 linhas, na ordem da planilha: item, ingrediente, marca, qtd, unidade, conteúdo, lote, validade, custo. */
function planilha() {
  const novos = [
    ["Fermento biológico seco 500 g", "Fermento biológico", "Fleischmann", "6", "kg", "", "", 120, "62,00"],
    ["Sal fino 1 kg", "Sal fino", "Cisne", "10", "kg", "", "", 400, "3,10"],
    ["Leite integral 1 L", "Leite integral", "Piracanjuba", "24", "l", "", "", 20, "5,40"],
    ["Chocolate meio amargo 1 kg", "Chocolate meio amargo", "Harald", "5", "kg", "", "", 180, "58,00"],
    ["Cacau em pó 200 g", "Cacau em pó", "Nestlé", "2", "kg", "", "", 300, "42,00"],
    ["Aveia em flocos 500 g", "Aveia em flocos", "Quaker", "3", "kg", "", "", 200, "14,50"],
    ["Farinha especial 5 kg", "Farinha de trig", "Sol", "20", "kg", "", "", 90, "4,30"], // parecida com “Farinha de trigo”
    ["Gergelim branco 1 kg", "Gergelim", "Kodilar", "2", "kg", "", "", 250, "21,00"],
    ["Linhaça dourada 500 g", "Linhaça", "Yoki", "2", "kg", "", "", 250, "17,00"],
    ["Mel puro 1 kg", "Mel", "Baldoni", "4", "kg", "", "", 500, "36,00"],
    ["Óleo de girassol 900 ml", "Óleo de girassol", "Liza", "12", "l", "", "", 150, "9,80"],
    ["Leite condensado 395 g", "Leite condensado", "Moça", "5", "kg", "", "", 140, "19,00"],
    ["Creme de leite 1 L", "Creme de leite", "Piracanjuba", "6", "l", "", "", null, "18,00"], // sem validade
    ["Queijo muçarela 4 kg", "Queijo muçarela", "Tirolez", "8", "kg", "", "", 25, "39,90"],
    ["Presunto cozido 3 kg", "Presunto cozido", "Sadia", "6", "kg", "", "", 18, "28,00"],
    ["Uva-passa 1 kg", "Uva-passa", "Hikari", "2", "kg", "", "", 300, "34,00"],
    ["Nozes sem casca 1 kg", "Nozes", "Nutty", "1", "kg", "", "", 200, "98,00"],
    ["Manteiga 200 g — Aviação", "", "", "24", "emb", "", "", 35, "11,50"],
    ["Açúcar refinado 5 kg — União", "", "", "20", "kg", "", "", 220, "5,10"],
    ["Coco ralado 1 kg", "Coco ralado", "Sococo", "2", "kg", "", "", 220, "27,00"],
  ];
  return novos
    .map(([item, ing, marca, qtd, un, cont, lote, dias, custo]) =>
      [item, ing, marca, qtd, un, cont, lote, dias === null ? "" : dataEm(dias), custo].join("\t"),
    )
    .join("\n");
}

async function abrirSemNotaCom20(page) {
  await page.goto(`${base}/entradas/sem-nota`, { waitUntil: "networkidle0" });
  await page.waitForSelector(".gestao-topbar");
  await (await porNome(page, "button", "Compra sem nota")).click();
  await (await porNome(page, "button", "Colar da planilha")).click();
  await page.waitForSelector('[role="dialog"] textarea');
  await page.evaluate((texto) => {
    const area = document.querySelector('[role="dialog"] textarea');
    Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(area, texto);
    area.dispatchEvent(new Event("input", { bubbles: true }));
  }, planilha());
  await (await porNome(page, '[role="dialog"] button', "Adicionar 20 linhas")).click();
  await page.waitForFunction(() => !document.querySelector('[role="dialog"]'), { timeout: 4000 });
  await page.waitForFunction(
    () => {
      const t = (document.querySelector(".entrada-rodape")?.textContent ?? "").replace(/\s+/g, " ");
      return /20 itens\s*1 a decidir/.test(t) && !/Conferindo/.test(t);
    },
    { timeout: 15000 },
  );
  await pausa(300);
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-first-run"] });
try {
  // ---- as larguras: a tabela e o resto, com 20 linhas
  for (const largura of [1280, 390, 1024, 1440, 960, 768, 320]) {
    const page = await abrirPagina(browser, largura);
    await entrar(page);
    await abrirSemNotaCom20(page);
    const completo = largura === 1280 || largura === 390;
    await capturar(page, largura, "entrada-sem-nota", { fullPage: completo || largura === 1024 || largura === 1440 });

    const medidas = await page.evaluate(() => ({
      tabela: Boolean(document.querySelector("table.entrada-tabela")),
      altura: document.documentElement.scrollHeight,
      linhasDaTabela: document.querySelectorAll("table.entrada-tabela tbody").length,
      alturaDaLinha: Math.round(document.querySelector("table.entrada-tabela tbody tr.linha-dados")?.getBoundingClientRect().height ?? 0),
      sublinhas: document.querySelectorAll("tr.linha-avisos").length,
      quadros: document.querySelectorAll(".grade-linha").length,
    }));
    const resumoMedidas =
      largura >= 1024
        ? `tabela, ${medidas.linhasDaTabela} linhas, ${medidas.alturaDaLinha} px por linha, ${medidas.sublinhas} sublinhas, página com ${medidas.altura} px`
        : `lista, ${medidas.quadros} itens, página com ${medidas.altura} px`;
    const esperado =
      largura >= 1024
        ? medidas.tabela && medidas.alturaDaLinha > 0 && medidas.alturaDaLinha <= 60 && medidas.altura < 3200
        : !medidas.tabela;
    nota(`medidas-${largura}`, esperado ? [] : [`fora do esperado ${JSON.stringify(medidas)}`], resumoMedidas);

    if (largura === 1280 || largura === 1024) {
      // cabeçalho fixo: rola a página e o cabeçalho continua no topo
      const alvoDeRolagem = largura === 1280 ? "window" : ".entrada-tabela-rolagem";
      await page.evaluate((alvo) => {
        if (alvo === "window") window.scrollTo(0, 620);
        else document.querySelector(alvo).scrollTo(0, 420);
      }, alvoDeRolagem);
      await pausa(300);
      const topo = await page.evaluate(() => {
        const th = document.querySelector("table.entrada-tabela thead th");
        const r = th.getBoundingClientRect();
        const cont = document.querySelector(".entrada-tabela-rolagem").getBoundingClientRect();
        return { thTop: Math.round(r.top), contTop: Math.round(cont.top), visivel: r.bottom > 0 && r.top >= -1 };
      });
      const fixo = largura === 1280 ? topo.thTop <= 1 && topo.visivel : Math.abs(topo.thTop - topo.contTop) <= 1;
      await capturar(page, largura, "entrada-sem-nota-rolada", { checar: false });
      nota(`cabecalho-fixo-${largura}`, fixo ? [] : [`cabeçalho saiu do topo ${JSON.stringify(topo)}`]);
      await page.evaluate(() => window.scrollTo(0, 0));
    }

    if (largura === 1280) {
      // contadores do rodapé: levam à primeira linha naquela situação
      const rodape = await page.$eval(".entrada-rodape", (no) => no.innerText.replace(/\s+/g, " ").trim());
      nota("rodape-1280", /20 itens/.test(rodape) && /1 a decidir/.test(rodape) && /0 incompletos/.test(rodape) && /1 sem validade/.test(rodape) ? [] : [rodape]);
      await (await porNome(page, ".entrada-rodape button", "sem validade")).click();
      await pausa(300);
      const noValidade = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
      nota("contador-sem-validade-1280", noValidade === "Validade, linha 13" ? [] : [`foco em ${noValidade}`]);
      await capturar(page, largura, "entrada-sem-nota-contador-validade", { checar: false });
      await (await porNome(page, ".entrada-rodape button", "a decidir")).click();
      await pausa(300);
      const noParecido = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
      nota("contador-a-decidir-1280", noParecido === "Ingrediente, linha 7" ? [] : [`foco em ${noParecido}`]);
      await capturar(page, largura, "entrada-sem-nota-contador-decidir", { checar: false });

      // teclado: Enter na última coluna segue para a linha de baixo
      await page.focus('[aria-label^="Custo"][aria-label$=", linha 1"]');
      await page.keyboard.press("Enter");
      const proxima = await page.evaluate(() => document.activeElement?.getAttribute("aria-label"));
      nota("enter-na-ultima-coluna-1280", proxima === "Item como comprado, linha 2" ? [] : [`foco em ${proxima}`]);

      // Tab segue a ordem das colunas
      await page.focus('[aria-label="Item como comprado, linha 3"]');
      const visitados = [];
      // o campo de data do Chrome tem uma parada de Tab por pedaço (dia, mês, ano, calendário): conta como uma coluna
      for (let i = 0; i < 16; i += 1) {
        await page.keyboard.press("Tab");
        const rotulo = await page.evaluate(() => (document.activeElement?.getAttribute("aria-label") ?? "").replace(/, linha \d+$/, ""));
        if (rotulo !== visitados[visitados.length - 1]) visitados.push(rotulo);
        if (rotulo.startsWith("Mais ações")) break;
      }
      const ordemOk =
        visitados.slice(0, 4).join(">") === "Ingrediente>Marca>Quantidade>Unidade" &&
        visitados.slice(-4).join(">").startsWith("Validade>Sem validade>") &&
        visitados[visitados.length - 1].startsWith("Mais ações");
      nota("tab-na-ordem-1280", ordemOk ? [] : [`ordem ${visitados.join(" > ")}`], `OK: item > ${visitados.join(" > ")}`);

      // menu ⋯
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.click('[aria-label="Mais ações da linha 7"]');
      await page.waitForSelector('[role="menu"]');
      await pausa(200);
      await capturar(page, largura, "entrada-sem-nota-menu-linha", { checar: false });
      await page.keyboard.press("Escape");
    }
    await page.close();
  }

  // ---- Ingredientes com o aviso de parecidos
  for (const largura of [1280, 390]) {
    const page = await abrirPagina(browser, largura);
    await entrar(page);
    await page.goto(`${base}/ingredientes`, { waitUntil: "networkidle0" });
    await page.waitForSelector(".gestao-topbar");
    await pausa(500);
    const aviso = await page.$eval('[role="status"]', (no) => no.innerText.replace(/\s+/g, " ").trim()).catch(() => "");
    const lista = await page.$$eval(".ingrediente-linha", (nos) => nos.map((no) => no.innerText.replace(/\s+/g, " ").trim()));
    const sal = lista.find((t) => t.startsWith("Sal")) ?? "";
    nota(
      `ingredientes-${largura}-aviso`,
      /1 par parece o mesmo ingrediente/.test(aviso) && /nenhum item/.test(sal) && /Sem saldo/.test(sal) && !/0 itens/.test(sal)
        ? []
        : [`aviso "${aviso}"; Sal: "${sal}"`],
    );
    await capturar(page, largura, "ingredientes", { fullPage: true });
    await page.close();
  }

  // ---- a trilha da barra de cima
  for (const largura of [1280, 1024]) {
    const page = await abrirPagina(browser, largura);
    await entrar(page);
    const trilha = await page.$eval(".gestao-trail", (no) => no.innerText.replace(/\s+/g, " ").trim());
    nota(`trilha-hoje-${largura}`, trilha === "Hoje" ? [] : [`trilha "${trilha}"`]);
    await capturar(page, largura, "hoje", { fullPage: false });
    await page.goto(`${base}/entradas/sem-nota`, { waitUntil: "networkidle0" });
    const trilha2 = await page.$eval(".gestao-trail", (no) => no.innerText.replace(/\s+/g, " ").trim());
    nota(`trilha-sem-nota-${largura}`, trilha2 === "Entradas / Entrada sem nota" ? [] : [`trilha "${trilha2}"`]);
    await page.close();
  }
} finally {
  await browser.close();
}
writeFileSync(join(outDir, "capturas.md"), `| Captura | Resultado |\n|---|---|\n${linhas.join("\n")}\n`);
console.log(falhas ? `${falhas} captura(s) com achado(s)` : "todas as capturas OK");
