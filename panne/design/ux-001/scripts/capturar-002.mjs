import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const lab = resolve(here, "../index.html");
const out = resolve(here, "../../../documentacao/evidencias/ux-002");
mkdirSync(out, { recursive: true });
const browser = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].find((path) => existsSync(path));
if (!browser) process.exit(0);

function shot(name, width, height, query) {
  const dest = resolve(out, `${name}.png`);
  const url = `file:///${lab.replace(/\\/g, "/")}?${query}`;
  spawnSync(browser, ["--headless=new", "--disable-gpu", `--window-size=${width},${height}`, `--screenshot=${dest}`, url], {
    encoding: "utf8",
  });
  console.log(dest);
}

const telas = [
  ["login", "login", ""],
  ["inicio", "inicio", "producao"],
  ["quadro", "quadro", "producao"],
  ["submenu-componentes", "inicio", "componentes"],
  ["ingredientes", "ingredientes", "componentes"],
  ["ingrediente", "ingrediente", "componentes"],
  ["receita", "receita", "receitas"],
  ["operacional", "operacional", "producao"],
  ["assistente", "quadro", "producao"],
  ["vazio", "quadro", "producao"],
  ["carregando", "quadro", "producao"],
  ["conflito", "quadro", "producao"],
  ["erro", "quadro", "producao"],
  ["bloqueio", "quadro", "producao"],
  ["ficha", "ficha", ""],
  ["tokens", "tokens", ""],
];

const estados = { vazio: "vazio", carregando: "carregando", conflito: "conflito", erro: "erro", bloqueio: "bloqueio" };

for (const [label, tela, menu] of telas) {
  const estado = estados[label] || "ok";
  const ass = label === "assistente" || label === "ingrediente" ? "1" : "0";
  const guia = label === "ingrediente" ? "ingrediente" : "primeiros";
  shot(`aprovada-${label}-desktop`, 1440, 900, `dir=aprovada&tela=${tela}&menu=${menu}&estado=${estado}&assistente=${ass}&guia=${guia}`);
}

shot("aprovada-notebook", 1366, 768, "dir=aprovada&tela=quadro&menu=producao");
shot("aprovada-tablet-h", 1024, 768, "dir=aprovada&tela=operacional&menu=producao");
shot("aprovada-tablet-v", 768, 1024, "dir=aprovada&tela=ingredientes&menu=componentes");
shot("aprovada-monitor-quadro", 1920, 1080, "dir=aprovada&tela=quadro&menu=producao&papel=leitor");
shot("historico-oficina-quadro", 1440, 900, "dir=oficina&tela=quadro&menu=producao");
shot("historico-atelier-quadro", 1440, 900, "dir=atelier&tela=quadro&menu=producao");
shot("comparacao", 1440, 900, "dir=aprovada&tela=comparar");
