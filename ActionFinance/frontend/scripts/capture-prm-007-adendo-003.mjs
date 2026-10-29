import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "prm-007-adendo-003");
await mkdir(shots, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  locale: "pt-BR",
});
const page = await context.newPage();
await page.goto("https://actionfinance.actionhub.com.br/receivables", {
  waitUntil: "domcontentloaded",
  timeout: 30000,
});
await page.waitForTimeout(1500);
const url = page.url();
const title = await page.title();
await page.screenshot({
  path: join(shots, "receivables-unauthenticated.png"),
  fullPage: false,
});
await context.close();
await browser.close();

const log = {
  capturedAt: new Date().toISOString(),
  destination: "https://actionfinance.actionhub.com.br/receivables",
  finalUrlHost: new URL(url).host,
  title,
  cookiesSaved: false,
  note: "No storage state. Authenticated header not captured; human login still pending.",
};
await writeFile(join(shots, "capture-log.json"), JSON.stringify(log, null, 2), "utf8");
console.log(`captured host=${log.finalUrlHost} title=${title}`);
