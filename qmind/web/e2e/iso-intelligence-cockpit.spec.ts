import { test, expect, type Page } from "@playwright/test";
import { createApi } from "./helpers/api";
import { signIn, visit } from "./helpers/executionSession";

/**
 * ISOI-010: Cockpit read model — synthesis, filter, drill-down, refresh
 * without calling OI execution-intelligence POST.
 *
 * Self-contained: seeds profile + cases + overdue action + impediment via API
 * (does not require Python seed_cockpit_demo_local.py). Core must be up; the
 * analysis-run step needs OI the same way execution-intelligence.spec.ts does.
 */

const EI_POST =
  /\/api\/v1\/organizations\/current\/improvement-cases\/[^/]+\/execution-intelligence\/runs/;

function spyOiExecutionIntelligencePosts(page: Page) {
  const posts: string[] = [];
  page.on("request", (req) => {
    if (req.method() !== "POST") return;
    const url = req.url();
    if (EI_POST.test(url) || url.includes("/execution-intelligence/runs")) {
      posts.push(url);
    }
  });
  return posts;
}

async function seedCockpitCases(
  api: Awaited<ReturnType<typeof createApi>>,
  stamp: number,
) {
  const profile = await api.request("PATCH", "/api/v1/organizations/current/profile", {
    body: {
      trade_name: "Acme Cockpit Playwright",
      summary: "Organização de teste para ISO Intelligence Cockpit",
      industry: "Saúde",
      business_model: "b2b",
      employee_range: "11-50",
      unit_count: 1,
      certification_status: "none",
      quality_structure: "formal",
    },
  });
  expect(profile.status).toBe(200);

  const overdueCase = await api.request(
    "POST",
    "/api/v1/organizations/current/improvement-cases",
    {
      body: {
        problem_statement: `Cockpit E2E bloqueio ${stamp}`,
        impact_statement: "Parada de atendimento",
        related_process: "Atendimento",
      },
    },
  );
  expect(overdueCase.status).toBeLessThan(400);
  const overdueCaseId = overdueCase.json.id as string;

  const analysis = await api.request(
    "POST",
    `/api/v1/organizations/current/improvement-cases/${overdueCaseId}/analysis-runs`,
    { body: {} },
  );
  expect(analysis.status).toBe(201);
  const finding = analysis.json.analysis?.findings?.[0];
  expect(finding?.code, JSON.stringify(analysis.json.analysis)).toBeTruthy();

  const action = await api.request(
    "POST",
    `/api/v1/organizations/current/improvement-cases/${overdueCaseId}/analysis-runs/${analysis.json.id}/findings/${finding.code}/actions`,
    {
      body: {
        owner_membership_id: api.membershipId,
        due_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      },
    },
  );
  expect(action.status).toBe(201);
  const actionItemId = action.json.id as string;

  await api.request(
    "PATCH",
    `/api/v1/organizations/current/improvement-cases/${overdueCaseId}`,
    { body: { status: "acting" } },
  );

  const impediment = await api.request(
    "POST",
    `/api/v1/organizations/current/actions/${actionItemId}/impediments`,
    {
      body: {
        title: "Sem recurso alocado",
        description: "Impedimento E2E do Cockpit",
        severity: "high",
      },
    },
  );
  expect(impediment.status, impediment.text).toBeLessThan(400);

  const plain = await api.request(
    "POST",
    "/api/v1/organizations/current/improvement-cases",
    {
      body: {
        problem_statement: `Cockpit E2E fila ${stamp}`,
        impact_statement: "Caso complementar na fila",
        related_process: "Qualidade",
      },
    },
  );
  expect(plain.status).toBeLessThan(400);

  return { overdueCaseId, plainCaseId: plain.json.id as string };
}

test("iso intelligence cockpit: synthesis, filter, drill-down, refresh without OI POST", async ({
  page,
  baseURL,
}) => {
  test.setTimeout(300_000);
  const origin = baseURL!;
  const oiPosts = spyOiExecutionIntelligencePosts(page);
  const stamp = Date.now();

  const who = await signIn(page, "/execution");
  const api = await createApi(origin, who.orgId, {
    sub: who.sub,
    email: who.email,
  });
  await seedCockpitCases(api, stamp);

  await visit(page, "/cockpit");
  await expect(page.getByTestId("cockpit-page")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("cockpit-summary")).toBeVisible();
  await expect(page.getByTestId("cockpit-refresh")).toBeVisible();

  const queue = page.getByTestId("cockpit-queue");
  const emptyOrg = page.getByText(/Nenhum caso de melhoria nesta organização/i);
  await expect(queue.or(emptyOrg)).toBeVisible();
  await expect(queue).toBeVisible();
  await expect(page.getByTestId("cockpit-queue-row").first()).toBeVisible();

  // Filter immediate attention (URL-backed synthesis control).
  await page.getByTestId("cockpit-filter-immediate").click();
  await expect(page).toHaveURL(/priority_band=immediate_attention/);
  await expect(page.getByTestId("cockpit-filter-active")).toBeVisible();
  await expect(
    page
      .getByTestId("cockpit-queue-row")
      .first()
      .or(page.getByTestId("cockpit-empty-filter")),
  ).toBeVisible();

  // Drill-down: open a case from the full queue (filters may exclude all rows
  // when is_overdue is not yet flipped by Core — still assert the control).
  await page.getByTestId("cockpit-clear-filters").click();
  await expect(page.getByTestId("cockpit-queue-row").first()).toBeVisible();
  await page.getByTestId("cockpit-open-case").first().click();

  await expect(page).toHaveURL(/\/improvement-cases\//);
  await expect(page.getByTestId("improvement-case-detail")).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByTestId("ic-section-evolution")).toBeVisible();

  // Return to cockpit with filter in the URL — preservation contract.
  await visit(page, "/cockpit?priority_band=immediate_attention");
  await expect(page.getByTestId("cockpit-page")).toBeVisible();
  await expect(page).toHaveURL(/priority_band=immediate_attention/);
  await expect(page.getByTestId("cockpit-filter-active")).toBeVisible();
  await expect(page.getByTestId("cockpit-filter-immediate")).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  const postsBefore = oiPosts.length;
  await page.getByTestId("cockpit-refresh").click();
  await expect(page.getByTestId("cockpit-summary")).toBeVisible();
  expect(oiPosts.length).toBe(postsBefore);
  expect(oiPosts.some((u) => u.includes("execution-intelligence"))).toBe(false);
});
