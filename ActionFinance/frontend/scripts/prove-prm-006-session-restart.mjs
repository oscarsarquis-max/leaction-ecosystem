import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..", "..");
const shots = join(root, "documents", "reviews", "screenshots", "prm-006-cor-001");
await mkdir(shots, { recursive: true });

const baseUrl = process.env.ACTIONFINANCE_HTTPS_TRIAL_URL ?? "https://finance.trial.localhost:18443";
const hostJar = join(root, "backend", "target", "actionfinance-backend-0.1.0.jar");
const composeFile = join(root, "ops", "compose", "actionfinance-https-trial.yml");
const trialOrgs = {
  issuer: process.env.ACTIONFINANCE_TRIAL_ISSUER ?? "https://idp.trial.localhost:18444/default",
  aTenant: process.env.ACTIONFINANCE_TRIAL_TENANT_A ?? "d6f19ecc-1832-4c50-982b-76e7e93f8f3d",
  aCompany: process.env.ACTIONFINANCE_TRIAL_COMPANY_A ?? "23cc1d84-4554-4d07-b06f-cd5529fa12fd",
  bTenant: process.env.ACTIONFINANCE_TRIAL_TENANT_B ?? "65d614c0-b209-43fc-aaec-c0c5c095dad8",
  bCompany: process.env.ACTIONFINANCE_TRIAL_COMPANY_B ?? "a3e2ef38-fe88-4c8c-aa9c-552421dbe958",
};

function run(file, args, env = process.env) {
  const result = spawnSync(file, args, { env, encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`${file} ${args.join(" ")} failed (${result.status}): ${result.stderr || result.stdout}`);
  }
  return result.stdout;
}

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
  for (const [role, tenantId, companyId, reason] of [
    ["OPERATOR", trialOrgs.aTenant, trialOrgs.aCompany, "ensaio-https-operator-a"],
    ["VIEWER", trialOrgs.bTenant, trialOrgs.bCompany, "ensaio-https-viewer-b"],
  ]) {
    run("java", [
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
    ], env);
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
  if (await page.getByRole("heading", { name: "Seu acesso ainda não foi liberado" }).count()) {
    const identity = await page.evaluate(async () => (await fetch("/api/v1/access/me", { credentials: "include" })).json());
    provisionTrialSubject(identity.issuer, identity.subject);
    await page.goto(`${baseUrl}/receivables`, { waitUntil: "domcontentloaded" });
    await page.getByText("Carregando acesso…").waitFor({ state: "hidden", timeout: 30000 }).catch(() => undefined);
  }
  await page.getByRole("button", { name: "A receber" }).or(page.getByRole("heading", { name: "Contas a receber" })).first().waitFor({ timeout: 45000 });
}

async function readMe(page) {
  return page.evaluate(async () => {
    const response = await fetch("/api/v1/access/me", { credentials: "include" });
    return { status: response.status, body: await response.json().catch(async () => await response.text()) };
  });
}

function waitReady() {
  for (let i = 0; i < 45; i += 1) {
    const result = spawnSync(
      "curl.exe",
      ["-sk", "--resolve", "finance.trial.localhost:18443:127.0.0.1", `${baseUrl}/api/v1/system/info`],
      { encoding: "utf8" },
    );
    if (result.status === 0 && /OIDC/.test(result.stdout ?? "")) {
      return;
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 2000);
  }
  throw new Error("App did not become ready after restart.");
}

const browser = await chromium.launch({
  headless: true,
  args: ["--host-resolver-rules=MAP finance.trial.localhost 127.0.0.1, MAP idp.trial.localhost 127.0.0.1"],
});
const context = await browser.newContext({ viewport: { width: 1280, height: 800 }, ignoreHTTPSErrors: true });
const page = await context.newPage();

try {
  await signInOidc(page);
  const before = await readMe(page);
  if (before.status !== 200 || !before.body?.actorId) {
    throw new Error(`Login did not yield an actor: ${JSON.stringify(before)}`);
  }
  const cookies = await context.cookies();
  const session = cookies.find((item) => item.name === "AFSESSION");
  if (!session) {
    throw new Error("AFSESSION missing before restart.");
  }
  const cookieHash = createHash("sha256").update(session.value).digest("hex");
  const actorId = before.body.actorId;
  const companyA = (before.body.authorizedCompanyDetails ?? []).find((item) => item.name === "Empresa-A-ensaio-HTTPS");
  if (!companyA?.id) {
    throw new Error("Company A missing before restart.");
  }

  run("docker", ["compose", "-p", "actionfinance-https-trial", "-f", composeFile, "restart", "app"]);
  waitReady();

  const after = await readMe(page);
  if (after.status !== 200) {
    throw new Error(`Session did not survive app restart: ${after.status}`);
  }
  if (after.body.actorId !== actorId) {
    throw new Error(`Actor changed after restart: ${after.body.actorId} vs ${actorId}`);
  }
  const companyAfter = (after.body.authorizedCompanyDetails ?? []).find((item) => item.id === companyA.id);
  if (!companyAfter || companyAfter.role !== companyA.role) {
    throw new Error("Company scope was not recovered after restart.");
  }
  if (page.url().includes("/oauth2") || (await page.getByRole("button", { name: "Entrar" }).count())) {
    throw new Error("Restart forced a new login.");
  }

  run(
    "java",
    [
      "-jar",
      hostJar,
      "--spring.profiles.active=access-admin",
      "revoke",
      `--user-id=${actorId}`,
      `--tenant-id=${trialOrgs.aTenant}`,
      `--company-id=${trialOrgs.aCompany}`,
      "--reason=prova-restart-revoke-a",
    ],
    {
      ...process.env,
      ACTIONFINANCE_DATASOURCE_URL: "jdbc:postgresql://127.0.0.1:15439/actionfinance",
      ACTIONFINANCE_RUNTIME_USERNAME: "actionfinance_runtime",
      ACTIONFINANCE_RUNTIME_PASSWORD: process.env.ACTIONFINANCE_TRIAL_RUNTIME_PASSWORD ?? "runtime-change-me",
      ACTIONFINANCE_MIGRATOR_USERNAME: "actionfinance_migrator",
      ACTIONFINANCE_MIGRATOR_PASSWORD: process.env.ACTIONFINANCE_TRIAL_MIGRATOR_PASSWORD ?? "migrator-change-me",
      ACTIONFINANCE_OIDC_ENABLED: "false",
      ACTIONFINANCE_DEMO_AUTH_ENABLED: "false",
    },
  );

  const blocked = await page.evaluate(async (companyId) => {
    const csrf = await (await fetch("/api/v1/access/csrf", { credentials: "include" })).json();
    const create = await fetch(`/api/v1/receivables?companyId=${companyId}`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-XSRF-TOKEN": csrf.token ?? "",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify({
        description: "Deve ser recusado apos revogar",
        amountMinor: 1000,
        currency: "BRL",
        competenceDate: "2026-09-15",
        dueDate: "2026-09-30",
      }),
    });
    return { status: create.status };
  }, companyA.id);
  if (blocked.status !== 403) {
    throw new Error(`Expected 403 after revoke, got ${blocked.status}`);
  }

  await page.getByRole("button", { name: "Sair" }).click();
  await page.getByRole("button", { name: "Entrar" }).or(page.getByText("Não foi possível confirmar a saída")).first().waitFor({ timeout: 20000 });
  if (await page.getByText("Empresa-A-ensaio-HTTPS").count()) {
    throw new Error("Company data still visible after logout.");
  }

  const summary = {
    ok: true,
    actorId,
    companyId: companyA.id,
    cookieName: "AFSESSION",
    cookieSha256: cookieHash,
    restart: "docker compose restart app only",
    recoveredActor: after.body.actorId,
    recoveredCompany: companyAfter.id,
    revokeStatus: blocked.status,
    logout: "enter visible, company hidden",
    reprovisionAfterRestart: false,
  };
  await writeFile(join(shots, "session-restart-log.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
} finally {
  await context.close();
  await browser.close();
}
