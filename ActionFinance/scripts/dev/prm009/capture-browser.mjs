import { createRequire } from "node:module";
const require = createRequire("c:/Projetos/spider/frontend/package.json");
const { chromium } = require("playwright");
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const evidence = "c:/Projetos/ActionFinance/documents/reviews/evidence/prm-009-continuidade-001/captures";
mkdirSync(evidence, { recursive: true });
const tokens = Object.fromEntries(
  readFileSync("c:/Projetos/ActionFinance/.local/demo-tokens.env", "utf8")
    .split(/\r?\n/)
    .filter((l) => l.includes("="))
    .map((l) => {
      const i = l.indexOf("=");
      return [l.slice(0, i).trim(), l.slice(i + 1)];
    })
);
const token = tokens.ACTIONFINANCE_DEMO_TOKEN_OPERATOR_A;
const browser = await chromium.launch({ headless: true });
const notes = [];

async function shot(page, name) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  await page.screenshot({ path: join(evidence, `${name}-viewport.png`), fullPage: false });
  await page.screenshot({ path: join(evidence, `${name}-full.png`), fullPage: true });
  notes.push({ name, overflow, url: page.url(), title: await page.title() });
}

const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const page = await context.newPage();
await page.goto("http://127.0.0.1:5179/", { waitUntil: "networkidle" });
await page.getByLabel("Token local").fill(token);
await page.getByRole("button", { name: "Entrar na demonstração" }).click();
await page.getByRole("button", { name: "Recebimentos do Pay" }).click();
await page.getByRole("heading", { name: "Recebimentos do Pay" }).waitFor();
await shot(page, "af-1280");
await page.setViewportSize({ width: 768, height: 900 });
await shot(page, "af-768");
await page.setViewportSize({ width: 360, height: 740 });
await shot(page, "af-360");
await page.setViewportSize({ width: 1280, height: 800 });
const popupPromise = page.waitForEvent("popup", { timeout: 15000 }).catch(() => null);
await page.getByRole("button", { name: "Sincronizar recebimentos" }).click();
await page.getByText(/Sincronização concluída|Concluído sem novidades|parcial|indisponível/i).waitFor({ timeout: 20000 });
await shot(page, "af-after-sync-1280");
const link = page.getByRole("link", { name: "Ver execução na Spider" });
await link.waitFor({ timeout: 10000 });
const href = await link.getAttribute("href");
await link.click();
const monitor = (await popupPromise) || (await context.newPage());
if (!popupPromise) {
  await monitor.goto(href, { waitUntil: "networkidle" });
} else {
  await monitor.waitForLoadState("networkidle");
}
await monitor.waitForTimeout(1500);
await shot(monitor, "spider-1280");
await monitor.setViewportSize({ width: 768, height: 900 });
await shot(monitor, "spider-768");
await monitor.setViewportSize({ width: 360, height: 740 });
await shot(monitor, "spider-360");
const bodyText = await monitor.locator("body").innerText();
notes.push({
  monitorHref: href,
  hasRequest: /solicit|SATELLITE_REQUEST|Finance solicit/i.test(bodyText),
  hasCompany: /autorizad|SATELLITE_COMPANY/i.test(bodyText),
  hasCapability: /capacidade|LIST_PAYMENT|CAPABILITY_DISPATCHED/i.test(bodyText),
  hasProvider: /provider|ActionHub|OUTBOUND/i.test(bodyText),
  hasSecret: /prm009-hub-provider|prm009-edge-forward/i.test(bodyText),
});
writeFileSync(join(evidence, "notes.json"), JSON.stringify(notes, null, 2));
await browser.close();
console.log(`CAPTURES ${evidence}`);
console.log(`MONITOR ${href}`);
console.log(`OVERFLOW ${notes.filter((n) => n.overflow).map((n) => n.name).join(",") || "none"}`);
console.log(`SECRETS_ON_MONITOR ${notes.at(-1).hasSecret}`);
