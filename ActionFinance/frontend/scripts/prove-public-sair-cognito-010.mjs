import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "sair-cognito-010");
const evidence = join(here, "..", "..", "documents", "reviews", "evidence", "sair-cognito-010");
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });

const origin = "https://actionfinance.actionhub.com.br";
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const hops = [];
page.on("response", (response) => {
  const url = response.url();
  if (
    url.includes("/access/cognito-logout") ||
    url.includes("/oauth2/authorization") ||
    url.includes("amazoncognito.com/logout") ||
    url.includes("amazoncognito.com/login") ||
    url.includes("amazoncognito.com/oauth2")
  ) {
    hops.push({ status: response.status(), path: new URL(url).pathname, host: new URL(url).host });
  }
});

try {
  const started = await page.goto(`${origin}/access/cognito-logout?logout_uri=https://evil.example`, {
    waitUntil: "domcontentloaded",
    timeout: 45000,
  });
  await page.waitForURL(/amazoncognito\.com/, { timeout: 25000 });
  await page.locator("input.inputField-customizable[name=username], #signInFormUsername").first().waitFor({ state: "attached", timeout: 15000 });
  const url = page.url();
  const title = await page.title();
  const hasPassword = (await page.locator("input[name=password], #signInFormPassword").count()) > 0;
  const localReenter = await page.getByRole("button", { name: "Entrar novamente" }).count();
  const meResponse = await page.request.get(`${origin}/api/v1/access/me`, { headers: { Accept: "application/json" } });
  const me = { status: meResponse.status() };
  await page.screenshot({ path: join(shots, "1280-cognito-form.png"), fullPage: true });
  const record = {
    at: new Date().toISOString(),
    startStatus: started?.status(),
    url: url.split("?")[0],
    host: new URL(url).host,
    title,
    hasPassword,
    localReenter,
    me,
    hops,
    note: "Formulário Cognito real após GET /access/cognito-logout. Sem tokens. logout_uri do usuário foi ignorado.",
  };
  await writeFile(join(evidence, "public-form.json"), JSON.stringify(record, null, 2), "utf8");
  console.log(JSON.stringify(record, null, 2));
  if (!url.includes("amazoncognito.com") || !hasPassword || localReenter) {
    throw new Error("Did not remain on the Finance Hosted UI form.");
  }
  if (me.status !== 401) {
    throw new Error(`expected /access/me 401, got ${me.status}`);
  }
} finally {
  await browser.close();
}
