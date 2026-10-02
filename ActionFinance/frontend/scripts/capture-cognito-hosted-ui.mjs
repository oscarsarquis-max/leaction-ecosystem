import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "nova-interface");
await mkdir(shots, { recursive: true });

const domain = "https://actionfinance-253137917703.auth.us-east-2.amazoncognito.com";
const clientId = "275ig9d7lfi0j7if9rqe374rqc";
const redirect = encodeURIComponent("https://actionfinance.actionhub.com.br/login/oauth2/code/actionfinance");
const query = `response_type=code&client_id=${clientId}&redirect_uri=${redirect}&scope=openid+profile`;
const loginUrl = `${domain}/login?${query}`;
const forgotUrl = `${domain}/forgotPassword?${query}`;
const notes = [];

const browser = await chromium.launch({ headless: true });

async function capture(name, url, width, height) {
  const page = await browser.newPage({ viewport: { width, height } });
  const response = await page.goto(url, { waitUntil: "networkidle", timeout: 45000 });
  notes.push(`${name} ${width}x${height} status=${response?.status()} url=${page.url()}`);
  await page.screenshot({ path: join(shots, `${name}-${width}.png`) });
  await page.close();
}

for (const width of [1280, 768, 360]) {
  const height = width === 360 ? 800 : 800;
  await capture("cognito-login", loginUrl, width, height);
  await capture("cognito-forgot", forgotUrl, width, height);
}

const originProbe = await fetch("https://actionfinance.actionhub.com.br/oauth2/authorization/actionfinance", {
  redirect: "manual",
});
const location = originProbe.headers.get("location") ?? "";
notes.push(`af-oauth status=${originProbe.status} location=${location}`);

await browser.close();
await writeFile(join(shots, "cognito-probe.txt"), notes.join("\n"), "utf8");
console.log(notes.join("\n"));
if (!location.includes("actionfinance-253137917703.auth.us-east-2.amazoncognito.com")) {
  throw new Error("Finance OIDC start did not redirect to the Finance Hosted UI domain.");
}
if (!location.includes(clientId)) {
  throw new Error("Finance OIDC start did not use the Finance confidential client.");
}
