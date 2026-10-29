import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "prm-007-encerramento");
await mkdir(shots, { recursive: true });

const origin = "https://actionfinance.actionhub.com.br";
const expectedCompanyId = "624023a4-57e3-415c-b7d0-925ca1acd3b7";
const waitMs = Number(process.env.ACTIONFINANCE_LOGIN_WAIT_MS ?? 15 * 60 * 1000);

function stripSecrets(text) {
  return String(text ?? "")
    .replace(/[A-Za-z0-9_-]{20,}/g, "[redacted]")
    .replace(/XSRF-TOKEN=[^;]+/gi, "XSRF-TOKEN=[redacted]")
    .replace(/AFSESSION=[^;]+/gi, "AFSESSION=[redacted]");
}

const browser = await chromium.launch({ headless: false, handleSIGINT: true });
const context = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  locale: "pt-BR",
});
const page = await context.newPage();

console.log("Use esta janela do Chromium. Clique em Entrar e conclua o login.");
console.log("Quando aparecer Loja de Pães, deixe a janela aberta. O ensaio continua sozinho.");

let log = { capturedAt: new Date().toISOString(), origin, cookiesWritten: false };

try {
  await page.goto(`${origin}/receivables`, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.getByRole("button", { name: "Sair" }).waitFor({ timeout: waitMs });
  await page.getByText("Loja de Pães").first().waitFor({ timeout: 20000 });
  await page.waitForTimeout(1500);

  const me = await page.evaluate(async () => {
    const response = await fetch("/api/v1/access/me", { credentials: "include", headers: { Accept: "application/json" } });
    if (response.status !== 200) {
      return { status: response.status };
    }
    const body = await response.json();
    const companies = body.authorizedCompanies ?? [];
    return {
      status: 200,
      actorId: body.actorId,
      companyIds: companies.map((item) => item.id),
      companyNames: companies.map((item) => item.name),
      companyCount: companies.length,
    };
  });
  log.meStatus = me.status;
  log.actorId = me.actorId;
  log.companyIds = me.companyIds;
  log.companyNames = me.companyNames;
  if (me.status !== 200) {
    throw new Error("O cabeçalho autenticado apareceu, mas /api/v1/access/me não devolveu 200.");
  }
  if (!me.companyIds.includes(expectedCompanyId) || me.companyCount !== 1) {
    throw new Error("Sessão autenticada não identificou só a empresa autorizada.");
  }

  const api = await page.evaluate(async () => {
    const csrfRes = await fetch("/api/v1/access/csrf", { credentials: "include", headers: { Accept: "application/json" } });
    const csrf = await csrfRes.json();
    const headerName = csrf.headerName;
    const noToken = await fetch("/logout", {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    const afterNoToken = await fetch("/api/v1/access/me", { credentials: "include", headers: { Accept: "application/json" } });
    const invalid = await fetch("/logout", {
      method: "POST",
      credentials: "include",
      headers: { Accept: "application/json", [headerName]: "invalid-csrf-token" },
    });
    const afterInvalid = await fetch("/api/v1/access/me", { credentials: "include", headers: { Accept: "application/json" } });
    return {
      csrfStatus: csrfRes.status,
      headerPresent: Boolean(headerName),
      logoutWithoutCsrf: noToken.status,
      meAfterMissingCsrf: afterNoToken.status,
      logoutInvalidCsrf: invalid.status,
      meAfterInvalidCsrf: afterInvalid.status,
    };
  });
  log.api = api;
  if (api.logoutWithoutCsrf < 400 || api.logoutInvalidCsrf < 400) {
    throw new Error("Logout sem CSRF válido não foi recusado.");
  }
  if (api.meAfterMissingCsrf !== 200 || api.meAfterInvalidCsrf !== 200) {
    throw new Error("Logout recusado encerrou a sessão.");
  }

  await page.goto(`${origin}/receivables`, { waitUntil: "domcontentloaded" });
  await page.getByText("Loja de Pães").first().waitFor({ timeout: 20000 });

  await page.route("**/logout", async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({ status: 403, contentType: "application/json", body: "{\"error\":\"csrf\"}" });
      return;
    }
    await route.continue();
  });
  await page.getByRole("button", { name: "Sair" }).click();
  await page.getByRole("alert").filter({ hasText: "Não foi possível confirmar a saída" }).waitFor({ timeout: 15000 });
  const refusedStillAuthed = await page.evaluate(async () => {
    const response = await fetch("/api/v1/access/me", { credentials: "include", headers: { Accept: "application/json" } });
    return response.status;
  });
  log.refusedLogoutStillMe = refusedStillAuthed;
  if (refusedStillAuthed !== 200) {
    throw new Error("A recusa visual de saída encerrou a sessão.");
  }
  const successOnRefuse = await page.getByRole("button", { name: "Entrar" }).count();
  log.uiShowedEnterOnRefuse = Boolean(successOnRefuse);
  if (successOnRefuse) {
    throw new Error("A interface mostrou entrada como se a saída tivesse sido aceite.");
  }
  await page.screenshot({ path: join(shots, "logout-csrf-unconfirmed.png"), fullPage: false });
  await page.unroute("**/logout");

  log.cookieCountBeforeLogout = (await context.cookies()).length;
  await page.getByRole("button", { name: "Tentar sair novamente" }).click();
  await page.getByRole("button", { name: "Entrar" }).waitFor({ timeout: 20000 });
  const meAfterLogout = await page.evaluate(async () => {
    const response = await fetch("/api/v1/access/me", { credentials: "include", headers: { Accept: "application/json" } });
    return response.status;
  });
  log.meAfterValidLogout = meAfterLogout;
  if (meAfterLogout !== 401) {
    throw new Error("Logout válido não devolveu 401 em /me.");
  }
  if (await page.getByText("Loja de Pães").count()) {
    throw new Error("A interface manteve o nome da empresa após a saída confirmada.");
  }
  await page.screenshot({ path: join(shots, "logout-csrf-signed-out.png"), fullPage: false });

  const replay = await page.evaluate(async () => {
    const response = await fetch("/api/v1/access/me", { credentials: "include", headers: { Accept: "application/json" } });
    return response.status;
  });
  log.replayMe = replay;
  if (replay !== 401) {
    throw new Error("Reutilização da navegação após logout ainda autenticou.");
  }

  log.ok = true;
  await writeFile(join(shots, "logout-csrf-log.json"), JSON.stringify(log, null, 2), "utf8");
  console.log(stripSecrets(`logout/csrf ok me=${me.status} companyCount=${me.companyCount} logoutWithout=${api.logoutWithoutCsrf} afterValid=${meAfterLogout}`));
} catch (error) {
  log.ok = false;
  log.error = String(error?.message ?? error);
  await writeFile(join(shots, "logout-csrf-log.json"), JSON.stringify(log, null, 2), "utf8").catch(() => undefined);
  await page.screenshot({ path: join(shots, "logout-csrf-error.png"), fullPage: false }).catch(() => undefined);
  console.error(stripSecrets(log.error));
  await page.waitForTimeout(8000).catch(() => undefined);
  throw error;
} finally {
  await context.close().catch(() => undefined);
  await browser.close().catch(() => undefined);
}
