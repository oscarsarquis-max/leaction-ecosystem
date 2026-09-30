import { mkdir } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "prm-006");
await mkdir(shots, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:5179";
const viewports = [
  { name: "1280", width: 1280, height: 800 },
  { name: "768", width: 768, height: 900 },
  { name: "360", width: 360, height: 800 },
];

const browser = await chromium.launch({ headless: true });
try {
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport });
    await page.goto(baseUrl, { waitUntil: "networkidle" });
    const enter = page.getByRole("button", { name: "Entrar" });
    const demo = page.getByRole("button", { name: "Entrar na demonstração" });
    if ((await enter.count()) === 0 && (await demo.count()) === 0) {
      throw new Error(`No access action at ${viewport.name}`);
    }
    const logo = await page.locator(".sign-in-brand .brand-logo").boundingBox();
    if (viewport.name === "360" && logo && Math.abs(logo.width - 144) > 2) {
      throw new Error(`360 sign-in logo width ${logo.width} is not 144`);
    }
    await page.screenshot({ path: join(shots, `access-${viewport.name}.png`), fullPage: true });
    await page.close();
  }
} finally {
  await browser.close();
}
