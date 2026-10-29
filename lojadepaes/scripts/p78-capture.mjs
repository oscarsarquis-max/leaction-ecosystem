import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"));
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(root, "readme", "evidence", "prompt-78", "prod");
mkdirSync(outDir, { recursive: true });
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const origin = "https://lojadepaes.com.br";
const report = { pages: [] };

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: "new",
  args: ["--hide-scrollbars", "--disable-gpu"],
});

async function waitReady(page) {
  await page.waitForFunction(
    () => !document.body.innerText.includes("Carregando a seleção") && document.querySelectorAll(".acc-card").length > 0,
    { timeout: 45000 },
  );
}

try {
  const page = await browser.newPage();
  for (const [name, path, width, height] of [
    ["geral-1440", "/acompanhar", 1440, 1100],
    ["vinhos-1440", "/acompanhar?cats=vinhos", 1440, 1100],
    ["vinhos-390", "/acompanhar?cats=vinhos", 390, 844],
    ["frios-1440", "/acompanhar?cats=frios", 1440, 1100],
  ]) {
    await page.setViewport({ width, height, deviceScaleFactor: 1 });
    await page.goto(`${origin}${path}`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await waitReady(page);
    const info = await page.evaluate(() => ({
      title: document.querySelector("h1")?.textContent?.trim(),
      names: [...document.querySelectorAll(".acc-card h3")].map((el) => el.textContent.trim()),
      columns: getComputedStyle(document.querySelector(".acc-grid")).gridTemplateColumns.split(" ").filter(Boolean).length,
    }));
    await page.screenshot({ path: join(outDir, `${name}.png`), fullPage: true });
    report.pages.push({ name, path, ...info });
  }
} finally {
  await browser.close();
}

writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
