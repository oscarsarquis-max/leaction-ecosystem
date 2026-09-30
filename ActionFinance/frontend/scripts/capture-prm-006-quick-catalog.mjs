import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
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

async function signInOidc(page) {
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.getByText("Carregando acesso…").waitFor({ state: "hidden", timeout: 30000 }).catch(() => undefined);
  const enter = page.getByRole("button", { name: "Entrar" });
  if (await enter.count()) {
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
    provisionTrialSubject(identity.issuer, identity.subject);
    await page.goto(`${baseUrl}/receivables`, { waitUntil: "domcontentloaded" });
    await page.getByText("Carregando acesso…").waitFor({ state: "hidden", timeout: 30000 }).catch(() => undefined);
  }
  await page.getByRole("button", { name: "A receber" }).or(page.getByRole("heading", { name: "Contas a receber" })).first().waitFor({ timeout: 45000 });
}

async function openReceivables(page, width) {
  if (width <= 1023) {
    await page.getByRole("button", { name: "Menu" }).click();
  }
  await page.getByRole("button", { name: "A receber" }).click();
}

function trackPosts(page) {
  const posts = [];
  page.on("request", (request) => {
    if (request.method() === "POST") {
      posts.push({
        url: request.url(),
        path: new URL(request.url()).pathname,
        hash: createHash("sha256").update(request.postData() ?? "").digest("hex").slice(0, 16),
      });
    }
  });
  return posts;
}

async function runWidth(browser, width, height) {
  const prefix = width <= 400 ? "mobile-360" : "desktop-1280";
  const stamp = `${prefix}-qc-${Date.now()}`;
  const context = await browser.newContext({
    viewport: { width, height },
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();
  const posts = trackPosts(page);

  await signInOidc(page);
  const companySelect = page.getByLabel("Empresa ativa");
  if (await companySelect.count()) {
    await companySelect.selectOption({ label: "Empresa-A-ensaio-HTTPS" });
  }
  await openReceivables(page, width);
  await page.getByRole("button", { name: "Novo recebível" }).first().click();
  await page.getByRole("heading", { name: "Novo recebível" }).waitFor({ timeout: 20000 });
  await page.getByLabel(/Descrição/).fill(`Rascunho rápido ${stamp}`);
  await page.getByLabel("Referência informativa").fill(`REF-${stamp}`);
  await page.screenshot({ path: join(shots, `${prefix}-quick-catalog-draft.png`), fullPage: true });

  const beforeDialog = posts.filter((item) => item.path.includes("/receivables")).length;
  await page.getByRole("button", { name: "Cadastrar contraparte" }).click();
  const cpDialog = page.getByRole("dialog");
  await cpDialog.getByRole("heading", { name: "Cadastrar contraparte" }).waitFor();
  await page.keyboard.press("Escape");
  await cpDialog.waitFor({ state: "hidden", timeout: 10000 });
  if ((await page.getByLabel(/Descrição/).inputValue()) !== `Rascunho rápido ${stamp}`) {
    throw new Error("Escape discarded the title draft.");
  }

  await page.getByRole("button", { name: "Cadastrar contraparte" }).click();
  await cpDialog.getByLabel("Nome").fill(`Cliente UI ${stamp}`);
  await cpDialog.getByRole("button", { name: "Salvar" }).click();
  await page.getByRole("heading", { name: "Cadastrar contraparte" }).waitFor({ state: "hidden", timeout: 20000 });
  const selectedCp = await page.locator("label.searchable").filter({ hasText: "Cliente / pagador" }).locator("select").inputValue();
  if (!selectedCp) {
    throw new Error("Created counterparty was not selected.");
  }
  if (posts.filter((item) => item.path.includes("/receivables")).length !== beforeDialog) {
    throw new Error("Saving the counterparty dialog submitted the title.");
  }
  if (!posts.some((item) => item.path.includes("/catalogs/counterparties"))) {
    throw new Error("Counterparty dialog did not POST /catalogs/counterparties.");
  }

  await page.getByRole("button", { name: "Cadastrar categoria" }).click();
  const catDialog = page.getByRole("dialog");
  await catDialog.getByRole("heading", { name: "Cadastrar categoria" }).waitFor();
  await catDialog.getByRole("button", { name: "Voltar" }).click();
  await catDialog.waitFor({ state: "hidden", timeout: 10000 });
  if ((await page.getByLabel("Referência informativa").inputValue()) !== `REF-${stamp}`) {
    throw new Error("Cancel discarded the title draft.");
  }

  await page.getByRole("button", { name: "Cadastrar categoria" }).click();
  await catDialog.getByLabel("Nome").fill(`Categoria UI ${stamp}`);
  await catDialog.getByRole("button", { name: "Salvar" }).click();
  await page.getByRole("heading", { name: "Cadastrar categoria" }).waitFor({ state: "hidden", timeout: 20000 });
  const selectedCat = await page.locator("label.searchable").filter({ hasText: "Categoria" }).locator("select").inputValue();
  if (!selectedCat) {
    throw new Error("Created category was not selected.");
  }
  if (!posts.some((item) => item.path.includes("/catalogs/categories"))) {
    throw new Error("Category dialog did not POST /catalogs/categories.");
  }

  await page.getByLabel("Valor (BRL)").fill("150,00");
  await page.getByLabel("Competência").fill("2026-09-15");
  await page.getByLabel("Vencimento").fill("2026-09-30");
  await page.screenshot({ path: join(shots, `${prefix}-quick-catalog-filled.png`), fullPage: true });
  await page.getByRole("button", { name: "Registrar" }).click();
  const titleName = `Rascunho rápido ${stamp}`;
  await page.getByRole("heading", { name: titleName }).or(page.getByText(titleName)).first().waitFor({ timeout: 20000 });
  await page.screenshot({ path: join(shots, `${prefix}-quick-catalog-registered.png`), fullPage: true });
  if (!posts.some((item) => item.path.includes("/receivables") && !item.path.includes("catalogs"))) {
    throw new Error("Title register POST was not observed.");
  }

  const persisted = await page.evaluate(async () => {
    const me = await (await fetch("/api/v1/access/me", { credentials: "include" })).json();
    const company = (me.authorizedCompanyDetails ?? []).find((item) => item.name === "Empresa-A-ensaio-HTTPS");
    const list = await (await fetch(`/api/v1/receivables?companyId=${company.id}&size=50`, { credentials: "include" })).json();
    return list;
  });
  const found = JSON.stringify(persisted).includes(titleName);
  if (!found) {
    throw new Error(`Registered title was not persisted: ${JSON.stringify(persisted).slice(0, 400)}`);
  }

  await context.close();
  return {
    viewport: prefix,
    title: titleName,
    posts: posts.map((item) => ({ path: item.path, bodyHash: item.hash })),
  };
}

const browser = await chromium.launch({
  headless: true,
  args: ["--host-resolver-rules=MAP finance.trial.localhost 127.0.0.1, MAP idp.trial.localhost 127.0.0.1"],
});

try {
  const desktop = await runWidth(browser, 1280, 800);
  const mobile = await runWidth(browser, 360, 800);
  const summary = {
    ok: true,
    baseUrl,
    automation: "Playwright OIDC. Cadastro rápido só pela UI do diálogo. Sem POST de catálogo via API substituta.",
    desktop,
    mobile,
  };
  await writeFile(join(shots, "quick-catalog-log.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
} finally {
  await browser.close();
}
