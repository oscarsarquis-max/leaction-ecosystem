/**
 * Capturas do GESTAO-007D (ambiente LOCAL). Não grava em produção.
 *
 * Prepara, na demonstração local, "Farinha de trigo tipo 00" juntada a
 * "Farinha de trigo" (00 com 0 a API recusa) e o item Nita 00 no que ficou.
 * Abre o diálogo de reativar e, numa página, reativa e conclui a troca.
 *
 *   GESTAO_BASE_URL=http://127.0.0.1:8090 GESTAO_USER=demo GESTAO_PASS=... \
 *   GESTAO_OUT=docs/evidence/gestao-007d-local node scripts/capture-gestao-007d.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const base = process.env.GESTAO_BASE_URL ?? "http://127.0.0.1:8090";
const usuario = process.env.GESTAO_USER ?? "";
const senha = process.env.GESTAO_PASS ?? "";
const outDir = process.env.GESTAO_OUT ?? "docs/evidence/gestao-007d-local";
const chrome = process.env.GESTAO_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
if (!/^http:\/\/(127\.0\.0\.1|localhost)(:|\/|$)/.test(base)) throw new Error("só em ambiente local");
const requirePkg = createRequire("C:/Temp/gestao-puppeteer/package.json");
const { default: puppeteer } = await import(pathToFileURL(requirePkg.resolve("puppeteer-core")).href);

const TIPO = "Farinha de trigo tipo 00";
const GENERICA = "Farinha de trigo";
const ITEM = "Farinha de Trigo Nita 00";
const larguras = (process.env.GESTAO_LARGURAS ?? "1280,390").split(",").map(Number);
mkdirSync(outDir, { recursive: true });
const linhas = [];
let falhas = 0;
const pausa = (ms) => new Promise((r) => setTimeout(r, ms));
const estreito = (largura) => largura < 960;

function nota(arquivo, achados) {
  const resultado = achados.length ? achados.join("; ") : "OK";
  if (achados.length) falhas += 1;
  linhas.push(`| ${arquivo} | ${resultado} |`);
  console.log(arquivo, resultado);
}

async function problemas(page, largura) {
  return page.evaluate((minimo) => {
    const achados = [];
    const doc = document.documentElement;
    if (doc.scrollWidth > window.innerWidth + 1) achados.push(`rolagem horizontal ${doc.scrollWidth}>${window.innerWidth}`);
    const dialogo = document.querySelector('[aria-label="Reativar ingrediente"]') ?? document.querySelector(".gestao-modal");
    if (dialogo) {
      const r = dialogo.getBoundingClientRect();
      if (r.top < -1 || r.left < -1 || r.bottom > window.innerHeight + 1 || r.right > window.innerWidth + 1) {
        achados.push(`diálogo fora da área ${Math.round(r.top)},${Math.round(r.left)} ${Math.round(r.width)}x${Math.round(r.height)}`);
      }
      if (getComputedStyle(dialogo).position !== "fixed") achados.push("diálogo sem position fixed");
      const caixa = dialogo.querySelector(".gestao-modal-caixa");
      if (caixa) {
        const c = caixa.getBoundingClientRect();
        if (c.top < -1 || c.bottom > window.innerHeight + 1) {
          achados.push(`caixa fora da área ${Math.round(c.top)}..${Math.round(c.bottom)}`);
        }
      }
    }
    const curtos = [...document.querySelectorAll("button, select, input:not([type=checkbox]):not([type=radio])")].filter((no) => {
      if (no.classList.contains("selo-corrigido") || no.classList.contains("ing-confirmar")) return false;
      if (no.closest(".ing-lista")) return false;
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
  }, estreito(largura) ? 44 : 40);
}

async function entrar(page) {
  await page.goto(`${base}/entrar`, { waitUntil: "networkidle0" });
  const formulario = await page.$('input[name="usuario"]');
  if (formulario) {
    await page.type('input[name="usuario"]', usuario);
    await page.type('input[name="senha"]', senha);
    await page.click('button[type="submit"]');
  }
  await page.waitForSelector(".gestao-topbar", { timeout: 15000 });
  await pausa(300);
}

async function capturar(page, largura, nome) {
  const arquivo = `${nome}-${largura}.png`;
  const atual = page.viewport();
  const altura = await page.evaluate(() => document.documentElement.scrollHeight);
  await page.setViewport({ ...atual, height: Math.max(atual.height, Math.min(altura, 1600)) });
  await pausa(200);
  await page.screenshot({ path: join(outDir, arquivo) });
  await page.setViewport(atual);
  nota(arquivo, await problemas(page, largura));
}

/** Deixa o tipo 00 inativo, juntado à farinha genérica, com o item Nita no que ficou. */
async function preparar(page) {
  const resultado = await page.evaluate(
    async (tipo, generica, item) => {
      const sessao = await fetch("/api/v1/auth/sessao").then((r) => r.json());
      const csrf = sessao.csrf;
      async function api(method, rota, corpo) {
        const r = await fetch(`/api/v1${rota}`, {
          method,
          headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
          body: corpo === undefined ? undefined : JSON.stringify(corpo),
        });
        const texto = await r.text();
        let json = null;
        try {
          json = texto ? JSON.parse(texto) : null;
        } catch {
          json = texto;
        }
        return { status: r.status, json };
      }
      function exato(lista, nome) {
        return (lista ?? []).find((i) => i.nome === nome) ?? null;
      }
      const buscaTipo = await api("GET", `/ingredientes/busca?q=${encodeURIComponent(tipo)}`);
      const buscaGen = await api("GET", `/ingredientes/busca?q=${encodeURIComponent(generica)}`);
      if (buscaTipo.status !== 200 || buscaGen.status !== 200) return { ok: false, passo: "busca", buscaTipo, buscaGen };

      let tipoId = exato(buscaTipo.json.da_padaria, tipo)?.id ?? exato(buscaTipo.json.juntados, tipo)?.id ?? null;
      if (!tipoId) {
        const criado = await api("POST", "/ingredientes", {
          nome: tipo,
          unidade_base: "g",
          categoria: "Farinhas",
          apelidos: ["nita 00", "farinha de trigo nita 00"],
        });
        if (criado.status >= 300) return { ok: false, passo: "criar-tipo", criado };
        tipoId = criado.json.id;
      }
      let genericaId = exato(buscaGen.json.da_padaria, generica)?.id ?? null;
      if (!genericaId) {
        const criado = await api("POST", "/ingredientes", {
          nome: generica,
          unidade_base: "g",
          categoria: "Farinhas",
          confirmado_inexistente: true,
        });
        if (criado.status >= 300) return { ok: false, passo: "criar-generica", criado };
        genericaId = criado.json.id;
      }

      const fichaTipo = await api("GET", `/ingredientes/${tipoId}`);
      const fichaGen = await api("GET", `/ingredientes/${genericaId}`);
      if (fichaTipo.status !== 200 || fichaGen.status !== 200) return { ok: false, passo: "ficha", fichaTipo, fichaGen };
      const apelidos = fichaTipo.json.apelidos ?? [];
      if (fichaTipo.json.ativo && !apelidos.includes("farinha de trigo nita 00")) {
        const patch = await api("PATCH", `/ingredientes/${tipoId}`, {
          apelidos: [...new Set([...apelidos, "nita 00", "farinha de trigo nita 00"])],
        });
        if (patch.status >= 300) return { ok: false, passo: "apelidos", patch };
      }

      const temItem = [...(fichaTipo.json.itens_detalhe ?? []), ...(fichaGen.json.itens_detalhe ?? [])].some((i) => i.nome === item);
      if (!temItem) {
        const locais = await api("GET", "/locais");
        if (locais.status !== 200 || !locais.json[0]) return { ok: false, passo: "locais", locais };
        const destino = fichaTipo.json.ativo ? tipoId : genericaId;
        const entrada = await api("POST", "/entradas", {
          chave: "demo-007d-nita",
          data: "2026-11-05",
          local_id: locais.json[0].id,
          motivo: "compra_sem_nota",
          fornecedor: "Demonstração local",
          linhas: [
            {
              item_nome: item,
              marca: "Nita",
              unidade_controle: "massa",
              ingrediente_id: destino,
              quantidade: 1,
              unidade: "kg",
              lote_codigo: "E20261105-7D",
              valor_pago: 8.9,
            },
          ],
        });
        if (entrada.status >= 300) return { ok: false, passo: "entrada", entrada };
      }

      const aindaAtivo = (await api("GET", `/ingredientes/${tipoId}`)).json.ativo;
      if (aindaAtivo) {
        const juncao = await api("POST", "/ingredientes/juntar", { mantem_id: genericaId, remove_id: tipoId });
        if (juncao.status >= 300) return { ok: false, passo: "juntar", juncao };
      }
      return { ok: true, tipoId, genericaId };
    },
    TIPO,
    GENERICA,
    ITEM,
  );
  if (!resultado.ok) throw new Error(`preparar falhou: ${JSON.stringify(resultado)}`);
  console.log("preparado", resultado.tipoId, "→", resultado.genericaId);
}

async function abrirTroca(page) {
  await page.goto(`${base}/ingredientes`, { waitUntil: "networkidle0" });
  await page.waitForSelector("table.lista-ingredientes");
  const busca = await page.$('input[type="search"]');
  await busca.click({ clickCount: 3 });
  await busca.type("Nita 00");
  await page.waitForSelector(`button[aria-label="Ações de ${ITEM}"]`, { timeout: 10000 });
  await page.click(`button[aria-label="Ações de ${ITEM}"]`);
  await page.waitForSelector('div[role="menu"]');
  await page.evaluate(() => {
    const botao = [...document.querySelectorAll('div[role="menu"] button')].find((n) => n.textContent?.trim() === "Trocar ingrediente");
    botao?.click();
  });
  await page.waitForSelector(".gestao-modal");
}

async function abrirReativar(page) {
  const ja = await page.$(".ing-reativar");
  if (!ja) {
    const campo = await page.$('.gestao-modal input[aria-label="Novo ingrediente do item"]');
    await campo.click();
    await campo.type(TIPO);
  }
  await page.waitForSelector(".ing-reativar", { timeout: 8000 });
  await page.evaluate(() => {
    const botao = document.querySelector(".ing-reativar");
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    botao?.click();
  });
  await page.waitForSelector('[aria-label="Reativar ingrediente"]', { timeout: 8000 });
  const frase = await page.$eval('[aria-label="Reativar ingrediente"]', (el) => el.innerText);
  if (!frase.includes("foi juntado") || !frase.includes("Reativar como ingrediente separado")) {
    throw new Error(`diálogo inesperado: ${frase}`);
  }
  const motivo = await page.$('[aria-label="Reativar ingrediente"] input');
  await motivo.click();
  await motivo.type("Vou usar o tipo 00 separado");
  await pausa(200);
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ["--font-render-hinting=none"],
});

let preparou = false;
for (const largura of larguras) {
  const page = await browser.newPage();
  page.on("console", (msg) => {
    if (msg.type() === "error") console.log("console", msg.text());
  });
  page.on("pageerror", (erro) => console.log("pageerror", erro.message));
  await page.setViewport({ width: largura, height: estreito(largura) ? 844 : 900, deviceScaleFactor: 1 });
  await entrar(page);
  if (!preparou) {
    await preparar(page);
    preparou = true;
  }
  await abrirTroca(page);
  await abrirReativar(page);
  await capturar(page, largura, "reativar");
  await page.close();
}

const page = await browser.newPage();
page.on("console", (msg) => {
  if (msg.type() === "error") console.log("console", msg.text());
});
await page.setViewport({ width: 1280, height: 900, deviceScaleFactor: 1 });
await entrar(page);
await abrirTroca(page);
await abrirReativar(page);
await page.waitForSelector('[aria-label="Reativar ingrediente"] button.gestao-btn.is-primary:not([disabled])');
await page.click('[aria-label="Reativar ingrediente"] button.gestao-btn.is-primary');
await page.waitForFunction(() => !document.querySelector('[aria-label="Reativar ingrediente"]'), { timeout: 8000 });
const campo = await page.$('.gestao-modal input[aria-label="Novo ingrediente do item"]');
await campo.click({ clickCount: 3 });
await campo.type(TIPO);
await page.waitForFunction(
  (nome) =>
    [...document.querySelectorAll('[aria-label="Farinhas"] [role="option"] strong')].some((n) => n.textContent === nome),
  { timeout: 8000 },
  TIPO,
);
await page.evaluate((nome) => {
  const opcao = [...document.querySelectorAll('[aria-label="Farinhas"] [role="option"]')].find(
    (n) => n.querySelector("strong")?.textContent === nome,
  );
  opcao?.click();
}, TIPO);
await page.waitForFunction(
  (nome) => document.querySelector(".gestao-modal .ing-chip strong")?.textContent?.includes(nome),
  { timeout: 8000 },
  TIPO,
);
const motivo = await page.$(".gestao-modal label.gestao-field input");
await motivo.click();
await motivo.type("Era o tipo 00, não a farinha genérica");
await page.waitForSelector(".gestao-modal button.gestao-btn.is-primary:not([disabled])");
await page.click(".gestao-modal button.gestao-btn.is-primary");
await page.waitForFunction(() => document.body.innerText.includes("Movido para"), { timeout: 8000 });
await page.evaluate(() => {
  const input = document.querySelector('input[type="search"]');
  const definir = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
  definir.call(input, "Farinha de trigo");
  input.dispatchEvent(new Event("input", { bubbles: true }));
});
await page.waitForFunction(
  () => document.body.innerText.includes("Movido para") && document.body.innerText.includes("Farinha de Trigo Nita 00"),
  { timeout: 8000 },
);
await pausa(500);
await capturar(page, 1280, "depois");
await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
await pausa(300);
await capturar(page, 390, "depois");
await page.close();
await browser.close();
writeFileSync(
  join(outDir, "capturas.md"),
  `# Capturas locais GESTAO-007D\n\n| Arquivo | Checagem |\n|---|---|\n${linhas.join("\n")}\n`,
  "utf8",
);
if (falhas) process.exitCode = 1;
