import { chromium } from "playwright";
import path from "path";
const out = process.argv[2];
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto("http://127.0.0.1:5180/entrar", { waitUntil: "networkidle" });
await page.waitForSelector(".login-center__header img");
const metrics = await page.evaluate(() => {
  const card = document.querySelector(".login-center");
  const header = document.querySelector(".login-center__header");
  const img = document.querySelector(".login-center__brand");
  const cr = card.getBoundingClientRect();
  const hr = header.getBoundingClientRect();
  const ir = img.getBoundingClientRect();
  const cs = getComputedStyle(card);
  return {
    card: { w: cr.width, h: cr.height, x: cr.x, y: cr.y, radius: cs.borderRadius, overflow: cs.overflow, pad: cs.padding },
    header: { w: hr.width, h: hr.height, x: hr.x, y: hr.y, topGap: hr.top - cr.top, leftGap: hr.left - cr.left, rightGap: cr.right - hr.right },
    img: { w: ir.width, h: ir.height, x: ir.x, y: ir.y, topGap: ir.top - hr.top, leftGap: ir.left - hr.left, rightGap: hr.right - ir.right, bottomGap: hr.bottom - ir.bottom },
  };
});
console.log(JSON.stringify(metrics, null, 2));
await page.locator(".login-center").screenshot({ path: path.join(out, "R026-005-caixa-cabecalho.png") });
await page.screenshot({ path: path.join(out, "R026-005-entrar-desktop.png"), fullPage: true });
await page.setViewportSize({ width: 390, height: 844 });
await page.goto("http://127.0.0.1:5180/entrar", { waitUntil: "networkidle" });
await page.screenshot({ path: path.join(out, "R026-005-entrar-mobile.png"), fullPage: true });
await browser.close();
