import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../documentacao/evidencias/cursor-017");
mkdirSync(out, { recursive: true });

const browser = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].find((path) => existsSync(path));

if (!browser) {
  console.log("Navegador headless não encontrado.");
  process.exit(0);
}

function shot(name, width, height, url) {
  const dest = resolve(out, `${name}.png`);
  spawnSync(
    browser,
    [
      "--headless=new",
      "--disable-gpu",
      "--hide-scrollbars",
      `--window-size=${width},${height}`,
      `--screenshot=${dest}`,
      url,
    ],
    { encoding: "utf8" },
  );
  console.log(dest);
}

const base = "http://127.0.0.1:5180";
shot("login-desktop", 1440, 900, `${base}/entrar`);
shot("login-notebook", 1366, 768, `${base}/entrar`);
shot("login-tablet-h", 1024, 768, `${base}/entrar`);
shot("login-tablet-v", 768, 1024, `${base}/entrar`);
