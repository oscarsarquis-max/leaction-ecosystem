import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-020");
mkdirSync(out, { recursive: true });

const browser = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].find((path) => existsSync(path));

if (!browser) {
  console.log("Navegador headless não encontrado.");
  process.exit(0);
}

function shot(file, name, width, height) {
  const dest = resolve(out, `${name}.png`);
  spawnSync(
    browser,
    [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      "--allow-file-access-from-files",
      `--window-size=${width},${height}`,
      `--screenshot=${dest}`,
      pathToFileURL(resolve(out, file)).href,
    ],
    { encoding: "utf8" },
  );
  console.log(dest);
}

shot("visao-geral.html", "visao-geral-desktop", 1440, 900);
shot("visao-geral.html", "visao-geral-notebook", 1366, 768);
shot("dossie.html", "criacao-guiada", 1440, 900);
shot("dossie.html", "aplicabilidade-incompleta", 1366, 768);
shot("dossie.html", "avaliacao-achados", 1280, 800);
shot("dossie.html", "tabela-nutricional", 1280, 800);
shot("dossie.html", "lupa", 1024, 768);
shot("dossie.html", "ingredientes-advertencias", 1024, 768);
shot("dossie.html", "candidato", 1440, 900);
shot("dossie.html", "comparacao", 1366, 768);
shot("impressao.html", "impressao-a4", 794, 1123);
shot("dossie.html", "desktop", 1440, 900);
shot("dossie.html", "notebook", 1366, 768);
shot("dossie.html", "tablet-horizontal", 1024, 768);
shot("dossie.html", "tablet-vertical", 768, 1024);
