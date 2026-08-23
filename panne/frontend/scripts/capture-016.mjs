import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const html = resolve(here, "../../documentacao/evidencias/cursor-016/executar.html");
const outDir = resolve(here, "../../documentacao/evidencias/cursor-016");
mkdirSync(outDir, { recursive: true });

const sizes = [
  ["pesagem", 1280, 800],
  ["etapa", 1280, 800],
  ["ocorrencia-bloqueante", 1280, 800],
  ["resumo-conclusao", 1280, 800],
  ["ficha", 1280, 800],
  ["tablet-horizontal", 1024, 768],
  ["tablet-vertical", 768, 1024],
];

const candidates = [
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
];

const browser = candidates.find((path) => existsSync(path));

if (!browser) {
  console.log("Navegador headless não encontrado; HTML permanece em documentacao/evidencias/cursor-016/executar.html");
  process.exit(0);
}

for (const [name, width, height] of sizes) {
  const dest = resolve(outDir, `${name}.png`);
  const result = spawnSync(
    browser,
    [
      "--headless=new",
      "--disable-gpu",
      `--window-size=${width},${height}`,
      `--screenshot=${dest}`,
      `file:///${html.replace(/\\/g, "/")}`,
    ],
    { encoding: "utf8" },
  );
  if (result.status !== 0) console.log(result.stderr || result.stdout);
  else console.log(dest);
}
