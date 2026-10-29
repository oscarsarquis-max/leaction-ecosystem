import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "correcao-logout-009");
const evidence = join(here, "..", "..", "documents", "reviews", "evidence", "correcao-logout-009");
await mkdir(shots, { recursive: true });
await mkdir(evidence, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_UI_URL ?? "http://127.0.0.1:4179";
const companyId = "11111111-1111-1111-1111-111111111111";
const log = [];
const notes = [
  "API simulada no Playwright. Não é sessão pública nem escrita financeira.",
  "Favicon 404 e aviso de inicialização do console não entram na causa.",
];

const me = {
  actorId: "actor",
  displayName: "Oscar Sarquis",
  accessState: "READY",
  permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write"],
  authorizedCompanies: [{ id: companyId, tenantId: "t", name: "Loja de Pães", active: true, demo: false }],
  authorizedCompanyDetails: [
    {
      id: companyId,
      tenantId: "t",
      name: "Loja de Pães",
      active: true,
      demo: false,
      permissions: ["titles:write", "catalogs:write", "financial-accounts:read", "financial-accounts:write"],
    },
  ],
};

const emptyList = {
  items: [],
  totalItems: 0,
  page: 0,
  size: 20,
  summary: { openCount: 0, openAmountMinor: "0", overdueCount: 0, overdueAmountMinor: "0", draftCount: 0 },
  businessDate: "2026-10-05",
};

function prefixOf(width) {
  if (width <= 400) return "360";
  if (width < 1000) return String(width);
  if (width < 1600) return "1280";
  return "1848";
}

const browser = await chromium.launch({ headless: true });

async function installRoutes(page, { logoutStatus = 204 } = {}) {
  let signedOut = false;
  const requests = [];
  page.on("request", (request) => {
    const url = request.url();
    if (url.includes("/logout") || url.includes("/access/me") || url.includes("/access/csrf")) {
      requests.push({
        at: new Date().toISOString(),
        method: request.method(),
        path: new URL(url).pathname,
        statusPending: true,
      });
    }
  });
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/logout") || url.includes("/access/me") || url.includes("/access/csrf")) {
      const row = requests.find((item) => item.statusPending && item.path === new URL(url).pathname);
      if (row) {
        row.status = response.status();
        delete row.statusPending;
      }
    }
  });
  await page.route("**/logout", async (route) => {
    signedOut = route.request().method() === "POST" && logoutStatus === 204;
    await route.fulfill({ status: logoutStatus, body: "" });
  });
  await page.route("**/api/v1/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/system/info")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ accessMode: "OIDC", receiptSyncEnabled: true }),
      });
      return;
    }
    if (url.includes("/access/me")) {
      await route.fulfill({
        status: signedOut ? 401 : 200,
        contentType: "application/json",
        body: signedOut ? "{}" : JSON.stringify(me),
      });
      return;
    }
    if (url.includes("/access/csrf")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ token: "t", headerName: "X-XSRF-TOKEN" }),
      });
      return;
    }
    if (url.includes("/pay-receipts")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          environment: "PRODUCTION",
          homolog: false,
          createsFinancialMovement: false,
          latestRun: null,
          items: [],
        }),
      });
      return;
    }
    if (url.includes("/receivables") || url.includes("/payables")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(emptyList) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  return { requests, getSignedOut: () => signedOut };
}

async function shot(page, name) {
  await page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
}

async function expectHold(page, label) {
  await page.getByRole("button", { name: "Entrar novamente" }).waitFor({ timeout: 15000 });
  const url = page.url();
  if (!url.includes("logout=1")) {
    throw new Error(`${label}: expected /?logout=1, got ${url}`);
  }
  if (url.includes("amazoncognito.com") || url.includes("/oauth2/authorization")) {
    throw new Error(`${label}: OIDC restarted after logout`);
  }
}

try {
  for (const width of [360, 900, 1280]) {
    const prefix = prefixOf(width);
    const page = await browser.newPage({
      viewport: { width, height: width <= 400 ? 900 : 900 },
      hasTouch: width <= 400,
    });
    const { requests } = await installRoutes(page);
    await page.goto(`${baseUrl}/receivables`, { waitUntil: "networkidle" });
    await page.getByText("Oscar Sarquis").waitFor({ timeout: 20000 });
    await shot(page, `${prefix}-antes`);
    const sair = page.getByRole("button", { name: "Sair" });
    if (width <= 400) {
      await sair.tap();
    } else {
      await sair.click();
    }
    await expectHold(page, `${prefix} mouse/touch`);
    await shot(page, `${prefix}-depois`);
    const returnPath = await page.evaluate(() => sessionStorage.getItem("af.returnPath"));
    if (returnPath) {
      throw new Error(`${prefix}: af.returnPath survived logout`);
    }
    await page.reload({ waitUntil: "networkidle" });
    await expectHold(page, `${prefix} reload`);
    log.push({ width, action: "sair", logout: requests.filter((row) => row.path === "/logout") });
    await page.close();
  }

  const keyboard = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await installRoutes(keyboard);
  await keyboard.goto(`${baseUrl}/receivables`, { waitUntil: "networkidle" });
  await keyboard.getByText("Oscar Sarquis").waitFor();
  await keyboard.getByRole("button", { name: "Sair" }).focus();
  await keyboard.keyboard.press("Enter");
  await expectHold(keyboard, "keyboard");
  await shot(keyboard, "1280-teclado");
  await keyboard.close();

  const dirty = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await installRoutes(dirty);
  dirty.on("dialog", async (dialog) => {
    log.push({ action: "dirty-confirm", message: dialog.message() });
    await dialog.dismiss();
  });
  await dirty.goto(`${baseUrl}/receivables/new`, { waitUntil: "networkidle" });
  await dirty.getByLabel(/Descrição/).fill("Rascunho sujo");
  await dirty.getByRole("button", { name: "Sair" }).click();
  await dirty.getByRole("heading", { name: "Nova conta a receber" }).waitFor();
  if (await dirty.getByRole("button", { name: "Entrar novamente" }).count()) {
    throw new Error("dirty refuse left the form");
  }
  await shot(dirty, "1280-rascunho-recusado");
  await dirty.close();

  const csrf = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  await installRoutes(csrf, { logoutStatus: 403 });
  await csrf.goto(`${baseUrl}/receivables`, { waitUntil: "networkidle" });
  await csrf.getByText("Oscar Sarquis").waitFor();
  await csrf.getByRole("button", { name: "Sair" }).click();
  await csrf.getByRole("alert").filter({ hasText: "Não foi possível confirmar a saída" }).waitFor({ timeout: 15000 });
  if (await csrf.getByRole("button", { name: "Entrar novamente" }).count()) {
    throw new Error("403 presented as completed logout");
  }
  await shot(csrf, "1280-csrf-403");
  await csrf.close();
} finally {
  await browser.close();
}

await writeFile(join(evidence, "local-logout.json"), JSON.stringify({ at: new Date().toISOString(), baseUrl, notes, log }, null, 2), "utf8");
console.log(JSON.stringify({ shots, notes, log }, null, 2));
