const { chromium } = require("playwright");
(async () => {
  const email = process.env.QMIND_UI_USER;
  const pass = process.env.QMIND_UI_PASS;
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto("https://app.homolog.qmind.com.br/", { waitUntil: "networkidle", timeout: 60000 });
  await page.getByRole("button", { name: /entrar/i }).click();
  await page.waitForURL(/amazoncognito\.com/, { timeout: 60000 });
  // Cognito duplicates inputs across responsive wrappers; force visible.
  const user = page.locator('input[name="username"]:visible').first();
  const pw = page.locator('input[name="password"]:visible').first();
  await user.waitFor({ state: "visible", timeout: 30000 });
  await user.fill(email);
  await pw.fill(pass);
  await page.locator('input[name="signInSubmitButton"]:visible, button[type="submit"]:visible').first().click();
  await page.waitForURL(/app\.homolog\.qmind\.com\.br/, { timeout: 90000 });
  await page.waitForTimeout(2500);
  const url = page.url();
  const ok = url.includes("app.homolog.qmind.com.br") && !url.includes("amazoncognito.com");
  const storage = await page.evaluate(() => ({ ls: Object.keys(localStorage), ss: Object.keys(sessionStorage) }));
  const sensitive = [...storage.ls, ...storage.ss].filter((k) => /access_token|id_token|refresh|password|secret/i.test(k));
  console.log(JSON.stringify({ ui_login_ok: ok, host: new URL(url).host, path: new URL(url).pathname, sensitive_keys: sensitive, ss: storage.ss }));
  await browser.close();
  process.exit(ok ? 0 : 1);
})().catch((e) => { console.error("ERR=" + String(e.message || e)); process.exit(1); });