import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-025");
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

shot("avatar-e-gaveta.html", "avatar-desktop", 1440, 900);
shot("avatar-e-gaveta.html", "avatar-tablet", 1024, 768);
shot("avatar-e-gaveta.html", "avatar-mobile", 390, 844);
shot("dominios-e-estados.html", "dominios-demo", 1440, 900);
shot("login-demo.html", "login-demo-perfis", 1440, 900);
shot("login-demo.html", "login-demo-mobile", 390, 844);
