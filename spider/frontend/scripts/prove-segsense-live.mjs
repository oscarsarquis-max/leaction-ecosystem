import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const dir = "test-results/simulation-live";
mkdirSync(dir, { recursive: true });

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
page.setDefaultTimeout(30000);

await page.goto("http://127.0.0.1:5180/", { waitUntil: "networkidle" });
await page.getByRole("button", { name: "Simulação" }).click();
await page.waitForSelector("[data-testid=simulation-panel]");
await page.waitForFunction(() => {
  const card = document.querySelector("[data-testid=satellite-card-segsense]");
  return card && card.getAttribute("data-available") === "true";
}, null, { timeout: 20000 });
await page.screenshot({ path: `${dir}/04-simulation-segsense-available.png`, fullPage: true });
const popupPromise = context.waitForEvent("page");
await page.getByRole("link", { name: "Abrir SegSense" }).click();
const segsense = await popupPromise;
await segsense.waitForLoadState("domcontentloaded");
await segsense.getByLabel(/Descreva o contexto/i).fill("continuidade familiar com dependentes");
await segsense.getByRole("textbox", { name: /O que você quer fazer/i }).fill("entender opções ilustrativas de proteção");
await segsense.getByRole("button", { name: /Ver possibilidades ilustrativas/i }).click();
await segsense.waitForTimeout(4000);
const body = await segsense.locator("body").innerText();
await segsense.screenshot({ path: `${dir}/05-segsense-journey.png`, fullPage: true });

await page.bringToFront();
await page.getByRole("button", { name: "Monitor" }).click();
await page.getByRole("button", { name: "Atualizar" }).click();
await page.waitForTimeout(1500);
const origin = await page.locator("select").first().innerText().catch(() => "");
const rows = await page.locator("button.monitor-transaction").allInnerTexts();
const satellite = page.locator("button.monitor-transaction").filter({ hasText: /satélite|segsense|SEGSENSE/i });
if (await satellite.count()) await satellite.first().click();
await page.waitForTimeout(1000);
await page.screenshot({ path: `${dir}/06-monitor-segsense.png`, fullPage: true });
const selected = await page.locator("button.monitor-transaction[aria-pressed=true]").innerText().catch(() => "");

const report = { segsenseBody: body.slice(0, 2000), origin, rows: rows.slice(0, 8), selected };
writeFileSync(`${dir}/segsense-ui.json`, JSON.stringify(report, null, 2));
console.log(JSON.stringify(report, null, 2));
await browser.close();
