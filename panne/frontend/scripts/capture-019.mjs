import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-019");
mkdirSync(out, { recursive: true });

const browser = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].find((path) => existsSync(path));

if (!browser) {
  console.log("Navegador headless não encontrado.");
  process.exit(0);
}

const html = pathToFileURL(resolve(out, "assistente.html")).href;

function shot(name, width, height) {
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
      html,
    ],
    { encoding: "utf8" },
  );
  console.log(dest);
}

shot("desktop", 1440, 900);
shot("notebook", 1366, 768);
shot("tablet-horizontal", 1024, 768);
shot("tablet-vertical", 768, 1024);
