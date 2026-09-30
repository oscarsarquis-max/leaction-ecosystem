import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "cor-001");
await mkdir(shots, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:5179/";
const browser = await chromium.launch({ headless: true });
const findings = [];

async function capture(name, width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.waitForSelector("h1");
  const overflow = await page.evaluate(() => {
    const doc = document.documentElement;
    return {
      scrollWidth: doc.scrollWidth,
      clientWidth: doc.clientWidth,
      overflowX: doc.scrollWidth > doc.clientWidth + 1,
    };
  });
  findings.push({ name, width, height, overflow });
  await page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });

  await page.keyboard.press("Tab");
  const focused = await page.evaluate(() => document.activeElement?.textContent?.trim() ?? "");
  findings.push({ name: `${name}-tab`, focused });
  if (focused.includes("Verificar novamente")) {
    await page.keyboard.press("Enter");
    await page.waitForTimeout(400);
  }

  await page.route("**/api/v1/system/info", (route) => route.abort());
  await page.getByRole("button", { name: "Verificar novamente" }).click();
  await page.getByText("API local indisponível. Tente verificar novamente.").waitFor();
  await page.screenshot({ path: join(shots, `${name}-api-fail.png`), fullPage: true });
  await page.unroute("**/api/v1/system/info");
  await page.getByRole("button", { name: "Verificar novamente" }).click();
  await page.getByText(/API local (disponível|indisponível)/).waitFor();
  await page.screenshot({ path: join(shots, `${name}-api-retry.png`), fullPage: true });
  const body = await page.locator("body").innerText();
  if (/Bearer|ACTIONFINANCE_DEMO_TOKEN|bootstrap password/i.test(body)) {
    throw new Error("Page leaked a secret-looking value.");
  }
  await page.close();
}

try {
  await capture("desktop-1280", 1280, 800);
  await capture("mobile-360", 360, 800);
  console.log(JSON.stringify({ ok: true, baseUrl, findings, shots }, null, 2));
} finally {
  await browser.close();
}
