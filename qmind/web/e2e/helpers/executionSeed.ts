import { expect } from "@playwright/test";
import { catalogIds, createApi, createStartedAssessment, type ApiClient } from "./api";
import { seedSecondApprover } from "./seedApprover";

function idem(prefix: string) {
  return { "Idempotency-Key": `${prefix}-${crypto.randomUUID()}` };
}

export async function post(
  api: ApiClient,
  path: string,
  body?: unknown,
  prefix = "e2e",
) {
  const res = await api.request("POST", path, {
    body,
    headers: body ? idem(prefix) : undefined,
  });
  expect(res.status, `${path} → ${res.text}`).toBeLessThan(400);
  return res.json;
}

/**
 * Seeds one action item that is ready to be executed on the board: an
 * assessment with an approved finding, an active action plan and an owner.
 * Seeding through the API keeps the browser assertions about the workspace
 * itself instead of re-testing the audit flow that other specs already cover.
 */
export async function seedExecutableAction(api: ApiClient, description: string) {
  const { REQUIREMENT } = catalogIds();
  const assessmentId = await createStartedAssessment(api);

  const finding = await post(
    api,
    "/api/v1/findings",
    {
      assessment_id: assessmentId,
      finding_type: "observation",
      title: "Registro de ocorrências sem padrão",
      body: "Execução ágil e2e",
      requirement_ids: [REQUIREMENT],
      evidence_ids: [],
      insufficient_evidence: true,
      insufficient_evidence_rationale: "lacuna documentada",
    },
    "e2e-find",
  );
  await post(api, `/api/v1/findings/${finding.id}/transitions/submit`);

  const approver = seedSecondApprover(api.orgId);
  const apiQm = await createApi(api.baseURL, api.orgId, {
    sub: approver.sub,
    email: approver.email,
  });
  await post(apiQm, `/api/v1/findings/${finding.id}/transitions/approve`);

  await post(api, `/api/v1/assessments/${assessmentId}/transitions/begin_analysis`);
  await post(api, `/api/v1/assessments/${assessmentId}/transitions/open_actions`);

  const plan = await post(
    api,
    "/api/v1/action-plans",
    { assessment_id: assessmentId },
    "e2e-plan",
  );
  const dueAt = new Date(Date.now() + 14 * 864e5).toISOString();
  const item = await post(
    api,
    `/api/v1/action-plans/${plan.id}/items`,
    {
      finding_id: finding.id,
      action_kind: "improvement",
      description,
      owner_membership_id: api.membershipId,
      due_at: dueAt,
      efficacy_required: false,
    },
    "e2e-item",
  );
  await post(api, `/api/v1/action-plans/${plan.id}/transitions/activate`);
  return { assessmentId, actionPlanId: plan.id as string, actionItemId: item.id as string };
}

export async function seedSprintWithCard(api: ApiClient, actionItemId: string) {
  const squad = await post(
    api,
    "/api/v1/organizations/current/agile/squads",
    {
      name: `Squad execução ${Date.now()}`,
      purpose: "Executar melhorias",
      value_owner_membership_id: api.membershipId,
    },
    "e2e-squad",
  );
  const startsAt = new Date().toISOString();
  const sprint = await post(
    api,
    "/api/v1/organizations/current/agile/sprints",
    {
      squad_id: squad.id,
      name: `Sprint execução ${Date.now()}`,
      goal: "Concluir a ação piloto",
      starts_at: startsAt,
      ends_at: new Date(Date.now() + 14 * 864e5).toISOString(),
    },
    "e2e-sprint",
  );
  await post(
    api,
    `/api/v1/organizations/current/agile/sprints/${sprint.id}/cards`,
    { action_item_id: actionItemId },
    "e2e-card",
  );
  await post(
    api,
    `/api/v1/organizations/current/agile/sprints/${sprint.id}/activate`,
  );
  const ceremony = await post(
    api,
    "/api/v1/agenda/events",
    {
      title: "Daily da sprint de execução",
      event_type: "daily_check_in",
      starts_at: startsAt,
      sprint_id: sprint.id,
    },
    "e2e-agenda",
  );
  return {
    squadId: squad.id as string,
    squadName: squad.name as string,
    sprintId: sprint.id as string,
    sprintName: sprint.name as string,
    ceremonyTitle: ceremony.title as string,
  };
}
