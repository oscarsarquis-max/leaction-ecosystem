import { test, expect } from "@playwright/test";
import { createApi } from "./helpers/api";
import { signIn, visit } from "./helpers/executionSession";

/**
 * ISOI-009: Evolution panel shows Execution Intelligence from Core,
 * requests a new analysis, and never auto-mutates case/efficacy.
 * Requires Core with OI reachable (same as other execution e2e).
 */
test("execution intelligence: interpret, stale after change, no auto lifecycle", async ({
  page,
  baseURL,
}) => {
  test.setTimeout(300_000);
  const origin = baseURL!;

  const who = await signIn(page, "/execution");
  const api = await createApi(origin, who.orgId, { sub: who.sub, email: who.email });

  const profile = await api.request("PATCH", "/api/v1/organizations/current/profile", {
    body: {
      trade_name: "Acme EI Playwright",
      summary: "Organização de teste para Execution Intelligence",
      industry: "Saúde",
      business_model: "b2b",
      employee_range: "11-50",
      unit_count: 1,
      certification_status: "none",
      quality_structure: "formal",
    },
  });
  expect(profile.status).toBe(200);

  const created = await api.request(
    "POST",
    "/api/v1/organizations/current/improvement-cases",
    {
      body: {
        problem_statement: `EI Playwright atraso ${Date.now()}`,
        impact_statement: "Cliente espera demais",
        related_process: "Atendimento",
      },
    },
  );
  expect(created.status).toBeLessThan(400);
  const caseId = created.json.id as string;

  const analysis = await api.request(
    "POST",
    `/api/v1/organizations/current/improvement-cases/${caseId}/analysis-runs`,
    { body: {} },
  );
  expect(analysis.status).toBe(201);
  const finding = analysis.json.analysis?.findings?.[0];
  expect(finding?.code, JSON.stringify(analysis.json.analysis)).toBeTruthy();
  const memberships = await api.request(
    "GET",
    "/api/v1/organizations/me/memberships",
  );
  const owner = memberships.json.find(
    (membership: { organization_id: string }) =>
      membership.organization_id === who.orgId,
  );
  expect(owner?.id).toBeTruthy();
  const action = await api.request(
    "POST",
    `/api/v1/organizations/current/improvement-cases/${caseId}/analysis-runs/${analysis.json.id}/findings/${finding.code}/actions`,
    {
      body: {
        owner_membership_id: owner.id,
        due_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      },
    },
  );
  expect(action.status).toBe(201);

  await visit(page, `/improvement-cases/${caseId}`);
  const panel = page.getByTestId("ic-evo-execution-intelligence");
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("Interpretação QMind OI");
  await expect(panel.getByTestId("ic-ei-never")).toBeVisible();

  const interpret = panel.getByRole("button", {
    name: /Interpretar execução|Atualizar interpretação/i,
  });
  await interpret.click();
  await expect(panel.getByTestId("ic-ei-result")).toBeVisible({ timeout: 60_000 });
  await expect(panel.getByTestId("ic-ei-signal").first()).toBeVisible();
  await expect(panel).toContainText("Prazos");
  await expect(panel).toContainText("Prazo de ação pede atenção");
  await expect(panel).toContainText("Fatos considerados");
  await expect(panel).toContainText("Base ISO 9001");
  await expect(panel).toContainText("Próximo passo recomendado");
  await expect(panel).toContainText("validação humana");
  await expect(panel).not.toContainText(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}/i);
  await expect(panel).not.toContainText(/execution\./);

  const before = (
    await api.request(
      "GET",
      `/api/v1/organizations/current/improvement-cases/${caseId}`,
    )
  ).json;
  const statusBefore = before.status;

  // Change a fact on the case so latest analysis must become stale.
  await api.request(
    "PATCH",
    `/api/v1/organizations/current/improvement-cases/${caseId}`,
    {
      body: {
        impact_statement: `Impacto revisado ${Date.now()}`,
      },
    },
  );

  await visit(page, `/improvement-cases/${caseId}`);
  const panel2 = page.getByTestId("ic-evo-execution-intelligence");
  await expect(panel2.getByTestId("ic-ei-result")).toBeVisible();
  await expect(panel2.getByTestId("ic-ei-stale")).toBeVisible();
  await panel2.getByTestId("ic-ei-run").click();
  await expect(panel2.getByTestId("ic-ei-current")).toBeVisible({
    timeout: 60_000,
  });
  await expect(panel2.getByTestId("ic-ei-history").locator("li")).toHaveCount(2);
  await expect(panel2).not.toContainText(/execution\./);

  const after = (
    await api.request(
      "GET",
      `/api/v1/organizations/current/improvement-cases/${caseId}`,
    )
  ).json;
  expect(after.status).toBe(statusBefore);
});
