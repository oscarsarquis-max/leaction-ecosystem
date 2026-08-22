import { spawnSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const html = resolve(here, "../../documentacao/evidencias/cursor-015/quadro.html");
const outDir = resolve(here, "../../documentacao/evidencias/cursor-015");
mkdirSync(outDir, { recursive: true });

const sizes = [
  ["desktop-amplo", 1440, 900],
  ["notebook", 1366, 768],
  ["tablet-horizontal", 1024, 768],
  ["tablet-vertical", 768, 1024],
];

const candidates = [
  "C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe",
  "C:\\\\Program Files (x86)\\\\Microsoft\\\\Edge\\\\Application\\\\msedge.exe",
];

const browser = candidates.find((path) => {
  try {
    return spawnSync("cmd", ["/c", `if exist "${path}" echo yes`], { encoding: "utf8" }).stdout.includes("yes");
  } catch {
    return false;
  }
});

if (!browser) {
  console.log("Navegador headless não encontrado; HTML de evidência permanece em documentacao/evidencias/cursor-015/quadro.html");
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
  if (result.status !== 0) {
    console.log(result.stderr || result.stdout);
  } else {
    console.log(dest);
  }
}
