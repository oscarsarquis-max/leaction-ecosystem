import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const evidence = join(here, "..", "..", "documents", "reviews", "evidence", "correcao-logout-009");
await mkdir(evidence, { recursive: true });

const origin = "https://actionfinance.actionhub.com.br";
const waitMs = Number(process.env.AF_LOGIN_WAIT_MS ?? 180000);
const browser = await chromium.launch({ headless: false });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const logout = [];

page.on("response", (response) => {
  const url = response.url();
  if (url.includes("/logout") || url.endsWith("/access/me") || url.includes("/access/csrf")) {
    logout.push({
      at: new Date().toISOString(),
      method: response.request().method(),
      path: new URL(url).pathname,
      status: response.status(),
    });
  }
});

try {
  await page.goto(`${origin}/receivables`, { waitUntil: "domcontentloaded", timeout: 45000 });
  const sair = page.getByRole("button", { name: "Sair" });
  try {
    await sair.waitFor({ timeout: waitMs });
  } catch {
    await writeFile(
      join(evidence, "public-auth-pending.json"),
      JSON.stringify(
        {
          at: new Date().toISOString(),
          url: page.url(),
          note: "Sessão humana não concluída nesta janela. Hold anônimo já comprovado em public-hold.json.",
        },
        null,
        2,
      ),
      "utf8",
    );
    throw new Error("Human login was not completed; authenticated logout remains pending.");
  }
  const identity = await page.locator(".top-user-name").innerText();
  const company = await page.locator(".top-company-name, select[aria-label='Empresa ativa']").first().innerText();
  await sair.click();
  await page.getByRole("button", { name: "Entrar novamente" }).waitFor({ timeout: 20000 });
  const after = page.url();
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Entrar novamente" }).waitFor({ timeout: 20000 });
  const me = await page.evaluate(async () => {
    const response = await fetch("/api/v1/access/me", { credentials: "include", headers: { Accept: "application/json" } });
    return { status: response.status };
  });
  const titles = await page.evaluate(async () => {
    const response = await fetch("/api/v1/receivables?page=0&size=1", {
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    return { status: response.status };
  });
  const record = {
    at: new Date().toISOString(),
    identityPresentBefore: Boolean(identity),
    companyPresentBefore: Boolean(company),
    after,
    reload: page.url(),
    me,
    titles,
    logout,
    oauthAfter: after.includes("amazoncognito.com") || after.includes("/oauth2/authorization"),
  };
  await writeFile(join(evidence, "public-auth-logout.json"), JSON.stringify(record, null, 2), "utf8");
  console.log(JSON.stringify(record, null, 2));
  if (me.status !== 401 || titles.status !== 401) {
    throw new Error("Protected endpoints did not return 401 after Sair.");
  }
  if (!after.includes("logout=1") || record.oauthAfter) {
    throw new Error("Signed-out hold failed or OIDC restarted.");
  }
} finally {
  await browser.close();
}
