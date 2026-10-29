import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(process.env.P77_PUPPETEER || join(process.env.TEMP || "/tmp", "p76-puppeteer", "package.json"));
const { default: puppeteer } = await import(pathToFileURL(require.resolve("puppeteer-core")).href);

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = process.env.P83_OUT || join(root, "readme", "evidence", "prompt-83", "prod");
mkdirSync(outDir, { recursive: true });
const chrome = process.env.P77_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const origin = "https://lojadepaes.com.br";
const report = { origin, pages: [], images: [] };

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

async function shot(page, name, fullPage = true) {
  const path = join(outDir, name);
  await page.screenshot({ path, fullPage });
  report.images.push(name);
}

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: "new",
  args: ["--hide-scrollbars", "--disable-gpu", "--no-first-run"],
});

try {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}/`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForSelector("button.gigio-launch", { timeout: 20000 });
  await page.click("button.gigio-launch");
  await page.waitForSelector("textarea[aria-label='Mensagem para o Gigio'], .gigio-panel, .gigio-form", { timeout: 15000 });
  const gigio = await page.evaluate(() => ({
    launch: Boolean(document.querySelector("button.gigio-launch")),
    textarea: Boolean(document.querySelector("textarea[aria-label='Mensagem para o Gigio']")),
    sourcesCss: Boolean(document.querySelector("style, link")) && Boolean(document.querySelector(".gigio-form, .gigio-panel, [class*='gigio']")),
    welcome: (document.body.innerText || "").includes("Gigio"),
  }));
  report.pages.push({ name: "gigio-open", ...gigio });
  await shot(page, "gigio-open-1440.png", false);
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 });
  await shot(page, "gigio-open-390.png", false);

  const pages = [
    ["vitrine-pork-cta-1440", "/acompanhar?cats=vinhos&mesa=porco&ids=MLB38120577,MLB29767613,MLB72723513", 1440, 1100],
    ["vitrine-pork-cta-390", "/acompanhar?cats=vinhos&mesa=porco&ids=MLB38120577,MLB29767613,MLB72723513", 390, 844],
    ["vitrine-cheese-cta-1440", "/acompanhar?cats=vinhos,queijos&ids=MLB38120577,MLB29767613,MLB72723513,MLB48276443,MLB27911650,MLB67488520", 1440, 1100],
    ["vitrine-preserved-1440", "/acompanhar?cats=vinhos&mesa=leitao,salada", 1440, 1100],
    ["vitrine-preserved-390", "/acompanhar?cats=vinhos&mesa=leitao,salada", 390, 844],
    ["vitrine-geral-1440", "/acompanhar", 1440, 1100],
  ];
  for (const [name, path, width, height] of pages) {
    await page.setViewport({ width, height, deviceScaleFactor: 1 });
    await page.goto(`${origin}${path}`, { waitUntil: "domcontentloaded", timeout: 45000 });
    await waitVitrine(page);
    const info = await page.evaluate(() => ({
      url: location.href,
      title: document.querySelector("h1")?.textContent?.trim() || "",
      cards: document.querySelectorAll(".acc-card").length,
      names: [...document.querySelectorAll(".acc-card h3")].map((el) => el.textContent.trim()),
      columns: document.querySelector(".acc-grid")
        ? getComputedStyle(document.querySelector(".acc-grid")).gridTemplateColumns.split(" ").filter(Boolean).length
        : 0,
      objectFit: [...document.querySelectorAll(".acc-card-media img")].slice(0, 3).map((img) => getComputedStyle(img).objectFit),
    }));
    await shot(page, `${name}.png`, true);
    report.pages.push({ name, ...info });
  }

  await page.setViewport({ width: 1440, height: 1100, deviceScaleFactor: 1 });
  await page.goto(`${origin}/pedido/novo`, { waitUntil: "domcontentloaded", timeout: 45000 });
  const review = await page.evaluate(() => ({
    heading: document.querySelector("h1")?.textContent?.trim() || "",
    submit: [...document.querySelectorAll("button, input[type='submit']")].map((el) => el.textContent.trim()).slice(0, 8),
    sent: document.body.innerText.includes("enviado"),
  }));
  await shot(page, "order-review-no-submit.png", true);
  report.pages.push({ name: "order-review", submitted: false, ...review });
} finally {
  await browser.close();
}

writeFileSync(join(outDir, "ui-report.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
