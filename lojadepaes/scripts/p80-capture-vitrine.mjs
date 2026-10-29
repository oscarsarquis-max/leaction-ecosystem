import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"));
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = join(root, "readme", "evidence", "prompt-80", "prod");
mkdirSync(outDir, { recursive: true });
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const origin = "https://lojadepaes.com.br";
const report = { origin, pages: [] };

async function waitVitrine(page) {
  await page.waitForFunction(
    () => {
      const loading = document.body.innerText.includes("Carregando a seleção");
      const cards = document.querySelectorAll(".acc-card").length;
      const empty = document.body.innerText.includes("Não há complementos disponíveis para essa sugestão");
      return !loading && (cards > 0 || empty);
    },
    { timeout: 45000 },
  );
  await page.evaluate(() =>
    Promise.all(
      [...document.images].map((img) =>
        img.complete
          ? null
          : new Promise((resolve) => {
              img.onload = img.onerror = resolve;
            }),
      ),
    ),
  );
}

async function measure(page) {
  return page.evaluate(() => {
    const grid = document.querySelector(".acc-grid");
    const cards = [...document.querySelectorAll(".acc-card")];
    const h2 = [...document.querySelectorAll("h2")].map((el) => el.textContent.trim());
    const h3 = [...document.querySelectorAll(".acc-card h3")].map((el) => el.textContent.trim());
    const photos = [...document.querySelectorAll(".acc-card-media img")].map((img) => {
      const box = img.getBoundingClientRect();
      const wrap = img.parentElement ? getComputedStyle(img.parentElement) : null;
      const computed = getComputedStyle(img);
      return {
        alt: img.alt,
        src: (img.currentSrc || img.src).slice(0, 160),
        naturalW: img.naturalWidth,
        naturalH: img.naturalHeight,
        boxW: Math.round(box.width),
        boxH: Math.round(box.height),
        fit: computed.objectFit,
        width: computed.width,
        height: computed.height,
        maxH: computed.maxHeight,
        wrapPad: wrap?.padding || "",
        wrapRatio: wrap?.aspectRatio || "",
        overflow: wrap?.overflow || "",
      };
    });
    return {
      url: location.href,
      title: document.querySelector("h1")?.textContent?.trim() || "",
      h2,
      names: h3,
      cards: cards.length,
      columns: grid ? getComputedStyle(grid).gridTemplateColumns.split(" ").filter(Boolean).length : 0,
      context: document.querySelector(".acc-context")?.innerText?.replace(/\s+/g, " ").trim() || "",
      prices: [...document.querySelectorAll(".acc-price")].map((el) => el.textContent.trim()),
      naMercado: document.body.innerText.includes("na Mercado Livre"),
      photos,
    };
  });
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: "new",
  args: ["--hide-scrollbars", "--disable-gpu", "--no-first-run"],
});

try {
  const page = await browser.newPage();
  const shots = [
    ["vitrine-meal-1440", "/acompanhar?cats=vinhos,azeites,queijos&mesa=leitao,salada", 1440, 1100],
    ["vitrine-wine-1440", "/acompanhar?cats=vinhos&mesa=leitao,salada", 1440, 1100],
    ["garrafas-1440", "/acompanhar?cats=vinhos&mesa=leitao,salada", 1440, 1100],
    ["garrafas-1024", "/acompanhar?cats=vinhos&mesa=leitao,salada", 1024, 1100],
    ["garrafas-768", "/acompanhar?cats=vinhos&mesa=leitao,salada", 768, 1100],
    ["garrafas-390", "/acompanhar?cats=vinhos&mesa=leitao,salada", 390, 844],
    ["garrafas-320", "/acompanhar?cats=vinhos&mesa=leitao,salada", 320, 720],
    ["geral-1440", "/acompanhar", 1440, 1100],
    ["queijos-1440", "/acompanhar?cats=queijos", 1440, 1100],
    ["azeites-1440", "/acompanhar?cats=azeites", 1440, 1100],
    ["frios-1440", "/acompanhar?cats=frios", 1440, 1100],
  ];
  for (const [name, path, width, height] of shots) {
    await page.setViewport({ width, height, deviceScaleFactor: 1 });
    await page.goto(`${origin}${path}`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await waitVitrine(page);
    const info = await measure(page);
    await page.screenshot({ path: join(outDir, `${name}.png`), fullPage: true });
    report.pages.push({ name, ...info });
  }
} finally {
  await browser.close();
}

writeFileSync(join(outDir, "vitrine-report.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
