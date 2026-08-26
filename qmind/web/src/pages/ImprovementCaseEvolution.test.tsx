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
let executionIntelligence: Record<string, unknown> | null = null;
let executionRuns = 0;
let executionHistory: Record<string, unknown>[] = [];
let executionReadsFail = false;

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

function fullExecutionRun(index: number, isStale = false) {
  return {
    id: `ei-${index}`,
    organization_id: ORG,
    improvement_case_id: "case-1",
    schema_version: "1.0",
    mechanism_version: "execution-intelligence-rules-v1",
    request_id: `request-${index}`,
    correlation_id: `correlation-${index}`,
    generated_at: `2026-08-${25 + index}T12:00:00Z`,
    input_fingerprint: `fingerprint-${index}`,
    created_by: "user-1",
    created_at: `2026-08-${25 + index}T12:00:00Z`,
    is_stale: isStale,
    input_snapshot: {
      schema_version: "1.0",
      core_organization_id: ORG,
      improvement_case_id: "case-1",
      request_id: `request-${index}`,
      correlation_id: `correlation-${index}`,
      captured_at: `2026-08-${25 + index}T12:00:00Z`,
      source: { system: "qmind-core", component: "execution-intelligence" },
      case: { status: "acting" },
      execution: {
        plan: { plan_ref: "execution-plan", status: "active" },
        actions: [
          {
            action_ref: "action:1",
            label: "Revisar fila de atendimento",
            status: "in_progress",
            owner_assigned: true,
            created_at: "2026-08-20T12:00:00Z",
            active_impediment_count: 1,
            open_dependency_count: 0,
            overdue_dependency_count: 0,
            evidence_count: 0,
            approved_evidence_count: 0,
            is_overdue: true,
            is_terminal: false,
            claims_execution: false,
          },
        ],
      },
      measurement: {
        plans: [],
        indicators: [
          {
            indicator_ref: "indicator:1",
            plan_ref: "measurement-plan:1",
            name: "Tempo de atendimento",
            unit: "horas",
            direction: "lower_is_better",
            measurement_posture: "overdue",
            target_posture: "not_met",
            baseline_status: "recorded",
            is_measurement_overdue: true,
            substantiation: "partial",
            comparable_reading_count: 1,
          },
        ],
      },
      fact_refs: [],
    },
    result: {
      schema_version: "1.0",
      core_organization_id: ORG,
      improvement_case_id: "case-1",
      analysis_id: `analysis-${index}`,
      request_id: `request-${index}`,
      correlation_id: `correlation-${index}`,
      generated_at: `2026-08-${25 + index}T12:00:00Z`,
      mechanism_version: "execution-intelligence-rules-v1",
      interpretability_status: "interpretable",
      execution_posture: "attention_required",
      interpretation_summary: "Há fatos que pedem atenção humana.",
      signals: [
        {
          code: "action_overdue",
          category: "schedule",
          level: "attention",
          title: "Prazo de ação pede atenção",
          interpretation: "A ação ultrapassou o prazo informado.",
          supporting_fact_refs: [
            "execution.action:action:1:due_at",
            "execution.action:action:1:is_overdue",
          ],
          iso_basis: ["6.2.2", "8.1"],
          recommended_next_step: "Revisar o prazo com a pessoa responsável.",
          requires_human_validation: true,
        },
        {
          code: "measurement_overdue",
          category: "measurement",
          level: "attention",
          title: "Medição em atraso",
          interpretation: "A medição planejada está atrasada.",
          supporting_fact_refs: [
            "measurement.indicator:indicator:1:measurement_posture",
          ],
          iso_basis: ["9.1.1"],
          recommended_next_step: "Realizar ou replanejar a medição.",
          requires_human_validation: true,
        },
      ],
      missing_information: ["Observação humana de resultado não informada."],
      limitations: ["A análise não verifica o conteúdo das evidências."],
    },
  };
}

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
    execution_intelligence: executionIntelligence,
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
    executionIntelligence = null;
    executionRuns = 0;
    executionHistory = [];
    executionReadsFail = false;
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
        if (
          url.includes("/execution-intelligence/latest") &&
          method === "GET"
        ) {
          if (executionReadsFail) {
            return jsonResponse(
              { code: "unavailable", message: "Unavailable", correlation_id: "test" },
              503,
            );
          }
          return executionHistory.length
            ? jsonResponse(executionHistory[0])
            : jsonResponse(
                { code: "not_found", message: "Not found", correlation_id: "test" },
                404,
              );
        }
        if (
          url.includes("/execution-intelligence/runs") &&
          method === "GET"
        ) {
          if (executionReadsFail) {
            return jsonResponse(
              { code: "unavailable", message: "Unavailable", correlation_id: "test" },
              503,
            );
          }
          return jsonResponse(executionHistory);
        }
        if (
          url.includes("/execution-intelligence/runs") &&
          method === "POST"
        ) {
          executionRuns += 1;
          executionHistory = [
            fullExecutionRun(executionRuns),
            ...executionHistory,
          ];
          executionIntelligence = {
            run_id: `ei-${executionRuns}`,
            generated_at: "2026-08-26T12:00:00Z",
            interpretability_status: "interpretable",
            execution_posture: "progressing",
            interpretation_summary: "A execução apresenta avanço registrado.",
            signal_count: 2,
            is_stale: false,
          };
          return jsonResponse(
            {
              id: `ei-${executionRuns}`,
              improvement_case_id: "case-1",
            },
            201,
          );
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
    expect(screen.getByTestId("ic-ei-never")).toBeInTheDocument();
  });

  it("runs and displays Execution Intelligence without raw identifiers", async () => {
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    await user.click(await screen.findByTestId("ic-ei-run"));
    await waitFor(() => expect(executionRuns).toBe(1));
    const result = await screen.findByTestId("ic-ei-result");
    expect(result).toHaveTextContent("Execução requer atenção");
    expect(result).toHaveTextContent("Há fatos que pedem atenção humana.");
    expect(result).not.toHaveTextContent("ei-1");
    expect(screen.getByText("Interpretação QMind OI")).toBeInTheDocument();
  });

  it("shows full grouped intelligence, facts, ISO, limits, missing data and history", async () => {
    executionHistory = [fullExecutionRun(2), fullExecutionRun(1, true)];
    executionIntelligence = {
      run_id: "ei-2",
      generated_at: "2026-08-27T12:00:00Z",
      interpretability_status: "interpretable",
      execution_posture: "attention_required",
      interpretation_summary: "Há fatos que pedem atenção humana.",
      signal_count: 2,
      is_stale: false,
    };
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);

    expect(await screen.findByText("Prazos")).toBeInTheDocument();
    expect(screen.getByText("Medição")).toBeInTheDocument();
    expect(screen.getAllByTestId("ic-ei-signal")).toHaveLength(2);
    expect(
      screen.getByText("Revisar fila de atendimento — prazo"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Tempo de atendimento — situação da medição/)).toBeInTheDocument();
    expect(screen.getByText(/Base ISO 9001: 6.2.2, 8.1/)).toBeInTheDocument();
    expect(screen.getByText(/Revisar o prazo com a pessoa responsável/)).toBeInTheDocument();
    expect(screen.getByTestId("ic-ei-missing")).toHaveTextContent(
      "Observação humana de resultado não informada.",
    );
    expect(screen.getByTestId("ic-ei-limitations")).toHaveTextContent(
      "não verifica o conteúdo das evidências",
    );
    expect(screen.getByTestId("ic-ei-mechanism")).toHaveTextContent("versão 1");
    expect(screen.getByTestId("ic-ei-history").querySelectorAll("li")).toHaveLength(2);
    expect(screen.getByTestId("ic-ei-human-warning")).toHaveTextContent(
      /validação humana.*não significa eficácia comprovada/i,
    );
    const panel = screen.getByTestId("ic-evo-execution-intelligence");
    expect(panel).not.toHaveTextContent("execution.action:");
    expect(panel).not.toHaveTextContent(ORG);
  });

  it("preserves the previous full analysis when refresh fails", async () => {
    executionHistory = [fullExecutionRun(1)];
    executionIntelligence = {
      run_id: "ei-1",
      generated_at: "2026-08-26T12:00:00Z",
      interpretability_status: "interpretable",
      execution_posture: "attention_required",
      interpretation_summary: "Há fatos que pedem atenção humana.",
      signal_count: 2,
      is_stale: false,
    };
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    expect((await screen.findAllByTestId("ic-ei-signal"))[0]).toHaveTextContent(
      "Prazo de ação pede atenção",
    );
    executionReadsFail = true;
    await user.click(screen.getByTestId("ic-ei-run"));
    expect(await screen.findByTestId("ic-ei-load-error")).toBeInTheDocument();
    expect(screen.getAllByTestId("ic-ei-signal")[0]).toHaveTextContent(
      "Prazo de ação pede atenção",
    );
  });

  it("shows stale interpretation and hides action from reader", async () => {
    roles = ["reader"];
    executionIntelligence = {
      run_id: "ei-old",
      generated_at: "2026-08-26T12:00:00Z",
      interpretability_status: "insufficient_facts",
      execution_posture: "insufficient_information",
      interpretation_summary: "Ainda faltam registros.",
      signal_count: 0,
      is_stale: true,
    };
    const user = userEvent.setup();
    renderPage();
    await enterApp(user);
    expect(await screen.findByTestId("ic-ei-stale")).toBeInTheDocument();
    expect(screen.queryByTestId("ic-ei-run")).not.toBeInTheDocument();
    expect(screen.getByText(/faltam fatos/i)).toBeInTheDocument();
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
