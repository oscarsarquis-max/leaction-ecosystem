import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const dir = "test-results/simulation-tab";
mkdirSync(dir, { recursive: true });
const id = "exec-503d6a85-0d18-4b99-a5ac-b0dea4151b61";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
page.setDefaultTimeout(20000);
await page.goto("http://127.0.0.1:5180/", { waitUntil: "networkidle" });
await page.getByRole("button", { name: "Atualizar" }).click();
await page.waitForTimeout(1200);
const row = page.locator("button.monitor-transaction").filter({ hasText: id.slice(0, 8) });
if (await row.count()) {
  await row.first().click();
} else {
  await page.getByPlaceholder("Objetivo, origem ou id").fill(id);
  await page.waitForTimeout(400);
  const match = page.locator("#transaction-search-results button").first();
  if (await match.count()) await match.click();
}
await page.waitForTimeout(800);
await page.screenshot({ path: `${dir}/03-monitor-retry.png`, fullPage: true });
const selected = await page.locator("button.monitor-transaction[aria-pressed=true]").innerText().catch(() => "");
console.log(JSON.stringify({ selected }, null, 2));
await browser.close();
