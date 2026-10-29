import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "nova-interface");
await mkdir(shots, { recursive: true });
const origin = "https://actionfinance.actionhub.com.br";
const browser = await chromium.launch({ headless: true });

async function shot(name, path, width) {
  const page = await browser.newPage({ viewport: { width, height: 800 } });
  const response = await page.goto(`${origin}${path}`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(2500);
  const url = page.url();
  await page.screenshot({ path: join(shots, `${name}-${width}.png`) });
  const returnPath = await page.evaluate(() => sessionStorage.getItem("af.returnPath")).catch(() => null);
  await page.close();
  return { name, width, status: response?.status(), url, returnPath };
}

const notes = [];
notes.push(await shot("public-deeplink-pay", "/pay-receipts", 1280));
notes.push(await shot("public-deeplink-pay", "/pay-receipts", 360));
notes.push(await shot("public-oauth-start", "/oauth2/authorization/actionfinance", 1280));
await browser.close();
for (const row of notes) {
  console.log(JSON.stringify(row));
}
if (!notes.some((row) => String(row.url).includes("amazoncognito.com"))) {
  throw new Error("Public unauthenticated entry did not reach the Finance Hosted UI.");
}
