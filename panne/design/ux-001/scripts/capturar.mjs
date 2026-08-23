import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const lab = resolve(here, "../index.html");
const out = resolve(here, "../../../documentacao/evidencias/ux-001");
mkdirSync(out, { recursive: true });

const browser = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].find((path) => existsSync(path));

if (!browser) process.exit(0);

function shot(name, width, height, url) {
  const dest = resolve(out, `${name}.png`);
  spawnSync(browser, ["--headless=new", "--disable-gpu", `--window-size=${width},${height}`, `--screenshot=${dest}`, url], {
    encoding: "utf8",
  });
  console.log(dest);
}

const file = `file:///${lab.replace(/\\/g, "/")}`;
const sizes = [
  ["desktop", 1440, 900],
  ["notebook", 1366, 768],
  ["tablet-h", 1024, 768],
  ["tablet-v", 768, 1024],
];

shot("atual-login-desktop", 1440, 900, "http://127.0.0.1:5180/entrar");
shot("atual-login-notebook", 1366, 768, "http://127.0.0.1:5180/entrar");
shot("atual-login-tablet-h", 1024, 768, "http://127.0.0.1:5180/entrar");
shot("atual-login-tablet-v", 768, 1024, "http://127.0.0.1:5180/entrar");

const atualQuadro = resolve(here, "../../../documentacao/evidencias/cursor-015/quadro.html");
if (existsSync(atualQuadro)) {
  for (const [name, w, h] of sizes) {
    shot(`atual-quadro-${name}`, w, h, `file:///${atualQuadro.replace(/\\/g, "/")}`);
  }
}

const telas = [
  ["login", "login", ""],
  ["inicio", "inicio", "producao"],
  ["producao", "quadro", "producao"],
  ["componentes", "ingredientes", "componentes"],
  ["ingrediente", "ingrediente", "componentes"],
  ["receita", "receita", "receitas"],
  ["operacional", "operacional", "producao"],
  ["assistente", "quadro", "producao"],
  ["badges", "tokens", ""],
  ["ficha", "ficha", ""],
];

for (const dir of ["atelier", "oficina", "mesa"]) {
  for (const [label, tela, menu] of telas) {
    const ass = label === "assistente" ? "1" : "0";
    shot(`${dir}-${label}-desktop`, 1440, 900, `${file}?dir=${dir}&tela=${tela}&menu=${menu}&assistente=${ass}&papel=gestor`);
  }
  shot(`${dir}-tablet-h`, 1024, 768, `${file}?dir=${dir}&tela=quadro&menu=producao`);
  shot(`${dir}-tablet-v`, 768, 1024, `${file}?dir=${dir}&tela=ingredientes&menu=componentes`);
}

shot("comparacao-lados", 1440, 900, `${file}?tela=comparar`);
