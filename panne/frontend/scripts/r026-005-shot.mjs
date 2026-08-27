import { chromium } from "playwright";
import path from "path";

const out = process.argv[2];
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto("http://127.0.0.1:5180/entrar", { waitUntil: "networkidle" });
await page.waitForSelector(".login-center__header img", { timeout: 15000 });
await page.screenshot({ path: path.join(out, "R026-005-entrar-desktop.png"), fullPage: true });
const box = page.locator(".login-center");
await box.screenshot({ path: path.join(out, "R026-005-caixa-cabecalho.png") });
await page.getByRole("button", { name: /Entrar/ }).first().focus();
await box.screenshot({ path: path.join(out, "R026-005-foco-entrar.png") });
await page.getByRole("button", { name: "Ajuda para entrar", exact: true }).click();
await page.getByRole("heading", { name: "Ajuda para entrar" }).waitFor();
await page.screenshot({ path: path.join(out, "R026-005-ajuda-aberta.png"), fullPage: true });
await page.setViewportSize({ width: 390, height: 844 });
await page.goto("http://127.0.0.1:5180/entrar", { waitUntil: "networkidle" });
await page.waitForSelector(".login-center__header img");
await page.screenshot({ path: path.join(out, "R026-005-entrar-mobile.png"), fullPage: true });
await page.addStyleTag({ content: "html { font-size: 125% !important; }" });
await page.screenshot({ path: path.join(out, "R026-005-entrar-texto-maior.png"), fullPage: true });
// narrow window mid size
await page.setViewportSize({ width: 900, height: 700 });
await page.goto("http://127.0.0.1:5180/entrar", { waitUntil: "networkidle" });
await page.waitForSelector(".login-center__header img");
await page.screenshot({ path: path.join(out, "R026-005-entrar-estreito.png"), fullPage: true });
await browser.close();
console.log("OK");
