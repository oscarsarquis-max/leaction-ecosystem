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
const assertOverflow = process.env.ACTIONFINANCE_OVERFLOW_ASSERT !== "0";
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

function prefixFor(width) {
  if (width <= 400) {
    return "mobile-360";
  }
  if (width <= 800) {
    return "tablet-768";
  }
  return "desktop-1280";
}

async function measureLayout(page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const form = document.querySelector("form.form");
    const card = form?.getBoundingClientRect();
    const header = document.querySelector(".top")?.getBoundingClientRect();
    const fieldsets = [...document.querySelectorAll("form.form fieldset")].map((el, index) => {
      const box = el.getBoundingClientRect();
      return {
        index,
        legend: el.querySelector("legend")?.textContent?.trim() ?? "",
        left: Number(box.left.toFixed(2)),
        right: Number(box.right.toFixed(2)),
        width: Number(box.width.toFixed(2)),
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
      };
    });
    const controls = [...document.querySelectorAll("form.form input, form.form select, form.form textarea")].map((el) => {
      const box = el.getBoundingClientRect();
      const label = el.closest("label")?.childNodes[0]?.textContent?.trim() || el.getAttribute("aria-label") || "";
      return {
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute("type") || "",
        label,
        left: Number(box.left.toFixed(2)),
        right: Number(box.right.toFixed(2)),
        width: Number(box.width.toFixed(2)),
        scrollWidth: el.scrollWidth,
        clientWidth: el.clientWidth,
      };
    });
    return {
      clientWidth: root.clientWidth,
      scrollWidth: root.scrollWidth,
      bodyClientWidth: document.body.clientWidth,
      bodyScrollWidth: document.body.scrollWidth,
      overflowPx: root.scrollWidth - root.clientWidth,
      form: card
        ? {
            left: Number(card.left.toFixed(2)),
            right: Number(card.right.toFixed(2)),
            width: Number(card.width.toFixed(2)),
          }
        : null,
      header: header
        ? {
            top: Number(header.top.toFixed(2)),
            bottom: Number(header.bottom.toFixed(2)),
            height: Number(header.height.toFixed(2)),
          }
        : null,
      fieldsets,
      controls,
      maxControlRight: Number(Math.max(0, ...controls.map((item) => item.right)).toFixed(2)),
      maxFieldsetRight: Number(Math.max(0, ...fieldsets.map((item) => item.right)).toFixed(2)),
    };
  });
}

function assertNoOverflow(layout, label) {
  if (!assertOverflow) {
    return;
  }
  if (layout.scrollWidth !== layout.clientWidth) {
    throw new Error(
      `${label}: document overflow scrollWidth=${layout.scrollWidth} clientWidth=${layout.clientWidth}`,
    );
  }
}

async function captureStages(page, prefix, stage) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(120);
  await page.screenshot({ path: join(shots, `${prefix}-quick-catalog-${stage}-viewport-top.png`), fullPage: false });

  const actions = page.locator("form.form .actions");
  await actions.scrollIntoViewIfNeeded();
  const access = await page.evaluate(() => {
    const header = document.querySelector(".top")?.getBoundingClientRect();
    const actionsBox = document.querySelector("form.form .actions")?.getBoundingClientRect();
    const registrar = [...document.querySelectorAll("form.form button")].find((button) =>
      (button.textContent ?? "").includes("Registrar"),
    );
    const registrarBox = registrar?.getBoundingClientRect();
    return {
      headerTop: header ? Number(header.top.toFixed(2)) : null,
      headerBottom: header ? Number(header.bottom.toFixed(2)) : null,
      actionsTop: actionsBox ? Number(actionsBox.top.toFixed(2)) : null,
      actionsBottom: actionsBox ? Number(actionsBox.bottom.toFixed(2)) : null,
      registrarTop: registrarBox ? Number(registrarBox.top.toFixed(2)) : null,
      registrarBottom: registrarBox ? Number(registrarBox.bottom.toFixed(2)) : null,
      headerPinnedToViewportTop: header ? header.top <= 1 : false,
      actionsReachable:
        Boolean(header && actionsBox && registrarBox) &&
        registrarBox.top >= header.bottom - 1 &&
        registrarBox.bottom <= window.innerHeight + 1,
    };
  });
  if (assertOverflow && !access.actionsReachable) {
    throw new Error(`${prefix} ${stage}: sticky header blocked the register actions.`);
  }
  await page.screenshot({ path: join(shots, `${prefix}-quick-catalog-${stage}-viewport-actions.png`), fullPage: false });

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(120);
  const fullPageName = `${prefix}-quick-catalog-${stage}.png`;
  await page.screenshot({ path: join(shots, fullPageName), fullPage: true });
  return access;
}

async function runWidth(browser, width, height) {
  const prefix = prefixFor(width);
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
  const draftLayout = await measureLayout(page);
  assertNoOverflow(draftLayout, `${prefix} draft`);
  const draftAccess = await captureStages(page, prefix, "draft");

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

  const afterCounterpartyLayout = await measureLayout(page);

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
  const filledLayout = await measureLayout(page);
  assertNoOverflow(filledLayout, `${prefix} filled`);
  const filledAccess = await captureStages(page, prefix, "filled");

  const shouldRegister = width <= 400 || width >= 1280;
  let registered = false;
  if (shouldRegister) {
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
    registered = true;
  }

  await context.close();
  return {
    viewport: prefix,
    width,
    title: `Rascunho rápido ${stamp}`,
    counterparty: `Cliente UI ${stamp}`,
    category: `Categoria UI ${stamp}`,
    registered,
    overflowAsserted: assertOverflow,
    layout: {
      draft: draftLayout,
      afterCounterparty: afterCounterpartyLayout,
      filled: filledLayout,
    },
    headerAccess: {
      draft: draftAccess,
      filled: filledAccess,
    },
    posts: posts.map((item) => ({ path: item.path, bodyHash: item.hash })),
  };
}

const browser = await chromium.launch({
  headless: true,
  args: ["--host-resolver-rules=MAP finance.trial.localhost 127.0.0.1, MAP idp.trial.localhost 127.0.0.1"],
});

try {
  const requested = (process.env.ACTIONFINANCE_CAPTURE_WIDTHS ?? "1280,768,360")
    .split(",")
    .map((item) => Number(item.trim()))
    .filter((item) => item > 0);
  const heights = { 1280: 800, 768: 800, 360: 800 };
  const runs = {};
  for (const width of requested) {
    runs[prefixFor(width)] = await runWidth(browser, width, heights[width] ?? 800);
  }
  const summary = {
    ok: true,
    baseUrl,
    overflowAsserted: assertOverflow,
    widths: requested,
    automation:
      "Playwright OIDC. Cadastro rápido só pela UI do diálogo. Medição scrollWidth/clientWidth em 360/768/1280. Sem POST de catálogo via API substituta.",
    desktop: runs["desktop-1280"] ?? null,
    tablet: runs["tablet-768"] ?? null,
    mobile: runs["mobile-360"] ?? null,
  };
  await writeFile(join(shots, "quick-catalog-log.json"), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(summary, null, 2));
} finally {
  await browser.close();
}
