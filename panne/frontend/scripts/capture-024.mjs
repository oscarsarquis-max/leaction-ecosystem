import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-024");
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

shot("quadro-antes-depois.html", "quadro-antes-depois", 1440, 900);
shot("quadro-contexto-filtros.html", "contexto-operacional", 1440, 900);
shot("quadro-contexto-filtros.html", "filtros-recolhidos-abertos", 1366, 768);
shot("quadro-visoes-vazios.html", "fluxo-lista-estacao", 1440, 900);
shot("quadro-visoes-vazios.html", "estados-vazios", 1280, 800);
shot("assistente-dominios.html", "assistente-global", 1440, 900);
shot("assistente-dominios.html", "glossario-intencoes", 1366, 768);
shot("login-viewports.html", "login-desktop", 1920, 1080);
shot("login-viewports.html", "login-notebook", 1366, 768);
shot("login-viewports.html", "login-tablet", 1024, 768);
shot("login-viewports.html", "login-celular", 390, 844);
shot("tokens-foco.html", "tokens-foco-contraste", 1280, 800);
