import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer-core";

const root = process.env.P76_ROOT || join(dirname(fileURLToPath(import.meta.url)), "..");
const outDir = process.env.P76_OUT || join(root, "readme", "evidence", "prompt-76");
mkdirSync(outDir, { recursive: true });

const target = process.env.P76_URL || "http://127.0.0.1:5175/acompanhar";
const catalogUrl = process.env.P76_CATALOG_URL || "https://lojadepaes.com.br/api/v1/accompaniments";
const chrome = process.env.P76_CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

const catalog = await (await fetch(catalogUrl)).json();
writeFileSync(join(outDir, "catalog.json"), JSON.stringify({
  enabled: catalog.enabled,
  source_status: catalog.source_status,
  preview: catalog.preview,
  items: catalog.items?.length,
}, null, 2));

const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: "new",
  args: ["--hide-scrollbars", "--disable-gpu"],
});

const viewports = [
  { name: "1440", width: 1440, height: 1100 },
  { name: "1024", width: 1024, height: 1100 },
  { name: "768", width: 768, height: 1100 },
  { name: "390", width: 390, height: 844 },
  { name: "320", width: 320, height: 720 },
];

const report = [];

async function measure(page) {
  return page.evaluate(() => {
    const grid = document.querySelector(".acc-grid");
    const cards = [...document.querySelectorAll(".acc-card")];
    const style = grid ? getComputedStyle(grid) : null;
    const cols = style?.gridTemplateColumns.split(" ").filter(Boolean).length || 0;
    const overflowX = document.documentElement.scrollWidth > window.innerWidth + 1;
    const pager = document.querySelector(".acc-pager");
    const next = [...document.querySelectorAll("a.acc-outbound")].slice(0, 1)[0];
    const nextBox = next?.getBoundingClientRect();
    return {
      cards: cards.length,
      columns: cols,
      gridTemplate: style?.gridTemplateColumns || "",
      overflowX,
      pagerText: pager?.textContent?.replace(/\s+/g, " ").trim() || "",
      firstCta: next?.textContent?.trim() || "",
      firstCtaHref: next?.getAttribute("href") || "",
      firstCtaVisible: Boolean(nextBox && nextBox.width > 40 && nextBox.height >= 40),
    };
  });
}

try {
  const page = await browser.newPage();
  await page.setRequestInterception(true);
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/api/v1/accompaniments") && !url.includes("for-product") && target.includes("127.0.0.1")) {
      request.respond({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(catalog),
      });
      return;
    }
    request.continue();
  });

  for (const viewport of viewports) {
    await page.setViewport({ width: viewport.width, height: viewport.height, deviceScaleFactor: 1 });
    await page.goto(target, { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForSelector(".acc-card, .shelf-status", { timeout: 20000 });
    await page.waitForFunction(() => document.querySelectorAll(".acc-card").length > 0, { timeout: 20000 }).catch(() => {});
    await page.evaluate(() => Promise.all([...document.images].map((img) => (
      img.complete ? null : new Promise((resolve) => { img.onload = img.onerror = resolve; })
    ))));
    const first = await measure(page);
    await page.screenshot({
      path: join(outDir, `acompanhar-${viewport.name}-p1.png`),
      fullPage: true,
    });
    let second = null;
    const wentNext = await page.evaluate(() => {
      const button = [...document.querySelectorAll("button")].find((item) => item.textContent.trim() === "Próxima");
      if (!button || button.disabled) {
        return false;
      }
      button.click();
      return true;
    });
    if (wentNext) {
      await page.waitForFunction(() => document.body.innerText.includes("Página 2"), { timeout: 10000 });
      second = await measure(page);
      await page.screenshot({
        path: join(outDir, `acompanhar-${viewport.name}-p2.png`),
        fullPage: false,
      });
      await page.evaluate(() => {
        const button = [...document.querySelectorAll("button")].find((item) => item.textContent.trim() === "Anterior");
        button?.click();
      });
      await page.waitForFunction(() => document.body.innerText.includes("Página 1"), { timeout: 10000 });
    }
    const lastUrl = new URL(target);
    lastUrl.searchParams.set("pagina", "3");
    await page.goto(lastUrl.toString(), { waitUntil: "domcontentloaded", timeout: 45000 });
    await page.waitForSelector(".acc-card", { timeout: 20000 });
    const last = await measure(page);
    await page.screenshot({
      path: join(outDir, `acompanhar-${viewport.name}-last.png`),
      fullPage: true,
    });
    report.push({ viewport: viewport.name, first, second, last });
  }
} finally {
  await browser.close();
}

writeFileSync(join(outDir, "grid-report.json"), JSON.stringify({ target, catalogItems: catalog.items?.length, report }, null, 2));
console.log(JSON.stringify({ target, catalogItems: catalog.items?.length, report }, null, 2));
