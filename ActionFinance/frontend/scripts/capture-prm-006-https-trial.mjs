import { spawnSync } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "documents", "reviews", "screenshots", "prm-006-cor-001");
await mkdir(shots, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_HTTPS_TRIAL_URL ?? "https://finance.trial.localhost:18443";
const hostJar = join(here, "..", "..", "backend", "target", "actionfinance-backend-0.1.0.jar");
const trialOrgs = {
  issuer: process.env.ACTIONFINANCE_TRIAL_ISSUER ?? "https://idp.trial.localhost:18444/default",
  aTenant: process.env.ACTIONFINANCE_TRIAL_TENANT_A ?? "d6f19ecc-1832-4c50-982b-76e7e93f8f3d",
  aCompany: process.env.ACTIONFINANCE_TRIAL_COMPANY_A ?? "23cc1d84-4554-4d07-b06f-cd5529fa12fd",
  bTenant: process.env.ACTIONFINANCE_TRIAL_TENANT_B ?? "65d614c0-b209-43fc-aaec-c0c5c095dad8",
  bCompany: process.env.ACTIONFINANCE_TRIAL_COMPANY_B ?? "a3e2ef38-fe88-4c8c-aa9c-552421dbe958",
};

function provisionTrialSubject(issuer, subject) {
  const env = {
    ...process.env,
    ACTIONFINANCE_DATASOURCE_URL: process.env.ACTIONFINANCE_DATASOURCE_URL ?? "jdbc:postgresql://127.0.0.1:15439/actionfinance",
    ACTIONFINANCE_RUNTIME_USERNAME: "actionfinance_runtime",
    ACTIONFINANCE_RUNTIME_PASSWORD: process.env.ACTIONFINANCE_TRIAL_RUNTIME_PASSWORD ?? "runtime-change-me",
    ACTIONFINANCE_MIGRATOR_USERNAME: "actionfinance_migrator",
    ACTIONFINANCE_MIGRATOR_PASSWORD: process.env.ACTIONFINANCE_TRIAL_MIGRATOR_PASSWORD ?? "migrator-change-me",
    ACTIONFINANCE_OIDC_ENABLED: "false",
    ACTIONFINANCE_DEMO_AUTH_ENABLED: "false",
  };
  const grants = [
    ["OPERATOR", trialOrgs.aTenant, trialOrgs.aCompany, "ensaio-https-operator-a"],
    ["VIEWER", trialOrgs.bTenant, trialOrgs.bCompany, "ensaio-https-viewer-b"],
  ];
  for (const [role, tenantId, companyId, reason] of grants) {
    const result = spawnSync(
      "java",
      [
        "-jar",
        hostJar,
        "--spring.profiles.active=access-admin",
        "provision",
        "--display-name=Operadora-ensaio-HTTPS",
        `--issuer=${issuer}`,
        `--subject=${subject}`,
        `--tenant-id=${tenantId}`,
        `--company-id=${companyId}`,
        `--role=${role}`,
        `--reason=${reason}`,
      ],
      { env, encoding: "utf8" },
    );
    if (result.status !== 0) {
      throw new Error(`access-admin provision ${role} failed with ${result.status}`);
    }
  }
}
const clicks = [];
const measures = [];
const created = [];
const cookieEvidence = [];

function note(step, how) {
  clicks.push({ step, how });
}

function prefixFor(width) {
  if (width <= 400) {
    return "mobile-360";
  }
  if (width <= 800) {
    return "tablet-768";
  }
  return "desktop-1280";
}

async function measure(page, name) {
  const box = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  measures.push({ name, ...box });
}

async function shot(page, name) {
  await measure(page, name);
  await page.screenshot({ path: join(shots, `${name}.png`), fullPage: true });
}

async function openNav(page, width, label) {
  if (width <= 1023) {
    await page.getByRole("button", { name: "Menu" }).click();
  }
  await page.getByRole("button", { name: label }).click();
}

async function signInOidc(page) {
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.getByText("Carregando acesso…").waitFor({ state: "hidden", timeout: 30000 }).catch(() => undefined);
  const enter = page.getByRole("button", { name: "Entrar" });
  if (await enter.count()) {
    await enter.waitFor({ state: "visible", timeout: 15000 });
    note("entrar", "automatizado: clicou Entrar e seguiu o Authorization Code do IdP de ensaio");
    await enter.click();
    await page
      .getByRole("heading", { name: "Seu acesso ainda não foi liberado" })
      .or(page.getByRole("button", { name: "A receber" }))
      .or(page.getByText("Não foi possível entrar com o provedor"))
      .first()
      .waitFor({ timeout: 45000 });
  }
  if (await page.getByText("Não foi possível entrar com o provedor").count()) {
    throw new Error("OIDC login failed at the application.");
  }
  if (await page.getByRole("heading", { name: "Seu acesso ainda não foi liberado" }).count()) {
    const identity = await page.evaluate(async () => {
      const response = await fetch("/api/v1/access/me", { credentials: "include" });
      return response.json();
    });
    if (!identity.issuer || !identity.subject) {
      throw new Error("Authenticated trial user did not expose issuer+subject.");
    }
    note("provisionar subject", "automatizado: leu issuer+subject no /me e executou access-admin provision OPERATOR/VIEWER");
    provisionTrialSubject(identity.issuer, identity.subject);
    await page.goto(`${baseUrl}/receivables`, { waitUntil: "domcontentloaded" });
    await page.getByText("Carregando acesso…").waitFor({ state: "hidden", timeout: 30000 }).catch(() => undefined);
  }
  await page.getByRole("button", { name: "A receber" }).or(page.getByRole("heading", { name: "Contas a receber" })).first().waitFor({ timeout: 45000 });
}

async function assertSessionCookies(context) {
  const cookies = await context.cookies();
  const session = cookies.find((item) => item.name === "AFSESSION");
  const csrf = cookies.find((item) => item.name === "XSRF-TOKEN");
  if (!session) {
    throw new Error("AFSESSION cookie missing after OIDC login.");
  }
  if (!session.httpOnly || !session.secure || String(session.sameSite).toLowerCase() !== "lax") {
    throw new Error(`AFSESSION flags unexpected: ${JSON.stringify(session)}`);
  }
  if (session.domain && session.domain.startsWith(".")) {
    throw new Error(`AFSESSION is not host-only: domain=${session.domain}`);
  }
  if (!csrf || csrf.httpOnly) {
    throw new Error(`XSRF-TOKEN missing or HttpOnly: ${JSON.stringify(csrf)}`);
  }
  cookieEvidence.push({
    name: "AFSESSION",
    httpOnly: session.httpOnly,
    secure: session.secure,
    sameSite: session.sameSite,
    domain: session.domain ?? "(host-only / unset)",
    path: session.path,
  });
  cookieEvidence.push({
    name: "XSRF-TOKEN",
    httpOnly: csrf.httpOnly,
    secure: csrf.secure,
    sameSite: csrf.sameSite,
    path: csrf.path,
  });
}

async function selectAccount(page, accountName) {
  const box = page.locator("label.searchable").filter({ hasText: "Conta financeira" });
  await box.getByLabel("Buscar Conta financeira").fill(accountName);
  await box.locator("select").selectOption({ label: accountName });
}

async function unknownApiIsNotIndex(page) {
  const result = await page.evaluate(async () => {
    const response = await fetch("/api/v1/does-not-exist-cor001", { credentials: "include" });
    const body = await response.text();
    return { status: response.status, body, contentType: response.headers.get("content-type") };
  });
  if (result.status === 200 && /<!doctype html/i.test(result.body)) {
    throw new Error("Unknown API path returned index.html");
  }
  if (/<div id="root"|@vite\/client/.test(result.body)) {
    throw new Error("Unknown API path leaked the SPA or Vite client");
  }
  return { status: result.status, contentType: result.contentType, looksLikeHtml: /<!doctype html/i.test(result.body) };
}

async function refuseWriteOnViewerCompany(page) {
  const result = await page.evaluate(async () => {
    const me = await fetch("/api/v1/access/me", { credentials: "include" });
    const profile = await me.json();
    const viewer = (profile.authorizedCompanyDetails ?? profile.authorizedCompanies ?? []).find(
      (item) => item.name === "Empresa-B-ensaio-HTTPS",
    );
    const companyId = viewer?.id ?? viewer?.companyId;
    if (!viewer || !companyId) {
      return { error: `Viewer company B not present on /me: ${JSON.stringify(profile.authorizedCompanyDetails ?? profile.authorizedCompanies)}` };
    }
    const csrf = await fetch("/api/v1/access/csrf", { credentials: "include" });
    const token = (await csrf.json()).token;
    const create = await fetch(`/api/v1/receivables?companyId=${companyId}`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-XSRF-TOKEN": token ?? "",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify({
        description: "Escrita recusada no ensaio B",
        amountMinor: 1000,
        currency: "BRL",
        competenceDate: "2026-09-15",
        dueDate: "2026-09-30",
      }),
    });
    return { status: create.status, body: await create.text(), companyId, viewer };
  });
  if (result.error) {
    throw new Error(result.error);
  }
  if (result.status !== 403) {
    throw new Error(`Expected 403 writing in company B, got ${result.status} ${result.body}`);
  }
  return result.companyId;
}

async function runJourney(browser, width, height) {
  const prefix = prefixFor(width);
  const stamp = `${prefix}-${Date.now()}`;
  const accountName = `Conta ensaio HTTPS ${stamp}`;
  const receivableName = `Recebível ensaio HTTPS ${stamp}`;
  created.push({ viewport: prefix, accountName, receivableName });

  const context = await browser.newContext({
    viewport: { width, height },
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();

  await signInOidc(page);
  await assertSessionCookies(context);
  if (await page.locator('script[src*="vite"]').count()) {
    throw new Error("Vite client script present in production image");
  }
  const companySelect = page.getByLabel("Empresa ativa");
  if (await companySelect.count()) {
    await companySelect.selectOption({ label: "Empresa-A-ensaio-HTTPS" });
    note("empresa A", "automatizado: selecionou Empresa-A-ensaio-HTTPS");
  }
  await shot(page, `${prefix}-signed-in`);

  await openNav(page, width, "Contas financeiras");
  await page.getByRole("button", { name: "Nova conta" }).click();
  await page.getByRole("heading", { name: "Nova conta financeira" }).waitFor({ timeout: 20000 });
  await page.getByLabel("Nome").fill(accountName);
  await page.getByLabel("Tipo").selectOption("CASH");
  await page.getByLabel("Início do controle").fill("2026-09-01");
  await page.getByLabel("Saldo inicial").fill("200,00");
  note("criar conta", "automatizado: nome/tipo/2026-09-01/200,00 e Criar conta");
  await page.getByRole("button", { name: "Criar conta" }).click();
  await page.getByRole("heading", { name: accountName }).waitFor({ timeout: 20000 });
  await shot(page, `${prefix}-account`);

  await openNav(page, width, "A receber");
  if (await companySelect.count()) {
    await companySelect.selectOption({ label: "Empresa-A-ensaio-HTTPS" });
  }
  await page.getByRole("button", { name: "Novo recebível" }).first().click();
  await page.getByRole("heading", { name: "Novo recebível" }).waitFor({ timeout: 20000 });
  const catalogNames = { counterparty: `Cliente ensaio ${stamp}`, category: `Categoria ensaio ${stamp}` };
  const catalogs = await page.evaluate(async (names) => {
    const me = await (await fetch("/api/v1/access/me", { credentials: "include" })).json();
    const company = (me.authorizedCompanyDetails ?? []).find((item) => item.name === "Empresa-A-ensaio-HTTPS");
    const csrf = await (await fetch("/api/v1/access/csrf", { credentials: "include" })).json();
    const headers = { "Content-Type": "application/json", "X-XSRF-TOKEN": csrf.token ?? "" };
    const counterparty = await fetch(`/api/v1/catalogs/counterparties?companyId=${company.id}`, {
      method: "POST",
      credentials: "include",
      headers,
      body: JSON.stringify({ name: names.counterparty, role: "CUSTOMER" }),
    });
    const category = await fetch(`/api/v1/catalogs/categories?companyId=${company.id}`, {
      method: "POST",
      credentials: "include",
      headers,
      body: JSON.stringify({ name: names.category, direction: "RECEIVABLE" }),
    });
    return {
      counterpartyStatus: counterparty.status,
      categoryStatus: category.status,
      counterparty: counterparty.ok ? await counterparty.json() : await counterparty.text(),
      category: category.ok ? await category.json() : await category.text(),
    };
  }, catalogNames);
  if (catalogs.counterpartyStatus !== 200 && catalogs.counterpartyStatus !== 201) {
    throw new Error(`Counterparty create failed: ${catalogs.counterpartyStatus} ${JSON.stringify(catalogs.counterparty)}`);
  }
  if (catalogs.categoryStatus !== 200 && catalogs.categoryStatus !== 201) {
    throw new Error(`Category create failed: ${catalogs.categoryStatus} ${JSON.stringify(catalogs.category)}`);
  }
  note("cadastros", "API autenticada da mesma sessão (o diálogo HTML não disparou POST no headless); título e baixa continuam pela UI");
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { name: "Novo recebível" }).waitFor({ timeout: 20000 });
  await page.locator("label.searchable").filter({ hasText: "Cliente / pagador" }).locator("select").selectOption({ label: catalogNames.counterparty });
  await page.locator("label.searchable").filter({ hasText: "Categoria" }).locator("select").selectOption({ label: catalogNames.category });
  await page.getByLabel(/Descrição/).fill(receivableName);
  await page.getByLabel("Valor (BRL)").fill("150,00");
  await page.getByLabel("Competência").fill("2026-09-15");
  await page.getByLabel("Vencimento").fill("2026-09-30");
  note("criar título", "automatizado: Novo recebível com contraparte/categoria de ensaio + Registrar");
  await page.getByRole("button", { name: "Registrar" }).click();
  const titleReady = page.getByRole("heading", { name: receivableName }).or(page.getByText(receivableName));
  const titleError = page.locator("p.error, .error-box, [role=alert]");
  await titleReady.or(titleError).first().waitFor({ timeout: 20000 });
  if (await titleError.count() && !(await titleReady.count())) {
    const fieldErrors = await page.locator("span.error, p.error").allInnerTexts();
    throw new Error(`Title was not registered: ${await titleError.first().innerText()} ${JSON.stringify(fieldErrors)}`);
  }
  await shot(page, `${prefix}-title`);

  await page.getByRole("button", { name: "Registrar recebimento" }).click();
  await page.getByRole("heading", { name: "Registrar recebimento realizado" }).waitFor();
  await selectAccount(page, accountName);
  await page.getByLabel("Valor").fill("50,00");
  await page.getByLabel("Meio").selectOption("PIX");
  note("baixa parcial", "automatizado: baixa 50,00 Pix na conta do ensaio");
  await page.getByRole("button", { name: "Registrar recebimento" }).click();
  await page.getByText("R$ 100,00").first().waitFor({ timeout: 20000 });
  await shot(page, `${prefix}-partial-settlement`);

  await openNav(page, width, "Contas financeiras");
  await page.getByRole("link", { name: accountName }).locator("visible=true").first().click();
  await page.getByRole("heading", { name: accountName }).waitFor({ timeout: 20000 });
  await page.getByText("Extrato gerencial").waitFor({ timeout: 20000 });
  await shot(page, `${prefix}-statement`);

  if (await companySelect.count()) {
    await companySelect.selectOption({ label: "Empresa-B-ensaio-HTTPS" });
    note("empresa B", "automatizado: trocou para Empresa-B-ensaio-HTTPS (VIEWER)");
    await openNav(page, width, "A receber");
    await page.getByRole("heading", { name: /Contas a receber|A receber/ }).or(page.getByRole("button", { name: "A receber" })).first().waitFor({ timeout: 20000 });
    if (await page.getByRole("button", { name: "Novo recebível" }).count()) {
      throw new Error("VIEWER company still shows Novo recebível");
    }
    await shot(page, `${prefix}-viewer-company`);
    await refuseWriteOnViewerCompany(page);
    await companySelect.selectOption({ label: "Empresa-A-ensaio-HTTPS" });
  }

  const unknownApi = await unknownApiIsNotIndex(page);

  await page.getByRole("button", { name: "Sair" }).click();
  await page.getByRole("button", { name: "Entrar" }).or(page.getByText("Não foi possível confirmar a saída")).first().waitFor({ timeout: 20000 });
  await shot(page, `${prefix}-signed-out`);
  if (await page.getByText(receivableName).count()) {
    throw new Error("Financial data still visible after confirmed or attempted logout");
  }

  await signInOidc(page);
  await openNav(page, width, "A receber");
  const matches = page.getByText(receivableName).locator("visible=true");
  await matches.first().waitFor({ timeout: 20000 });
  if ((await matches.count()) < 1) {
    throw new Error("Title missing after re-login");
  }
  await shot(page, `${prefix}-relogin-same-title`);

  await context.close();
  return unknownApi;
}

const browser = await chromium.launch({
  headless: true,
  args: ["--host-resolver-rules=MAP finance.trial.localhost 127.0.0.1, MAP idp.trial.localhost 127.0.0.1"],
});

try {
  const unknownApi = await runJourney(browser, 1280, 800);
  await runJourney(browser, 768, 800);
  await runJourney(browser, 360, 800);
  const summary = {
    ok: true,
    baseUrl,
    shots,
    created,
    cookieEvidence,
    unknownApi,
    automation: "Playwright headless, imagem de ensaio, OIDC mock HTTPS. Jornada entrar → empresa → título → baixa parcial → extrato → sair. Sem capturas PRM_005.",
    clicks,
    measures,
  };
  await writeFile(join(shots, "journey-log.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
} finally {
  await browser.close();
}
