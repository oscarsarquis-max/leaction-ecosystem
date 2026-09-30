import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
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
const image = process.env.ACTIONFINANCE_IMAGE ?? "actionfinance:local-prm006";
const runId = `af-restore-sess-${Date.now().toString(36)}`;
const created = [];

function run(file, args, env = process.env) {
  const result = spawnSync(file, args, { env, encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(`${file} ${args.join(" ")} failed (${result.status}): ${result.stderr || result.stdout}`);
  }
  return result.stdout;
}

function provisionTrialSubject(issuer, subject, orgs) {
  const env = {
    ...process.env,
    ACTIONFINANCE_DATASOURCE_URL: "jdbc:postgresql://127.0.0.1:15439/actionfinance",
    ACTIONFINANCE_RUNTIME_USERNAME: "actionfinance_runtime",
    ACTIONFINANCE_RUNTIME_PASSWORD: process.env.ACTIONFINANCE_TRIAL_RUNTIME_PASSWORD ?? "runtime-change-me",
    ACTIONFINANCE_MIGRATOR_USERNAME: "actionfinance_migrator",
    ACTIONFINANCE_MIGRATOR_PASSWORD: process.env.ACTIONFINANCE_TRIAL_MIGRATOR_PASSWORD ?? "migrator-change-me",
    ACTIONFINANCE_OIDC_ENABLED: "false",
    ACTIONFINANCE_DEMO_AUTH_ENABLED: "false",
  };
  for (const [role, tenantId, companyId, reason] of [
    ["OPERATOR", orgs.aTenant, orgs.aCompany, "ensaio-https-operator-a"],
    ["VIEWER", orgs.bTenant, orgs.bCompany, "ensaio-https-viewer-b"],
  ]) {
    run("java", [
      "-jar", hostJar, "--spring.profiles.active=access-admin", "provision",
      "--display-name=Operadora-ensaio-HTTPS", `--issuer=${issuer}`, `--subject=${subject}`,
      `--tenant-id=${tenantId}`, `--company-id=${companyId}`, `--role=${role}`, `--reason=${reason}`,
    ], env);
  }
}

async function signInOidc(page, orgs) {
  await page.goto(`${baseUrl}/`, { waitUntil: "domcontentloaded" });
  await page.getByText("Carregando acesso…").waitFor({ state: "hidden", timeout: 30000 }).catch(() => undefined);
  const enter = page.getByRole("button", { name: "Entrar" });
  if (await enter.count()) {
    await enter.click();
    await page.getByRole("heading", { name: "Seu acesso ainda não foi liberado" })
      .or(page.getByRole("button", { name: "A receber" }))
      .first()
      .waitFor({ timeout: 45000 });
  }
  if (await page.getByRole("heading", { name: "Seu acesso ainda não foi liberado" }).count()) {
    const identity = await page.evaluate(async () => (await fetch("/api/v1/access/me", { credentials: "include" })).json());
    provisionTrialSubject(identity.issuer, identity.subject, orgs);
    await page.goto(`${baseUrl}/receivables`, { waitUntil: "domcontentloaded" });
    await page.getByText("Carregando acesso…").waitFor({ state: "hidden", timeout: 30000 }).catch(() => undefined);
  }
  await page.getByRole("button", { name: "A receber" }).or(page.getByRole("heading", { name: "Contas a receber" })).first().waitFor({ timeout: 45000 });
}

function composeExec(args) {
  return run("docker", ["compose", "-p", "actionfinance-https-trial", "-f", composeFile, "exec", "-T", "postgres", ...args]);
}

const orgs = {
  aTenant: process.env.ACTIONFINANCE_TRIAL_TENANT_A ?? "d6f19ecc-1832-4c50-982b-76e7e93f8f3d",
  aCompany: process.env.ACTIONFINANCE_TRIAL_COMPANY_A ?? "23cc1d84-4554-4d07-b06f-cd5529fa12fd",
  bTenant: process.env.ACTIONFINANCE_TRIAL_TENANT_B ?? "65d614c0-b209-43fc-aaec-c0c5c095dad8",
  bCompany: process.env.ACTIONFINANCE_TRIAL_COMPANY_B ?? "a3e2ef38-fe88-4c8c-aa9c-552421dbe958",
};

const browser = await chromium.launch({
  headless: true,
  args: ["--host-resolver-rules=MAP finance.trial.localhost 127.0.0.1, MAP idp.trial.localhost 127.0.0.1"],
});
const context = await browser.newContext({ ignoreHTTPSErrors: true });
const page = await context.newPage();

try {
  await signInOidc(page, orgs);
  const me = await page.evaluate(async () => (await fetch("/api/v1/access/me", { credentials: "include" })).json());
  const session = (await context.cookies()).find((item) => item.name === "AFSESSION");
  if (!session) {
    throw new Error("AFSESSION missing before dump.");
  }
  const cookieHash = createHash("sha256").update(session.value).digest("hex");

  const counts = composeExec([
    "psql", "-U", "postgres", "-d", "actionfinance", "-tAc",
    "select (select count(*) from actionfinance.financial_title) || '|' || (select count(*) from actionfinance.app_user) || '|' || (select count(*) from actionfinance.company_membership) || '|' || (select count(*) from actionfinance.access_admin_audit) || '|' || (select count(*) from actionfinance.SPRING_SESSION)",
  ]).trim();

  const dump = run("docker", [
    "compose", "-p", "actionfinance-https-trial", "-f", composeFile, "exec", "-T", "postgres",
    "pg_dump", "-U", "postgres", "-d", "actionfinance", "--schema=actionfinance", "--no-owner", "--no-acl",
  ]);

  const trialPg = run("docker", ["compose", "-p", "actionfinance-https-trial", "-f", composeFile, "ps", "-q", "postgres"]).trim();
  const network = run("docker", ["inspect", "-f", "{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}", trialPg]).trim();
  const restoreName = `${runId}-pg`;
  const appName = `${runId}-app`;
  run("docker", [
    "run", "-d", "--name", restoreName, "--network", network,
    "--label", "com.actionfinance.project=actionfinance",
    "--label", "com.actionfinance.role=restore-session-proof",
    "-e", "POSTGRES_PASSWORD=verify-only",
    "-e", "POSTGRES_DB=actionfinance",
    "postgres:17.6",
  ]);
  created.push(restoreName);
  for (let i = 0; i < 40; i += 1) {
    const ready = spawnSync("docker", ["exec", restoreName, "pg_isready", "-U", "postgres", "-d", "actionfinance"], { encoding: "utf8" });
    if (ready.status === 0) {
      break;
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 500);
  }
  const bootstrap = [
    "CREATE ROLE actionfinance_migrator LOGIN PASSWORD 'migrator-change-me';",
    "CREATE ROLE actionfinance_runtime LOGIN PASSWORD 'runtime-change-me';",
    "GRANT CONNECT ON DATABASE actionfinance TO actionfinance_migrator;",
    "GRANT CONNECT ON DATABASE actionfinance TO actionfinance_runtime;",
    "REVOKE ALL ON SCHEMA public FROM PUBLIC;",
  ].join("\n");
  spawnSync("docker", ["exec", "-i", restoreName, "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "actionfinance"], {
    input: bootstrap,
    encoding: "utf8",
  });
  const restored = spawnSync("docker", ["exec", "-i", restoreName, "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "actionfinance"], {
    input: dump,
    encoding: "utf8",
  });
  if (restored.status !== 0) {
    throw new Error(`Restore dump failed: ${restored.stderr}`);
  }
  const priv = spawnSync("docker", ["exec", "-i", restoreName, "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "actionfinance"], {
    input: readFileSync(join(root, "scripts", "dev", "restore-runtime-privileges.sql"), "utf8"),
    encoding: "utf8",
  });
  if (priv.status !== 0) {
    throw new Error(`Restore privileges failed: ${priv.stderr}`);
  }

  const certs = join(root, "ops", "compose", "https-trial", "certs", "truststore.p12");
  run("docker", [
    "run", "-d", "--name", appName, "--network", network,
    "-p", "127.0.0.1:18094:8091",
    "--label", "com.actionfinance.project=actionfinance",
    "--label", "com.actionfinance.role=restore-session-proof",
    "-e", "SPRING_PROFILES_ACTIVE=production",
    "-e", `ACTIONFINANCE_DATASOURCE_URL=jdbc:postgresql://${restoreName}:5432/actionfinance`,
    "-e", "ACTIONFINANCE_RUNTIME_USERNAME=actionfinance_runtime",
    "-e", "ACTIONFINANCE_RUNTIME_PASSWORD=runtime-change-me",
    "-e", "ACTIONFINANCE_MIGRATOR_USERNAME=actionfinance_migrator",
    "-e", "ACTIONFINANCE_MIGRATOR_PASSWORD=migrator-change-me",
    "-e", "ACTIONFINANCE_PUBLIC_ORIGIN=https://finance.trial.localhost:18443",
    "-e", "ACTIONFINANCE_OIDC_ENABLED=true",
    "-e", "ACTIONFINANCE_OIDC_ISSUER=https://idp.trial.localhost:18444/default",
    "-e", "ACTIONFINANCE_OIDC_CLIENT_ID=actionfinance",
    "-e", "ACTIONFINANCE_OIDC_CLIENT_SECRET=trial-only-not-for-production",
    "-e", "ACTIONFINANCE_OIDC_REDIRECT_URI=https://finance.trial.localhost:18443/login/oauth2/code/actionfinance",
    "-e", "ACTIONFINANCE_TRUST_FORWARDED_HEADERS=false",
    "-e", "JAVA_TOOL_OPTIONS=-Djavax.net.ssl.trustStore=/certs/truststore.p12 -Djavax.net.ssl.trustStorePassword=trial-only-not-for-production -Djavax.net.ssl.trustStoreType=PKCS12",
    "-v", `${certs}:/certs/truststore.p12:ro`,
    image,
  ]);
  created.push(appName);

  let ready = false;
  for (let i = 0; i < 45; i += 1) {
    const info = spawnSync("curl.exe", ["-s", "http://127.0.0.1:18094/api/v1/system/info"], { encoding: "utf8" });
    if (info.status === 0 && /OIDC/.test(info.stdout ?? "")) {
      ready = true;
      break;
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 2000);
  }
  if (!ready) {
    throw new Error("Restored-app instance did not become ready on :18094.");
  }

  const beforeInvalidate = spawnSync("curl.exe", [
    "-s", "-o", "-", "-w", "%{http_code}",
    "http://127.0.0.1:18094/api/v1/access/me",
    "-H", `Cookie: AFSESSION=${session.value}`,
  ], { encoding: "utf8" });
  const beforeBody = beforeInvalidate.stdout ?? "";
  const beforeStatus = beforeBody.slice(-3);
  const beforeJson = beforeBody.slice(0, -3);
  if (beforeStatus !== "200" || !beforeJson.includes(me.actorId)) {
    throw new Error(`Restored session cookie did not authenticate before invalidate: ${beforeStatus}`);
  }

  run("powershell", [
    "-NoProfile",
    "-File",
    join(root, "scripts", "ops", "invalidate-sessions.ps1"),
    "-ContainerName",
    restoreName,
    "-ContainerUser",
    "actionfinance_runtime",
    "-ContainerPassword",
    "runtime-change-me",
  ]);

  const afterInvalidate = spawnSync("curl.exe", [
    "-s", "-o", "-", "-w", "%{http_code}",
    "http://127.0.0.1:18094/api/v1/access/me",
    "-H", `Cookie: AFSESSION=${session.value}`,
  ], { encoding: "utf8" });
  const afterStatus = (afterInvalidate.stdout ?? "").slice(-3);
  if (afterStatus === "200") {
    throw new Error("Cookie still authenticated after operational session invalidation.");
  }

  const afterCounts = run("docker", [
    "exec", restoreName, "psql", "-U", "postgres", "-d", "actionfinance", "-tAc",
    "select (select count(*) from actionfinance.financial_title) || '|' || (select count(*) from actionfinance.app_user) || '|' || (select count(*) from actionfinance.company_membership) || '|' || (select count(*) from actionfinance.access_admin_audit) || '|' || (select count(*) from actionfinance.SPRING_SESSION)",
  ]).trim();
  const [titles, users, memberships, audit, sessions] = afterCounts.split("|");
  const [srcTitles, srcUsers, srcMemberships, srcAudit] = counts.split("|");
  if (titles !== srcTitles || users !== srcUsers || memberships !== srcMemberships || audit !== srcAudit) {
    throw new Error(`Counts changed after invalidate. before=${counts} after=${afterCounts}`);
  }
  if (sessions !== "0") {
    throw new Error(`Sessions remained after invalidate: ${sessions}`);
  }

  const summary = {
    ok: true,
    actorId: me.actorId,
    cookieSha256: cookieHash,
    sourceCounts: counts,
    restoredCountsAfterInvalidate: afterCounts,
    cookieBeforeInvalidate: beforeStatus,
    cookieAfterInvalidate: afterStatus,
    restoredOver: "disposable postgres+app, not trial/dev volumes",
  };
  await writeFile(join(shots, "restore-session-invalidate-log.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
} finally {
  await context.close();
  await browser.close();
  for (const name of created.reverse()) {
    spawnSync("docker", ["rm", "-f", name], { encoding: "utf8" });
  }
}
