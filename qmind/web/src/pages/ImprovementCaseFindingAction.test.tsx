import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { ImprovementCaseDetailPage } from "@/pages/ImprovementCaseDetailPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const MEMBER = "mmmmmmmm-mmmm-4mmm-8mmm-mmmmmmmmmmmm";

let roles: string[] = ["org_admin"];
let actions: unknown[] = [];
let createCalls = 0;

const caseRow = {
  id: "case-1",
  organization_id: ORG,
  problem_statement: "Atrasos",
  impact_statement: "SLA",
  related_process: "Pedidos",
  status: "open",
  created_by: "user-1",
  created_at: "2026-08-19T12:00:00Z",
  updated_at: "2026-08-19T12:00:00Z",
};

const run = {
  id: "run-1",
  organization_id: ORG,
  improvement_case_id: "case-1",
  schema_version: "1.0",
  request_id: "r",
  correlation_id: "c",
  generated_at: "2026-08-19T15:00:00Z",
  input_fingerprint: "fp",
  created_at: "2026-08-19T15:00:00Z",
  is_stale: false,
  analysis: {
    schema_version: "1.0",
    core_organization_id: ORG,
    improvement_case_id: "case-1",
    analysis_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01",
    request_id: "r",
    correlation_id: "c",
    generated_at: "2026-08-19T15:00:00Z",
    context_status: "ready_for_initial_analysis",
    interpretation_summary: "Síntese",
    hypotheses: [],
    findings: [
      {
        code: "F-1",
        title: "Atenção ao processo",
        description: "Desc",
        relationship_to_problem: "Relação",
        business_impact: "Impacto",
        supporting_facts: [],
        missing_information: [],
        iso_basis: ["4.4"],
        recommended_next_step: "Mapear o fluxo",
        requires_human_validation: true,
      },
    ],
    limitations: ["Limite"],
  },
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

async function resolveRequest(input: RequestInfo | URL, init?: RequestInit) {
  const url =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.href
        : input.url;
  const req = input instanceof Request ? input : null;
  const method = (init?.method ?? req?.method ?? "GET").toUpperCase();
  let raw: BodyInit | null | undefined = init?.body;
  if (raw == null && req) raw = await req.clone().text();
  let body: Record<string, unknown> = {};
  if (typeof raw === "string" && raw.length > 0) {
    body = JSON.parse(raw) as Record<string, unknown>;
  }
  return { url, method, body };
}

describe("Finding to Action UI", () => {
  beforeEach(() => {
    resetConfigCache();
    resetQmindClient();
    roles = ["org_admin"];
    actions = [];
    createCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const { url, method, body } = await resolveRequest(input, init);
        if (url.includes("/organizations/me/memberships")) {
          return jsonResponse([
            {
              id: MEMBER,
              organization_id: ORG,
              organization_name: "Org",
              roles,
              status: "active",
            },
          ]);
        }
        if (url.includes("/profile")) {
          return jsonResponse({
            organization_id: ORG,
            trade_name: "Acme",
            legal_name: "",
            summary: "s",
            industry: "i",
            business_model: "b2b",
            employee_range: "11-50",
            unit_count: 1,
            certification_status: "none",
            quality_structure: "formal",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          });
        }
        if (url.includes("/members")) {
          return jsonResponse([
            {
              membership_id: MEMBER,
              email: "a@example.com",
              display_name: "Admin",
              roles: ["org_admin"],
              status: "active",
            },
          ]);
        }
        if (
          url.includes("/improvement-cases/case-1") &&
          method === "GET" &&
          !url.includes("analysis") &&
          !url.includes("actions") &&
          !url.includes("evolution") &&
          !url.includes("outcome")
        ) {
          return jsonResponse(caseRow);
        }
        if (url.includes("/evolution") && method === "GET") {
          return jsonResponse({
            case: caseRow,
            analysis_summary: {
              total_runs: 1,
              latest_run: run,
              previous_run: null,
              comparison: null,
            },
            action_summary: {
              total: actions.length,
              by_status: [],
              overdue: 0,
              completed: 0,
              items: actions,
              plan: null,
            },
            latest_outcome_observation: null,
            outcome_observations: [],
            closure_readiness: "insufficient_information",
          });
        }
        if (url.includes("analysis-runs") && method === "GET") {
          return jsonResponse([run]);
        }
        if (url.includes("/actions") && method === "GET") {
          return jsonResponse({
            plan: actions.length
              ? {
                  id: "plan-1",
                  organization_id: ORG,
                  assessment_id: null,
                  improvement_case_id: "case-1",
                  status: "draft",
                  empty_plan_rationale: null,
                  created_at: "2026-08-19T15:00:00Z",
                  updated_at: "2026-08-19T15:00:00Z",
                }
              : null,
            items: actions,
          });
        }
        if (url.includes("/findings/F-1/actions") && method === "POST") {
          createCalls += 1;
          if (createCalls > 1) {
            return jsonResponse({ detail: "exists" }, 409);
          }
          const item = {
            id: "item-1",
            organization_id: ORG,
            action_plan_id: "plan-1",
            finding_id: null,
            source_evolution_suggestion_id: null,
            source_analysis_run_id: "run-1",
            source_finding_code: "F-1",
            action_kind: "improvement",
            description:
              "Atenção ao processo\n\nMapear o fluxo\n\nContexto: Relação",
            owner_membership_id: body.owner_membership_id,
            due_at: body.due_at,
            status: "open",
            is_overdue: false,
            efficacy_required: false,
            source_finding_withdrawn: false,
            created_at: "2026-08-19T16:00:00Z",
            updated_at: "2026-08-19T16:00:00Z",
          };
          actions = [item];
          return jsonResponse(item, 201);
        }
        return jsonResponse({ detail: url }, 404);
      }),
    );
  });

  afterEach(() => vi.unstubAllGlobals());

  function renderPage() {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    return render(
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <OrganizationProvider>
            <MemoryRouter initialEntries={["/improvement-cases/case-1"]}>
              <Routes>
                <Route element={<AppShell />}>
                  <Route
                    path="improvement-cases/:caseId"
                    element={<ImprovementCaseDetailPage />}
                  />
                </Route>
              </Routes>
            </MemoryRouter>
          </OrganizationProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );
  }

  it("creates action from finding and lists it", async () => {
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("ic-create-action-F-1")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ic-actions-empty")).toBeInTheDocument();

    await user.click(screen.getByTestId("ic-create-action-F-1"));
    expect(screen.getByText(/somente leitura/i)).toBeInTheDocument();
    fireEvent.change(screen.getByTestId("ic-action-owner"), {
      target: { value: MEMBER },
    });
    fireEvent.change(screen.getByTestId("ic-action-due"), {
      target: { value: "2026-09-01T10:00" },
    });
    await user.click(screen.getByTestId("ic-action-confirm"));

    await waitFor(() => {
      expect(
        screen.getByTestId("ic-finding-action-created-F-1"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("ic-actions-list")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("ic-analysis-stale")).not.toBeInTheDocument();
  });

  it("hides create for reader", async () => {
    roles = ["reader"];
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("ic-finding-F-1")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("ic-create-action-F-1")).not.toBeInTheDocument();
  });
});
