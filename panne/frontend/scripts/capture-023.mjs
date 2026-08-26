import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-023");
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

shot("visao-estoque.html", "visao-estoque", 1440, 900);
shot("posicao-lotes.html", "saldo-lote-local", 1440, 900);
shot("posicao-lotes.html", "validade-bloqueio", 1366, 768);
shot("reserva-separacao.html", "reserva", 1440, 900);
shot("reserva-separacao.html", "separacao", 1366, 768);
shot("reserva-separacao.html", "movimento-rastreabilidade", 1280, 800);
shot("compras-inventario.html", "inventario-divergencia", 1440, 900);
shot("compras-inventario.html", "necessidade-reposicao", 1366, 768);
shot("compras-inventario.html", "requisicao", 1280, 800);
shot("compras-inventario.html", "comparacao-cotacoes", 1440, 900);
shot("compras-inventario.html", "pedido", 1366, 768);
shot("compras-inventario.html", "recebimento-parcial", 1280, 800);
shot("compras-inventario.html", "devolucao", 1024, 768);
shot("relatorios-estoque.html", "relatorios-estoque", 1440, 900);
shot("visao-estoque.html", "desktop", 1440, 900);
shot("visao-estoque.html", "notebook", 1366, 768);
shot("posicao-lotes.html", "tablet-horizontal", 1024, 768);
shot("compras-inventario.html", "tablet-vertical", 768, 1024);
