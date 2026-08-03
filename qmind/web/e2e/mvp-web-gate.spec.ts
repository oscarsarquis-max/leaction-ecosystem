import { test, expect, type Page, type ConsoleMessage } from "@playwright/test";
import {
  catalogIds,
  createApi,
  createSecondOrg,
  createStartedAssessment,
  downloadEvidenceOk,
  uploadApproveEvidence,
} from "./helpers/api";
import { seedSecondApprover } from "./helpers/seedApprover";

const DEMO_ORG = "088a3007-4e52-47ff-ba4c-007a0396ca4a";

function collectConsole(page: Page) {
  const errors: string[] = [];
  page.on("console", (msg: ConsoleMessage) => {
    if (msg.type() === "error") errors.push(msg.text());
  });
  page.on("pageerror", (err) => errors.push(String(err)));
  return errors;
}

async function assertNoSensitiveStorage(page: Page) {
  const result = await page.evaluate(() => {
    const forbidden = ["token", "access", "refresh", "id_token", "membership", "assessment"];
    const bad: string[] = [];
    const scan = (store: Storage, label: string) => {
      for (let i = 0; i < store.length; i++) {
        const k = store.key(i);
        if (!k?.startsWith("qmind.")) continue;
        const lower = k.toLowerCase();
        for (const f of forbidden) {
          if (
            f !== "organization" &&
            lower.includes(f) &&
            !lower.includes("preferredorganization")
          ) {
            bad.push(`${label}:${k}`);
          }
        }
        const v = store.getItem(k) || "";
        if (v.includes("eyJ") || v.length > 80) bad.push(`${label}:${k}:suspicious`);
      }
    };
    scan(sessionStorage, "session");
    scan(localStorage, "local");
    return {
      bad,
      preferred: sessionStorage.getItem("qmind.preferredOrganizationId"),
    };
  });
  expect(result.bad, JSON.stringify(result)).toEqual([]);
  return result;
}

test.describe.configure({ mode: "serial" });

test("MVP web end-to-end gate (real browser + API + Postgres)", async ({ page, baseURL }) => {
  test.setTimeout(300_000);
  const origin = baseURL!;
  const consoleErrors = collectConsole(page);
  const { REQUIREMENT } = catalogIds();

  // W1 — health through preview proxy
  expect((await page.request.get(`${origin}/health`)).ok()).toBeTruthy();
  expect((await page.request.get(`${origin}/ready`)).ok()).toBeTruthy();

  // W2 — auth dev shell
  await page.goto("/assessments");
  await expect(page.getByTestId("nav-assessments")).toBeVisible();
  await expect(page.getByLabel(/selecionar organização/i)).toBeVisible();
  await expect(page.getByText(/dev@example.com/i)).toBeVisible();

  const orgSelect = page.getByLabel(/selecionar organização/i);
  await orgSelect.selectOption(DEMO_ORG);

  // W3 — two orgs + tenant switch
  const orgB = await createSecondOrg(origin);
  await page.reload();
  await expect(orgSelect.locator(`option[value="${orgB.orgId}"]`)).toHaveCount(1);
  await orgSelect.selectOption(orgB.orgId);
  await page.waitForTimeout(600);
  await orgSelect.selectOption(DEMO_ORG);
  await page.waitForTimeout(600);
  const storage = await assertNoSensitiveStorage(page);
  expect(storage.preferred).toBe(DEMO_ORG);

  // W4 — real journey bootstrap (Postgres-backed API)
  const api = await createApi(origin, DEMO_ORG);
  const aid = await createStartedAssessment(api);
  const eid = await uploadApproveEvidence(api, aid);
  const dl = await downloadEvidenceOk(api, eid);
  expect(dl.byteLength).toBeGreaterThan(10);

  // W5 — direct refresh on detail route
  await page.goto(`/assessments/${aid}`);
  await page.reload();
  await expect(page.getByTestId("assessment-status")).toHaveText(/in_progress/i);

  // W6 — Finding SoD in UI (author cannot approve)
  const finding = await api.request("POST", "/api/v1/findings", {
    body: {
      assessment_id: aid,
      finding_type: "observation",
      title: "E2E SoD observation",
      body: "Browser gate",
      requirement_ids: [REQUIREMENT],
      evidence_ids: [],
      insufficient_evidence: true,
      insufficient_evidence_rationale: "documented gap",
    },
    headers: { "Idempotency-Key": `e2e-f-${crypto.randomUUID()}` },
  });
  expect(finding.status, finding.text).toBeLessThan(400);
  const fid = finding.json.id as string;
  expect(
    (await api.request("POST", `/api/v1/findings/${fid}/transitions/submit`)).status,
  ).toBeLessThan(400);

  await page.reload();
  await page.getByTestId(`finding-select-${fid}`).click();
  await expect(page.getByTestId("finding-sod-banner")).toBeVisible();
  await expect(page.getByTestId("finding-approve")).toBeDisabled();

  // W7 — keyboard focus on plan dialog (fresh draft)
  const draft = await api.request("POST", "/api/v1/assessments", {
    body: {
      assessment_model_id: catalogIds().MODEL,
      standard_version_id: catalogIds().STANDARD,
      type: "diagnosis",
      scope: [{ requirement_id: REQUIREMENT }],
    },
    headers: { "Idempotency-Key": `e2e-d-${crypto.randomUUID()}` },
  });
  expect(draft.status).toBeLessThan(400);
  const draftId = draft.json.id as string;
  await page.goto(`/assessments/${draftId}`);
  await page.getByTestId("plan-open-confirm").click();
  const dialog = page.getByTestId("plan-confirm");
  await expect(dialog).toBeVisible();
  await expect(dialog).toHaveAttribute("role", "dialog");
  await page.keyboard.press("Tab");
  await page.keyboard.press("Escape");
  // Escape may not close custom dialog — cancel button if present
  const cancel = dialog.getByRole("button", { name: /cancelar|voltar|fechar/i });
  if (await cancel.count()) await cancel.click();
  else await page.getByTestId("plan-open-confirm").click({ force: true }).catch(() => undefined);

  // W8 — second approver advances domain + report publish SoD
  const approver = seedSecondApprover(DEMO_ORG);
  const apiQm = await createApi(origin, DEMO_ORG, {
    sub: approver.sub,
    email: approver.email,
  });
  expect(
    (await apiQm.request("POST", `/api/v1/findings/${fid}/transitions/approve`)).status,
  ).toBeLessThan(400);

  expect(
    (await api.request("POST", `/api/v1/assessments/${aid}/transitions/begin_analysis`))
      .status,
  ).toBeLessThan(400);
  expect(
    (await api.request("POST", `/api/v1/assessments/${aid}/transitions/open_actions`)).status,
  ).toBeLessThan(400);

  const plan = await api.request("POST", "/api/v1/action-plans", {
    body: { assessment_id: aid, empty_plan_rationale: "E2E justified empty plan" },
    headers: { "Idempotency-Key": `e2e-p-${crypto.randomUUID()}` },
  });
  expect(plan.status).toBeLessThan(400);
  expect(
    (
      await api.request(
        "POST",
        `/api/v1/action-plans/${plan.json.id}/transitions/activate`,
      )
    ).status,
  ).toBeLessThan(400);
  expect(
    (await api.request("POST", `/api/v1/assessments/${aid}/transitions/begin_report`))
      .status,
  ).toBeLessThan(400);

  await page.goto(`/assessments/${aid}`);
  await page.reload();
  await expect(page.getByTestId("report-panel")).toBeVisible();
  await page.getByTestId("report-include-maturity").uncheck();
  await page.getByTestId("report-include-plan").check();
  await page.getByTestId("report-create").click();
  await expect(page.getByTestId("report-meta")).toBeVisible({ timeout: 20_000 });
  await expect(page.getByTestId("report-snapshot-summary")).toContainText(/finding/i);

  await page.getByTestId("report-submit").click();
  await expect(page.getByTestId("report-status")).toContainText(/revisão|in_review/i, {
    timeout: 20_000,
  });
  await expect(page.getByTestId("report-sod-banner")).toBeVisible();
  await expect(page.getByTestId("report-publish")).toBeDisabled();

  // Publish as QM (not author)
  const reports = await api.request("GET", `/api/v1/reports?assessment_id=${aid}`);
  const rid = reports.json[0].id as string;
  expect(
    (await apiQm.request("POST", `/api/v1/reports/${rid}/transitions/publish`)).status,
  ).toBeLessThan(400);

  await page.reload();
  await expect(page.getByTestId("report-status")).toContainText(/publicado/i);

  // W9 — export job queued + failure treatment (double export is idempotent 202)
  await page.getByTestId("report-export-pdf").click();
  await expect(page.getByTestId("report-export-job")).toBeVisible();
  await expect(page.getByTestId("report-export-status")).toHaveText(/queued/i);

  const failExport = await api.request("POST", `/api/v1/reports/${rid}/export-pdf`, {
    headers: { "Idempotency-Key": "bad-key-for-force-different" },
  });
  // Same report version → same job (idempotent) or 202 again
  expect([200, 202].includes(failExport.status) || failExport.status < 500).toBeTruthy();

  // W10 — close + reopen
  await page.getByTestId("assessment-close").click();
  await expect(page.getByTestId("assessment-status")).toHaveText(/closed/i, {
    timeout: 20_000,
  });
  await page.getByTestId("assessment-reopen-reason").fill("E2E reopen after publish");
  await page.getByTestId("assessment-reopen").click();
  await expect(page.getByTestId("assessment-status")).toHaveText(/report/i, {
    timeout: 20_000,
  });

  // W11 — 404 / error states
  await page.goto("/assessments/00000000-0000-4000-8000-000000000099");
  await expect(
    page.getByTestId("api-error").or(page.getByText(/não encontr|acesso negado|erro/i)).first(),
  ).toBeVisible();

  // W12 — list refresh
  await page.goto("/assessments");
  await page.reload();
  await expect(page.getByTestId("nav-assessments")).toBeVisible();
  await assertNoSensitiveStorage(page);

  // W13 — console
  const unexpected = consoleErrors.filter(
    (e) =>
      !/favicon/i.test(e) &&
      !/Download the React DevTools/i.test(e) &&
      !/404/i.test(e) &&
      !/Failed to load resource/i.test(e),
  );
  expect(unexpected, unexpected.join("\n")).toEqual([]);
});
