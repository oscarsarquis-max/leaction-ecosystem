/**
 * Capturas da Gestão no padrão 108A da Loja (6 larguras: 320, 390, 768, 960, 1280, 1440), com checagens:
 * sem rolagem horizontal, barra numa linha só, controles com a altura mínima (40 px no desktop, 44 px no celular)
 * e anel de foco.
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=... GESTAO_PASS=... \
 *   GESTAO_OUT=docs/evidence/gestao-003 node scripts/capture-evidence.mjs
 *
 * Modos (GESTAO_MODO):
 *   completo (padrão)  login, menu lateral, Hoje, Entradas, Entrada sem nota, Ingredientes. ESCREVE dados
 *                      (a entrada sem nota é só digitada, nunca gravada), por isso só em ambiente local.
 *   porta              login, menu lateral e o portão de aceite (cliente e admin da plataforma). Só lê.
 *                      Aceita GESTAO_ADMIN_USER / GESTAO_ADMIN_PASS para a conta sem organização.
 *
 * As senhas vêm só do ambiente do processo; nada delas é gravado.
 * Requer puppeteer-core (GESTAO_PUPPETEER = caminho do package.json que o contém) e o Chrome.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const usuarioAdmin = process.env.GESTAO_ADMIN_USER ?? "";
const senhaAdmin = process.env.GESTAO_ADMIN_PASS ?? "";
const modo = process.env.GESTAO_MODO ?? "completo";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-003";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const requirePkg = createRequire(
  process.env.GESTAO_PUPPETEER ?? join(process.env.TEMP ?? "/tmp", "gestao-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

const LARGURAS = [320, 390, 768, 960, 1280, 1440];
const COM_DADOS = [1280, 390];
let adminFalhou = false; // se o login do admin da plataforma falhar, não tenta de novo (evita travar a conta)

mkdirSync(outDir, { recursive: true });
const linhas = [];
let falhas = 0;

function nota(arquivo, achados) {
  const resultado = achados.length ? achados.join("; ") : "OK";
  if (achados.length) falhas += 1;
  linhas.push(`| ${arquivo} | ${resultado} |`);
  console.log(arquivo, resultado);
}

const estreito = (largura) => largura < 960;
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));

async function problemas(page, largura) {
  return page.evaluate(
    (minimo) => {
      const achados = [];
      const doc = document.documentElement;
      if (doc.scrollWidth > window.innerWidth + 1) {
        achados.push(`rolagem horizontal ${doc.scrollWidth}>${window.innerWidth}`);
      }
      const barra = document.querySelector(".gestao-topbar");
      if (barra && getComputedStyle(barra).borderBottomWidth !== "1px") achados.push("borda inferior ausente");
      const curtos = [...document.querySelectorAll("button, a.nl, select, input:not([type=checkbox]):not([type=radio])")].filter(
        (no) => {
          const r = no.getBoundingClientRect();
          const estilo = getComputedStyle(no);
          if (estilo.visibility === "hidden" || estilo.display === "none") return false;
          return r.width > 1 && r.height > 1 && r.height + 0.5 < minimo;
        },
      );
      if (curtos.length) {
        achados.push(
          `controle abaixo de ${minimo}px: ${[...new Set(curtos.map((no) => `${no.tagName.toLowerCase()}.${String(no.className).split(" ")[0]}`))].slice(0, 6).join(", ")}`,
        );
      }
      const cortado = [...document.querySelectorAll(".org-cnpj")].filter((no) => no.scrollWidth > no.clientWidth + 1);
      if (cortado.length) achados.push("CNPJ cortado");
      return achados;
    },
    estreito(largura) ? 44 : 40,
  );
}

async function abrirPagina(browser, largura, escala = 1) {
  // contexto novo a cada página: nenhuma sessão ou cookie vaza de uma captura para a outra
  const contexto = await browser.createBrowserContext();
  const page = await contexto.newPage();
  await page.setViewport({ width: largura, height: estreito(largura) ? 844 : 900, deviceScaleFactor: escala });
  return page;
}

async function entrar(page, user, pass) {
  await page.goto(`${base}/entrar`, { waitUntil: "networkidle0" });
  await page.waitForSelector('input[name="usuario"]');
  await page.type('input[name="usuario"]', user);
  await page.type('input[name="senha"]', pass);
  await page.click('button[type="submit"]');
}

async function sair(page) {
  await page.evaluate(async () => {
    const sessao = await (await fetch("/api/v1/auth/sessao?rotacionar=true", { credentials: "same-origin" })).json();
    await fetch("/api/v1/auth/sair", { method: "POST", credentials: "same-origin", headers: { "X-CSRF-Token": sessao.csrf } });
  });
}

async function aguardarShell(page) {
  await page.waitForSelector(".gestao-topbar", { timeout: 15000 });
  await page.waitForNetworkIdle({ idleTime: 400, timeout: 15000 }).catch(() => {});
  await pausa(300);
}

async function capturar(page, largura, nome, opcoes = {}) {
  const arquivo = `${nome}-${largura}${opcoes.sufixo ?? ""}.png`;
  if (opcoes.fullPage) {
    // a página inteira numa janela do tamanho dela, para o rodapé fixo ficar no fim e não no meio
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
  nota(arquivo, opcoes.semChecagem ? [] : await problemas(page, largura));
}

async function capturarMenu(page, largura, sufixo = "") {
  if (estreito(largura)) {
    await page.click(".gestao-etapa-botao");
    await page.waitForSelector(".gestao-side.is-open");
    await pausa(250);
    await capturar(page, largura, "menu", { sufixo });
    await page.keyboard.press("Escape");
    await pausa(200);
    if (await page.$(".gestao-side.is-open")) await page.click(".gestao-etapa-botao");
  } else {
    const lateral = await page.$(".gestao-side");
    const caixa = await lateral.boundingBox();
    const arquivo = `menu-${largura}${sufixo}.png`;
    await page.screenshot({ path: join(outDir, arquivo), clip: { x: 0, y: 0, width: Math.ceil(caixa.width), height: Math.min(caixa.height, 900) } });
    nota(arquivo, await problemas(page, largura));
  }
}

async function preencher(page, rotulo, valor, largura) {
  await page.waitForSelector(`[aria-label="${rotulo}"], .compacta-resumo`, { timeout: 8000 });
  let campo = await page.$(`[aria-label="${rotulo}"]`);
  if (!campo && estreito(largura)) {
    // no celular uma linha por vez fica aberta: abre a que tem este campo
    const n = Number(rotulo.match(/linha (\d+)/)?.[1] ?? 1);
    const resumo = (await page.$$(".compacta-resumo"))[n - 1];
    if (resumo) await resumo.click();
    await page.waitForSelector(`[aria-label="${rotulo}"]`, { timeout: 4000 });
    campo = await page.$(`[aria-label="${rotulo}"]`);
  }
  if (!campo) throw new Error(`campo não encontrado: ${rotulo}`);
  await campo.click({ clickCount: 3 });
  await campo.type(valor);
}

async function porNome(page, seletor, texto) {
  const alvos = await page.$$(seletor);
  for (const alvo of alvos) {
    const t = await alvo.evaluate((no) => (no.textContent ?? "").trim());
    if (t.includes(texto)) return alvo;
  }
  throw new Error(`não achei ${seletor} com "${texto}"`);
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-first-run"] });
try {
  // 1. Login e menu lateral nas 6 larguras (um deles a 2x, para nitidez)
  for (const largura of process.env.GESTAO_SO_PORTAO ? [] : LARGURAS) {
    for (const escala of largura === 1280 ? [1, 2] : [1]) {
      const sufixo = escala === 2 ? "@2x" : "";
      const page = await abrirPagina(browser, largura, escala);
      await page.goto(`${base}/entrar`, { waitUntil: "networkidle0" });
      await page.waitForSelector('input[name="usuario"]');
      await capturar(page, largura, "login", { sufixo });
      if (escala === 1) {
        await page.focus('input[name="usuario"]');
        const anel = await page.evaluate(() => {
          const estilo = getComputedStyle(document.activeElement);
          return `${estilo.outlineWidth} ${estilo.outlineStyle}`;
        });
        nota(`foco-login-${largura}`, anel.startsWith("2px solid") ? [] : [`anel: ${anel}`]);
        const marca = await page.$eval("img.gestao-logo", (img) => {
          const r = img.getBoundingClientRect();
          return { alt: img.getAttribute("alt"), largura: Math.round(r.width), altura: Math.round(r.height), natural: img.naturalWidth };
        });
        nota(
          `logo-login-${largura}`,
          marca.alt === "Loja de Pães" && marca.natural > 0 && marca.largura >= 60 ? [] : [`logo ${JSON.stringify(marca)}`],
        );
      }
      if (usuario && senha) {
        await entrar(page, usuario, senha);
        await aguardarShell(page);
        if (escala === 1) {
          // celular: logo da barra (~32 px); desktop: logo da lateral (~40 px)
          const seletorLogo = estreito(largura) ? ".gestao-topbar img.gestao-logo" : ".gestao-side img.gestao-logo";
          await page.waitForSelector(seletorLogo, { timeout: 8000 });
          const logo = await page.$eval(seletorLogo, (img) => ({
            alt: img.getAttribute("alt"),
            altura: Math.round(img.getBoundingClientRect().height),
          }));
          const esperado = estreito(largura) ? 32 : 40;
          nota(`logo-menu-${largura}`, logo.alt === "Loja de Pães" && Math.abs(logo.altura - esperado) <= 2 ? [] : [`logo ${JSON.stringify(logo)}`]);
        }
        await capturarMenu(page, largura, sufixo);
        await sair(page);
      }
      await page.close();
    }
  }

  // 2. Portão de aceite: topbar com organização e CNPJ, e a conta sem organização
  for (const largura of COM_DADOS) {
    if (usuario && senha) {
      const page = await abrirPagina(browser, largura);
      await entrar(page, usuario, senha);
      await aguardarShell(page);
      const topo = await page.$eval(".gestao-topbar", (no) => no.innerText.replace(/\s+/g, " ").trim());
      const achados = /CNPJ \d{2}\.\w{3}\.\w{3}\/\w{4}-\d{2}/.test(topo) ? [] : [`topbar sem org + CNPJ: "${topo}"`];
      await capturar(page, largura, "portao-cliente");
      nota(`portao-cliente-${largura}-topbar`, achados);
      await sair(page);
      await page.close();
    }
    if (usuarioAdmin && senhaAdmin && !adminFalhou) {
      const page = await abrirPagina(browser, largura);
      try {
        await entrar(page, usuarioAdmin, senhaAdmin);
        await page.waitForFunction(() => document.body.innerText.includes("Sua conta não opera nenhuma organização"), { timeout: 15000 });
        await capturar(page, largura, "portao-admin-plataforma");
        await sair(page);
      } catch (erro) {
        adminFalhou = true;
        // não grava a tela de erro (pode mostrar o usuário digitado); só diz o que o texto da página informa
        const texto = await page.evaluate(() => document.body.innerText.replace(/\s+/g, " ").slice(0, 160)).catch(() => "");
        nota(`portao-admin-plataforma-${largura}`, [`não chegou à tela esperada (${String(erro.message).slice(0, 60)}); a página diz: "${texto}"`]);
      }
      await page.close();
    }
  }

  // 3. Telas com dados (só no modo completo, em ambiente local)
  if (modo === "completo" && usuario && senha) {
    for (const largura of COM_DADOS) {
      const page = await abrirPagina(browser, largura);
      await entrar(page, usuario, senha);
      await aguardarShell(page);

      await page.waitForSelector(".hoje", { timeout: 15000 });
      await page.waitForFunction(() => !document.querySelector(".hoje-estado"), { timeout: 15000 });
      await capturar(page, largura, "hoje", { fullPage: true });

      await page.goto(`${base}/entradas`, { waitUntil: "networkidle0" });
      await aguardarShell(page);
      await capturar(page, largura, "entradas", { fullPage: true });
      await (await porNome(page, "button", "Nova entrada")).click();
      await page.waitForSelector('[role="dialog"]');
      await pausa(300);
      await capturar(page, largura, "entradas-como-chegou");
      await page.keyboard.press("Escape");

      await page.goto(`${base}/entradas/sem-nota`, { waitUntil: "networkidle0" });
      await aguardarShell(page);
      await (await porNome(page, "button", "Compra sem nota")).click();
      await preencher(page, "Item como comprado, linha 1", "Farinha de tigo 1 kg", largura);
      await preencher(page, "Ingrediente, linha 1", "Farinha de tigo", largura);
      await preencher(page, "Quantidade, linha 1", "3", largura);
      await page.select('[aria-label="Unidade, linha 1"]', "kg");
      await preencher(page, "Custo R$ por kg, linha 1", "9,90", largura);
      await preencher(page, "Marca, linha 1", "Renata", largura);
      // a linha 2 nasce vazia: usamos para a pendência (sem validade)
      await preencher(page, "Item como comprado, linha 2", "Azeite extra virgem", largura);
      await preencher(page, "Ingrediente, linha 2", "Azeite", largura);
      await preencher(page, "Quantidade, linha 2", "2", largura);
      await page.select('[aria-label="Unidade, linha 2"]', "l");
      await preencher(page, "Custo R$ por L, linha 2", "32", largura);
      await page.waitForSelector('[role="group"][aria-label^="Ingrediente parecido"], [role="group"][aria-label^="Item parecido"]', { timeout: 8000 }).catch(async (e) => {
        await page.screenshot({ path: join(outDir, `erro-sem-nota-${largura}.png`), fullPage: true });
        throw e;
      });
      await pausa(900);
      await capturar(page, largura, "entrada-sem-nota", { fullPage: true });

      await page.goto(`${base}/ingredientes`, { waitUntil: "networkidle0" });
      await aguardarShell(page);
      await capturar(page, largura, "ingredientes", { fullPage: true });
      await (await porNome(page, ".lista-linha, [role=button], button", "Farinha de trigo")).click();
      await page.waitForSelector('[role="dialog"]');
      await pausa(500);
      await capturar(page, largura, "ingredientes-painel");

      await sair(page);
      await page.close();
    }
  }
} finally {
  await browser.close();
}
writeFileSync(join(outDir, "capturas.md"), `| Captura | Resultado |\n|---|---|\n${linhas.join("\n")}\n`);
console.log(falhas ? `${falhas} captura(s) com achado(s)` : "todas as capturas OK");
