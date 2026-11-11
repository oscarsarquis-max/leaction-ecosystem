import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

const out = path.resolve("docs/operations/screenshots/af-spider-20261014");
mkdirSync(out, { recursive: true });

const AF = "https://actionfinance.actionhub.com.br";
const MONITOR = "https://monitor.spider.actionhub.com.br";
const PADARIA = "9c2e0a10-4f11-4b8a-9c2e-0a104f11000c";
const userDataDir = process.env.CHROME_USER_DATA_DIR;

const report = { startedAt: new Date().toISOString(), network: [], pages: {} };

function shot(page, name) {
  return page.screenshot({ path: path.join(out, name), fullPage: true }).then(() => {
    report.pages[name] = true;
  });
}

const browserOptions = {
  headless: false,
  channel: "chrome",
  args: ["--disable-blink-features=AutomationControlled"],
};

const context = userDataDir
  ? await chromium.launchPersistentContext(userDataDir, {
      ...browserOptions,
      viewport: { width: 1440, height: 900 },
    })
  : await (await chromium.launch(browserOptions)).newContext({ viewport: { width: 1440, height: 900 } });

const page = context.pages()[0] || (await context.newPage());
page.setDefaultTimeout(25000);

page.on("response", async (res) => {
  const url = res.url();
  if (!/pay-receipts|satellites|monitor\/records|console\//.test(url)) return;
  let body = "";
  try {
    body = (await res.text()).slice(0, 4000);
  } catch {
    body = "";
  }
  report.network.push({
    t: new Date().toISOString(),
    status: res.status(),
    method: res.request().method(),
    url,
    body,
  });
});

await page.goto(`${AF}/pay-receipts`, { waitUntil: "domcontentloaded", timeout: 45000 });
await page.waitForTimeout(2500);
report.afUrl = page.url();
report.afTitle = await page.title();
await shot(page, "01-af-pay-receipts.png");

const login = /cognito|login|signin|oauth/i.test(page.url());
report.afLogin = login;

if (!login) {
  const select = page.locator("select").first();
  if (await select.count()) {
    const options = await select.locator("option").evaluateAll((els) =>
      els.map((el) => ({ value: el.value, text: el.textContent }))
    );
    report.companies = options;
    const padaria = options.find((o) => o.value === PADARIA || /padaria|sandbox|pães|paes/i.test(o.text || ""));
    if (padaria) await select.selectOption(padaria.value);
    await page.waitForTimeout(1500);
  }

  const syncCalls = [];
  page.on("response", (res) => {
    if (res.url().includes("/api/v1/pay-receipts/sync")) syncCalls.push(res);
  });

  const btn = page.getByRole("button", { name: /^Sincronizar$/ });
  if (await btn.count()) {
    await btn.click();
    await page.waitForTimeout(8000);
  }
  report.afAfterClick = (await page.locator("body").innerText()).slice(0, 2500);
  await shot(page, "02-af-after-sync.png");
}

await page.goto(`${MONITOR}/?nocache=${Date.now()}`, { waitUntil: "domcontentloaded", timeout: 45000 });
await page.waitForTimeout(2500);
report.monitorUrl = page.url();
report.monitorLogin = /cognito|login|signin|oauth/i.test(page.url());
await shot(page, "03-monitor.png");
if (!report.monitorLogin) {
  report.monitorText = (await page.locator("body").innerText()).slice(0, 4000);
}

writeFileSync(path.join(out, "report.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify({
  afUrl: report.afUrl,
  afLogin: report.afLogin,
  monitorUrl: report.monitorUrl,
  monitorLogin: report.monitorLogin,
  companies: report.companies,
  network: report.network.map((n) => ({ status: n.status, method: n.method, url: n.url })),
}, null, 2));

await context.close();
