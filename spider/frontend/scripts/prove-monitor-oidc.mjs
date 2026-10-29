import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const email = process.env.SPIDER_MONITOR_EMAIL;
const password = process.env.SPIDER_MONITOR_PASSWORD;
const outDir = "C:/Projetos/spider/docs/operations/screenshots/sandbox-monitor-oidc-20260930";
const monitor = "https://monitor.spider.actionhub.com.br/";

if (!email || !password) {
  console.error("missing operator credentials in environment");
  process.exit(1);
}

await mkdir(outDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1400, height: 900 } });
const page = await context.newPage();

try {
  await page.goto(monitor, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForURL(/amazoncognito\.com/, { timeout: 30000 });
  const signInLink = page.getByRole("link", { name: /sign in|entrar/i }).first();
  if (await signInLink.isVisible().catch(() => false)) {
    await signInLink.click();
  }
  await page.screenshot({ path: path.join(outDir, "01-login.png"), fullPage: true });

  const user = page.locator('#signInFormUsername:visible, input[name="username"]:visible').first();
  const pass = page.locator('#signInFormPassword:visible, input[name="password"]:visible, input[type="password"]:visible').first();
  await user.waitFor({ state: "visible", timeout: 30000 });
  await user.fill(email);
  await pass.fill(password);
  await page.locator('#signInFormUsername:visible, input[name="username"]:visible').locator("xpath=ancestor::form").locator('input[type="submit"], button[type="submit"]').first().click();
  try {
    await page.waitForURL(/monitor\.spider\.actionhub\.com\.br/, { timeout: 45000, waitUntil: "domcontentloaded" });
  } catch (err) {
    await page.screenshot({ path: path.join(outDir, "01b-after-submit.png"), fullPage: true });
    console.error(`after-submit-url=${page.url()}`);
    throw err;
  }

  await page.waitForSelector("text=Monitor de transações", { timeout: 30000 });
  await page.waitForFunction(() => !document.body.innerText.includes("Consultando transações"), { timeout: 30000 }).catch(() => {});
  await page.screenshot({ path: path.join(outDir, "02-monitor.png"), fullPage: true });

  const consoleRes = await page.evaluate(async () => {
    const res = await fetch("/v1/console/executions", { credentials: "same-origin" });
    return { status: res.status, ok: res.ok };
  });
  if (!consoleRes.ok) {
    throw new Error(`console api status ${consoleRes.status}`);
  }

  await page.goto("https://monitor.spider.actionhub.com.br/logout", { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.screenshot({ path: path.join(outDir, "03-logout.png"), fullPage: true });
  if (!/amazoncognito\.com/.test(page.url())) {
    await page.goto(monitor, { waitUntil: "domcontentloaded" });
  }
  if (!/amazoncognito\.com/.test(page.url())) {
    throw new Error("session survived logout");
  }

  const cookies = await context.cookies();
  const leaked = cookies.some((item) => item.httpOnly === false && /Spider/i.test(item.name));
  if (leaked) {
    throw new Error("session cookie visible to javascript");
  }

  console.log("oidc-proof=ok");
  console.log(`console-api=${consoleRes.status}`);
} finally {
  await browser.close();
}
