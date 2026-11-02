/**
 * Capturas do login e da tela Hoje (1280 e 390 px) com checagens no padrão 108A da Loja:
 * sem rolagem horizontal, barra numa linha só, controles com a altura mínima, anel de foco.
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=... GESTAO_PASS=... \
 *   GESTAO_OUT=docs/evidence/gestao-002 node scripts/capture-evidence.mjs
 *
 * A senha vem só do ambiente do processo; nada dela é gravado.
 * Requer puppeteer-core (GESTAO_PUPPETEER = caminho do package.json que o contém) e o Chrome.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-002";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const requirePkg = createRequire(
  process.env.GESTAO_PUPPETEER ?? join(process.env.TEMP ?? "/tmp", "gestao-puppeteer", "package.json"),
);
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

mkdirSync(outDir, { recursive: true });
const linhas = [];

function nota(arquivo, resultado) {
  linhas.push(`| ${arquivo} | ${resultado} |`);
  console.log(arquivo, resultado);
}

async function problemas(page, largura) {
  return page.evaluate((minimo) => {
    const achados = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > window.innerWidth + 1) {
      achados.push(`rolagem horizontal ${doc.scrollWidth}>${window.innerWidth}`);
    }
    const barra = document.querySelector(".gestao-topbar");
    if (barra) {
      const lead = barra.querySelector(".gestao-topbar-lead")?.getBoundingClientRect();
      const acoes = barra.querySelector(".gestao-topbar-actions")?.getBoundingClientRect();
      if (lead && acoes && (Math.abs(lead.top + lead.height / 2 - (acoes.top + acoes.height / 2)) > 4 || acoes.top >= lead.bottom)) {
        achados.push("trilha e ações quebraram de linha");
      }
      if (getComputedStyle(barra).borderBottomWidth !== "1px") achados.push("borda inferior ausente");
    }
    const curtos = [...document.querySelectorAll("button, a.nl, select, input")].filter((no) => {
      const r = no.getBoundingClientRect();
      return r.width > 1 && r.height > 1 && r.height + 0.5 < minimo;
    });
    if (curtos.length) {
      achados.push(`controle abaixo de ${minimo}px: ${curtos.map((no) => `${no.tagName}.${no.className}`.slice(0, 40)).join(", ")}`);
    }
    return achados;
  }, largura < 960 ? 44 : 36);
}

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--no-first-run"] });
try {
  for (const largura of [1280, 390]) {
    const altura = largura >= 960 ? 900 : 844;
    const page = await browser.newPage();
    await page.setViewport({ width: largura, height: altura, deviceScaleFactor: 1 });

    await page.goto(`${base}/entrar`, { waitUntil: "networkidle0" });
    await page.waitForSelector('input[name="usuario"]');
    let arquivo = `login-${largura}.png`;
    await page.screenshot({ path: join(outDir, arquivo) });
    const achadosLogin = await problemas(page, largura);
    nota(arquivo, achadosLogin.length ? achadosLogin.join("; ") : "OK");

    // foco visível no campo de usuário
    await page.focus('input[name="usuario"]');
    const anel = await page.evaluate(() => {
      const estilo = getComputedStyle(document.activeElement);
      return `${estilo.outlineWidth} ${estilo.outlineStyle}`;
    });
    nota(`foco-login-${largura}`, anel.startsWith("2px solid") ? "OK (anel de 2 px)" : `anel: ${anel}`);

    // senha errada: mensagem
    await page.type('input[name="usuario"]', "usuario-inexistente-captura");
    await page.type('input[name="senha"]', "senha-qualquer-invalida");
    await page.click('button[type="submit"]');
    await page.waitForSelector('[role="alert"]', { timeout: 8000 });
    arquivo = `login-erro-${largura}.png`;
    await page.screenshot({ path: join(outDir, arquivo) });
    const achadosErro = await problemas(page, largura);
    nota(arquivo, achadosErro.length ? achadosErro.join("; ") : "OK");

    if (usuario && senha) {
      await page.goto(`${base}/entrar`, { waitUntil: "networkidle0" });
      await page.waitForSelector('input[name="usuario"]');
      await page.type('input[name="usuario"]', usuario);
      await page.type('input[name="senha"]', senha);
      await page.click('button[type="submit"]');
      await page.waitForSelector(".hoje", { timeout: 15000 });
      await page.waitForFunction(
        () => !document.querySelector(".hoje-estado") && document.querySelector(".hoje-resumo, .hoje-vazio"),
        { timeout: 15000 },
      );
      arquivo = `hoje-${largura}.png`;
      await page.screenshot({ path: join(outDir, arquivo), fullPage: true });
      const achadosHoje = await problemas(page, largura);
      nota(arquivo, achadosHoje.length ? achadosHoje.join("; ") : "OK");
      if (largura < 960) {
        await page.click(".gestao-menu-button");
        await page.waitForSelector(".gestao-side.is-open");
        arquivo = `menu-${largura}.png`;
        await page.screenshot({ path: join(outDir, arquivo) });
        nota(arquivo, "gaveta aberta (menu, 'em breve' sem link)");
      }
      // sai, para não deixar sessão aberta
      await page.evaluate(async () => {
        const sessao = await (await fetch("/api/v1/auth/sessao?rotacionar=true", { credentials: "same-origin" })).json();
        await fetch("/api/v1/auth/sair", {
          method: "POST",
          credentials: "same-origin",
          headers: { "X-CSRF-Token": sessao.csrf },
        });
      });
    }
    await page.close();
  }
} finally {
  await browser.close();
}
writeFileSync(join(outDir, "capturas.md"), `| Captura | Resultado |\n|---|---|\n${linhas.join("\n")}\n`);
