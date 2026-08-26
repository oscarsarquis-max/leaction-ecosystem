/**
 * Capture sanitized ISOI-010 cockpit screenshots (demo data only).
 * Run with Core+preview up: QMIND_E2E_BASE_URL=http://127.0.0.1:4179
 */
import { test, expect } from "@playwright/test";
import { createApi } from "./helpers/api";
import { signIn, visit } from "./helpers/executionSession";
import path from "node:path";
import { fileURLToPath } from "node:url";

const OUT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../architecture/04_Docs/assets/isoi-010",
);

test("isoi-010 capture cockpit screenshots", async ({ page, baseURL }) => {
  test.setTimeout(300_000);
  const origin = baseURL!;
  const who = await signIn(page, "/execution");
  const api = await createApi(origin, who.orgId, { sub: who.sub, email: who.email });

  await api.request("PATCH", "/api/v1/organizations/current/profile", {
    body: {
      trade_name: "Demo Cockpit Shot",
      summary: "Organização fictícia para captura ISOI-010",
      industry: "Serviços",
      business_model: "b2b",
      employee_range: "11-50",
      unit_count: 1,
      certification_status: "none",
      quality_structure: "formal",
    },
  });

  const created = await api.request(
    "POST",
    "/api/v1/organizations/current/improvement-cases",
    {
      body: {
        problem_statement: `[DEMO-ISOI-010] Atraso de fila ${Date.now()}`,
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
  const memberships = await api.request("GET", "/api/v1/organizations/me/memberships");
  const owner = memberships.json.find(
    (m: { organization_id: string }) => m.organization_id === who.orgId,
  );
  if (finding?.code && owner?.id) {
    await api.request(
      "POST",
      `/api/v1/organizations/current/improvement-cases/${caseId}/analysis-runs/${analysis.json.id}/findings/${finding.code}/actions`,
      {
        body: {
          owner_membership_id: owner.id,
          due_at: new Date(Date.now() - 864e5).toISOString(),
        },
      },
    );
  }

  await visit(page, "/cockpit");
  await expect(page.getByTestId("cockpit-page")).toBeVisible({ timeout: 60_000 });
  await expect(page.getByTestId("cockpit-summary")).toBeVisible();
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.screenshot({
    path: path.join(OUT, "cockpit-desktop-full.png"),
    fullPage: true,
  });

  const immediate = page.getByTestId("cockpit-filter-immediate");
  if (await immediate.isVisible().catch(() => false)) {
    await immediate.click();
  }
  await page.screenshot({
    path: path.join(OUT, "cockpit-filtered-queue.png"),
    fullPage: true,
  });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: path.join(OUT, "cockpit-mobile-width.png"),
    fullPage: true,
  });

  await page.setViewportSize({ width: 1280, height: 900 });
  await visit(page, `/improvement-cases/${caseId}`);
  const evo = page.getByTestId("ic-evo-execution-intelligence");
  await expect(evo).toBeVisible({ timeout: 60_000 });
  await evo.screenshot({
    path: path.join(OUT, "cockpit-drilldown-ei.png"),
  });
});
