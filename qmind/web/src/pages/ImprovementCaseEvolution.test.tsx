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
const ORG_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

let roles: string[] = ["org_admin"];
let caseStatus = "acting";
let closure: "insufficient_information" | "ready_for_review" =
  "insufficient_information";
let observations: unknown[] = [];
let comparison: unknown | null = null;
let totalRuns = 0;
let latestStale = false;
let actionTotal = 0;
let actionCompleted = 0;
let actionOverdue = 0;
let createObsCalls = 0;
let patchBodies: unknown[] = [];
let evolutionOrgId = ORG;

const caseRow = () => ({
  id: "case-1",
  organization_id: ORG,
  problem_statement: "Atrasos",
  impact_statement: "SLA",
  related_process: "Pedidos",
  status: caseStatus,
  created_by: "user-1",
  created_at: "2026-08-19T12:00:00Z",
  updated_at: "2026-08-19T12:00:00Z",
});

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

function evolutionPayload() {
  return {
    case: { ...caseRow(), organization_id: evolutionOrgId },
    analysis_summary: {
      total_runs: totalRuns,
      latest_run:
        totalRuns > 0
          ? {
              ...run,
              is_stale: latestStale,
              organization_id: evolutionOrgId,
            }
          : null,
      previous_run: totalRuns > 1 ? { ...run, id: "run-0" } : null,
      comparison,
    },
    action_summary: {
      total: actionTotal,
      by_status:
        actionTotal > 0
          ? [{ status: actionCompleted ? "done" : "open", count: actionTotal }]
          : [],
      overdue: actionOverdue,
      completed: actionCompleted,
      items: [],
      plan: null,
    },
    latest_outcome_observation: observations[0] ?? null,
    outcome_observations: observations,
    closure_readiness: closure,
  };
}

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

describe("Improvement Case Evolution UI", () => {
  beforeEach(() => {
    resetConfigCache();
    resetQmindClient();
    roles = ["org_admin"];
    caseStatus = "acting";
    closure = "insufficient_information";
    observations = [];
    comparison = null;
    totalRuns = 0;
    latestStale = false;
    actionTotal = 0;
    actionCompleted = 0;
    actionOverdue = 0;
    createObsCalls = 0;
    patchBodies = [];
    evolutionOrgId = ORG;
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
        if (url.includes("/evolution") && method === "GET") {
          return jsonResponse(evolutionPayload());
        }
        if (url.includes("/outcome-observations") && method === "POST") {
          createObsCalls += 1;
          const obs = {
            id: `obs-${createObsCalls}`,
            organization_id: ORG,
            improvement_case_id: "case-1",
            result_direction: body.result_direction,
            observation_statement: body.observation_statement,
            measurement_basis: body.measurement_basis,
            observed_at: body.observed_at,
            created_by: "user-1",
            created_at: "2026-08-19T18:00:00Z",
          };
          observations = [obs, ...observations];
          return jsonResponse(obs, 201);
        }
        if (
          url.includes("/improvement-cases/case-1") &&
          method === "PATCH"
        ) {
          patchBodies.push(body);
          if (typeof body.status === "string") caseStatus = body.status;
          return jsonResponse(caseRow());
        }
        if (
          url.includes("/improvement-cases/case-1") &&
          method === "GET" &&
          !url.includes("analysis") &&
          !url.includes("actions") &&
          !url.includes("evolution") &&
          !url.includes("outcome")
        ) {
          return jsonResponse(caseRow());
        }
        if (url.includes("analysis-runs") && method === "GET") {
          return jsonResponse(totalRuns > 0 ? [run] : []);
        }
        if (url.includes("/actions") && method === "GET") {
          return jsonResponse({ plan: null, items: [] });
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

  it("shows empty evolution without data", async () => {
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("ic-section-evolution")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ic-evo-outcome-empty")).toBeInTheDocument();
    expect(screen.getByTestId("ic-evo-comparison-empty")).toBeInTheDocument();
    expect(screen.getByTestId("ic-evo-closure")).toHaveTextContent(
      /faltam elementos/i,
    );
  });

  it("hides register for reader", async () => {
    roles = ["reader"];
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("ic-section-evolution")).toBeInTheDocument(),
    );
    expect(
      screen.queryByTestId("ic-evo-register-outcome"),
    ).not.toBeInTheDocument();
  });

  it("registers outcome with four questions and humanized directions", async () => {
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("ic-evo-register-outcome")).toBeInTheDocument(),
    );
    await user.click(screen.getByTestId("ic-evo-register-outcome"));
    expect(screen.getByText(/Como a situação se apresenta agora/i)).toBeInTheDocument();
    expect(screen.getByText(/O que foi observado depois das ações/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Em que informação essa observação se baseia/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Quando essa observação foi realizada/i),
    ).toBeInTheDocument();

    const select = screen.getByTestId("ic-evo-direction");
    expect(select).toHaveTextContent("Melhorou");
    expect(select).toHaveTextContent("Permaneceu igual");
    expect(select).toHaveTextContent("Piorou");
    expect(select).toHaveTextContent("Ainda não foi medido");

    fireEvent.change(select, { target: { value: "improved" } });
    fireEvent.change(screen.getByTestId("ic-evo-statement"), {
      target: { value: "Atrasos diminuíram." },
    });
    fireEvent.change(screen.getByTestId("ic-evo-basis"), {
      target: { value: "Relatório de SLA" },
    });
    fireEvent.change(screen.getByTestId("ic-evo-observed-at"), {
      target: { value: "2026-08-18T10:00" },
    });
    await user.click(screen.getByRole("button", { name: /Salvar observação/i }));

    await waitFor(() => expect(createObsCalls).toBe(1));
    await waitFor(() =>
      expect(screen.getByTestId("ic-evo-outcome-history")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ic-evo-outcome-history")).toHaveTextContent(
      /Melhorou/,
    );
  });

  it("shows action counts and comparison without resolved language", async () => {
    totalRuns = 2;
    actionTotal = 3;
    actionCompleted = 1;
    actionOverdue = 1;
    comparison = {
      context_status_before: "ready_for_initial_analysis",
      context_status_after: "insufficient_context",
      findings_added: ["F-3"],
      findings_removed: ["F-2"],
      findings_persisting: ["F-1"],
      missing_information_added: ["dado-y"],
      missing_information_removed: ["dado-x"],
      limitations_added: ["L3"],
      limitations_removed: ["L2"],
    };
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("ic-evo-situation")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ic-evo-situation")).toHaveTextContent(
      /Ações: 3 · concluídas 1 · pendentes 2 · vencidas 1/,
    );
    expect(screen.getByText("F-3")).toBeInTheDocument();
    expect(screen.getByTestId("ic-evo-removed-copy")).toHaveTextContent(
      /não aparece na análise mais recente/i,
    );
    expect(screen.queryByText(/resolvido/i)).not.toBeInTheDocument();
  });

  it("highlights stale analysis banner", async () => {
    totalRuns = 1;
    latestStale = true;
    closure = "insufficient_information";
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("ic-evo-stale")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ic-evo-stale")).toHaveTextContent(
      /não considera as informações mais recentes/i,
    );
  });

  it("offers Colocar em revisão when ready and acting", async () => {
    totalRuns = 1;
    closure = "ready_for_review";
    caseStatus = "acting";
    actionTotal = 1;
    actionCompleted = 1;
    observations = [
      {
        id: "obs-1",
        organization_id: ORG,
        improvement_case_id: "case-1",
        result_direction: "improved",
        observation_statement: "Melhora",
        measurement_basis: "SLA",
        observed_at: "2026-08-18T12:00:00Z",
        created_by: "user-1",
        created_at: "2026-08-18T12:00:00Z",
      },
    ];
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("ic-evo-to-review")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ic-evo-closure")).toHaveTextContent(
      /elementos para revisão/i,
    );
    await user.click(screen.getByTestId("ic-evo-to-review"));
    await waitFor(() => expect(patchBodies.length).toBe(1));
    expect(patchBodies[0]).toEqual({ status: "reviewing" });
  });

  it("shows close confirmation disclaimer", async () => {
    caseStatus = "reviewing";
    closure = "ready_for_review";
    totalRuns = 1;
    actionTotal = 1;
    actionCompleted = 1;
    observations = [
      {
        id: "obs-1",
        organization_id: ORG,
        improvement_case_id: "case-1",
        result_direction: "unchanged",
        observation_statement: "Igual",
        measurement_basis: "Reunião",
        observed_at: "2026-08-18T12:00:00Z",
        created_by: "user-1",
        created_at: "2026-08-18T12:00:00Z",
      },
    ];
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("ic-evo-close")).toBeInTheDocument(),
    );
    await user.click(screen.getByTestId("ic-evo-close"));
    expect(screen.getByTestId("ic-evo-close-confirm")).toHaveTextContent(
      /Não representa conformidade, certificação/i,
    );
    await user.click(screen.getByTestId("ic-evo-close-confirm-yes"));
    await waitFor(() =>
      expect(patchBodies.some((b) => (b as { status?: string }).status === "closed")).toBe(
        true,
      ),
    );
  });

  it("discards evolution when organization_id mismatches", async () => {
    evolutionOrgId = ORG_B;
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("ic-section-evolution")).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/Evolução indisponível para este problema/i),
    ).toBeInTheDocument();
  });
});
