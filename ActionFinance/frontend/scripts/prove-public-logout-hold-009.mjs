import { chromium } from "playwright";

const origin = "https://actionfinance.actionhub.com.br";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const oauthStarts = [];
page.on("framenavigated", (frame) => {
  if (frame === page.mainFrame()) {
    const url = frame.url();
    if (url.includes("amazoncognito.com") || url.includes("/oauth2/authorization")) {
      oauthStarts.push(url.split("?")[0]);
    }
  }
});

try {
  await page.goto(`${origin}/?logout=1`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.getByRole("button", { name: "Entrar novamente" }).waitFor({ timeout: 20000 });
  const first = page.url();
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Entrar novamente" }).waitFor({ timeout: 20000 });
  const second = page.url();
  const me = await page.evaluate(async () => {
    const response = await fetch("/api/v1/access/me", { credentials: "include", headers: { Accept: "application/json" } });
    return { status: response.status };
  });
  console.log(
    JSON.stringify(
      {
        first,
        second,
        me,
        oauthStarts,
        spa: await page.evaluate(() => [...document.scripts].map((s) => s.src).find((s) => s.includes("/assets/index-"))),
      },
      null,
      2,
    ),
  );
  if (oauthStarts.length) {
    throw new Error("OIDC restarted from /?logout=1");
  }
  if (!first.includes("logout=1") || !second.includes("logout=1")) {
    throw new Error("logout hold was wiped");
  }
  if (me.status !== 401) {
    throw new Error(`expected /access/me 401, got ${me.status}`);
  }
} finally {
  await browser.close();
}
