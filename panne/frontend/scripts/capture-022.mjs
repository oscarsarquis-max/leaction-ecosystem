import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-022");
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

shot("visao-geral.html", "visao-executiva", 1440, 900);
shot("producao.html", "producao", 1440, 900);
shot("producao.html", "componentes-e-perdas", 1366, 768);
shot("custos.html", "custos-e-precos", 1440, 900);
shot("custos.html", "conformidade", 1366, 768);
shot("custos.html", "rastreabilidade", 1280, 800);
shot("custos.html", "qualidade-dos-dados", 1280, 800);
shot("producao.html", "drill-down", 1440, 900);
shot("producao.html", "comparacao", 1366, 768);
shot("visao-geral.html", "filtros", 1280, 800);
shot("visao-geral.html", "relatorio-salvo", 1024, 768);
shot("impressao.html", "snapshot", 1440, 900);
shot("impressao.html", "impressao-a4", 794, 1123);
shot("visao-geral.html", "desktop", 1440, 900);
shot("visao-geral.html", "notebook", 1366, 768);
shot("producao.html", "tablet-horizontal", 1024, 768);
shot("impressao.html", "tablet-vertical", 768, 1024);
