import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const dir = "test-results/simulation-tab";
mkdirSync(dir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(20000);
await page.goto("http://127.0.0.1:5180/", { waitUntil: "networkidle" });
await page.getByRole("button", { name: "Simulação" }).click();
await page.waitForSelector("[data-testid=simulation-panel]");
await page.waitForTimeout(800);
await page.screenshot({ path: `${dir}/01-desktop.png`, fullPage: true });
await page.setViewportSize({ width: 390, height: 844 });
await page.waitForTimeout(400);
await page.screenshot({ path: `${dir}/02-narrow.png`, fullPage: true });

const nav = await page.locator("nav[aria-label='Navegação do Monitor'] button").allTextContents();
const cards = await page.locator(".satellite-card").count();
const lines = await page.locator(".scenario-line").count();
const enabled = await page.locator(".scenario-line button.cta:enabled").allTextContents();
const segsense = await page.getByTestId("satellite-card-segsense").innerText();
const bank = await page.getByTestId("satellite-card-spiderbank").innerText();
console.log(
  JSON.stringify({ nav, cards, lines, enabled, segsense, bank }, null, 2),
);
await browser.close();
