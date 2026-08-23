import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-021");
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

shot("visao-geral.html", "visao-geral", 1440, 900);
shot("politica.html", "politica", 1440, 900);
shot("custos.html", "custo-previsto", 1440, 900);
shot("custos.html", "custo-realizado", 1366, 768);
shot("custos.html", "lacunas-de-dados", 1280, 800);
shot("custos.html", "composicao", 1280, 800);
shot("custos.html", "previsto-versus-realizado", 1024, 768);
shot("simulador.html", "simulador-markup", 1440, 900);
shot("simulador.html", "simulador-margens", 1366, 768);
shot("simulador.html", "canais", 1024, 768);
shot("simulador.html", "revisao-e-publicacao", 1440, 900);
shot("visao-geral.html", "desktop", 1440, 900);
shot("visao-geral.html", "notebook", 1366, 768);
shot("custos.html", "tablet-horizontal", 1024, 768);
shot("simulador.html", "tablet-vertical", 768, 1024);
