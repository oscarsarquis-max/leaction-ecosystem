import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { CockpitPage } from "@/pages/CockpitPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const MEMBER = "mmmmmmmm-mmmm-4mmm-8mmm-mmmmmmmmmmmm";
const CASE_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";

let roles: string[] = ["org_admin"];
let summaryPayload: Record<string, unknown> | null = null;
let casesPayload: Record<string, unknown> | null = null;
let activityPayload: Record<string, unknown> | null = null;
let summaryFail = false;
let casesFail = false;
let getCalls: string[] = [];
let postCalls: string[] = [];

function emptySummary() {
  return {
    as_of: "2026-08-26T12:00:00Z",
    scope: {
      organization_id: ORG,
      case_status_filter: null,
      activity_window_days: 30,
    },
    case_totals: {
      total: 0,
      active: 0,
      reviewing: 0,
      closed: 0,
      ready_for_review: 0,
      unit: "cases",
    },
    priority_distribution: [],
    execution: {
      active_actions: 0,
      completed_actions: 0,
      overdue_actions: 0,
      blocked_cases: 0,
      active_impediments: 0,
      open_dependencies: 0,
      overdue_dependencies: 0,
      actions_without_recent_check_in: 0,
    },
    evidence: {
      claims_execution_actions: 0,
      with_approved_evidence: 0,
      without_approved_evidence: 0,
    },
    measurement: {
      by_measurement_posture: [],
      by_target_posture: [],
      by_substantiation: [],
      overdue_indicators: 0,
    },
    intelligence_coverage: {
      current: 0,
      stale: 0,
      never_analyzed: 0,
      unit: "cases",
    },
    execution_posture_distribution_current: [],
    execution_posture_distribution_stale: [],
    signals_current: [],
    signals_stale: [],
    recent_activity: [],
    coverage: {
      analyzed_count: 0,
      included_count: 0,
      excluded_count: 0,
      complete: true,
    },
  };
}

function populatedSummary() {
  return {
    ...emptySummary(),
    case_totals: {
      total: 2,
      active: 2,
      reviewing: 0,
      closed: 0,
      ready_for_review: 1,
      unit: "cases",
    },
    priority_distribution: [
      {
        code: "immediate_attention",
        label: "Atenção imediata",
        count: 1,
        unit: "cases",
      },
      { code: "attention", label: "Atenção", count: 1, unit: "cases" },
    ],
    execution: {
      active_actions: 3,
      completed_actions: 1,
      overdue_actions: 2,
      blocked_cases: 1,
      active_impediments: 1,
      open_dependencies: 0,
      overdue_dependencies: 0,
      actions_without_recent_check_in: 0,
    },
    measurement: {
      by_measurement_posture: [
        { code: "overdue", label: "Atrasada", count: 1, unit: "cases" },
        { code: "on_time", label: "Em dia", count: 1, unit: "cases" },
      ],
      by_target_posture: [],
      by_substantiation: [],
      overdue_indicators: 1,
    },
    intelligence_coverage: {
      current: 1,
      stale: 1,
      never_analyzed: 0,
      unit: "cases",
    },
    execution_posture_distribution_current: [
      {
        code: "attention_required",
        label: "attention_required",
        count: 1,
        unit: "cases",
      },
    ],
    execution_posture_distribution_stale: [
      {
        code: "progressing",
        label: "progressing",
        count: 1,
        unit: "cases",
      },
    ],
    signals_current: [
      { category: "schedule", level: "attention", count: 2, unit: "signals" },
    ],
    signals_stale: [
      { category: "blocker", level: "watch", count: 9, unit: "signals" },
    ],
    recent_activity: [
      {
        event_type: "check_in_recorded",
        event_type_label: "Check-in registrado",
        occurred_at: "2026-08-26T11:00:00Z",
        summary: "Atualização da ação de pedidos",
        case_id: CASE_ID,
        action_item_id: null,
      },
    ],
    coverage: {
      analyzed_count: 2,
      included_count: 2,
      excluded_count: 0,
      complete: true,
    },
  };
}

function populatedCases() {
  return {
    as_of: "2026-08-26T12:00:00Z",
    coverage: {
      analyzed_count: 2,
      included_count: 2,
      excluded_count: 0,
      complete: true,
    },
    items: [
      {
        case_id: CASE_ID,
        problem_label: "Atrasos no atendimento",
        related_process: "Pedidos",
        case_status: "acting",
        priority_band: "immediate_attention",
        priority_band_label: "Atenção imediata",
        priority_reasons: [
          { code: "overdue_action", label: "Há ação vencida" },
          {
            code: "ei_current_attention_required",
            label: "Execution Intelligence atual exige atenção",
          },
        ],
        action_count: 2,
        completed_action_count: 0,
        overdue_action_count: 1,
        active_impediment_count: 1,
        open_dependency_count: 0,
        overdue_dependency_count: 0,
        last_activity_at: "2026-08-26T11:00:00Z",
        oldest_due_at: "2026-08-20T12:00:00Z",
        measurement_posture: "overdue",
        target_posture: "not_met",
        substantiation: "partial",
        outcome_result_direction: null,
        outcome_observed_at: null,
        execution_posture: "attention_required",
        intelligence_generated_at: "2026-08-26T10:00:00Z",
        intelligence_mechanism_version: "execution-intelligence-rules-v1",
        intelligence_signal_count: 2,
        intelligence_freshness: "current",
        intelligence_freshness_label: "Atual",
        closure_readiness: "insufficient_information",
        closure_readiness_reason: "Há ações em aberto.",
        current_attention_signal_count: 1,
      },
      {
        case_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        problem_label: "Retrabalho em inspeção",
        related_process: "Qualidade",
        case_status: "acting",
        priority_band: "attention",
        priority_band_label: "Atenção",
        priority_reasons: [
          { code: "ei_stale", label: "Execution Intelligence desatualizada" },
        ],
        action_count: 1,
        completed_action_count: 1,
        overdue_action_count: 0,
        active_impediment_count: 0,
        open_dependency_count: 0,
        overdue_dependency_count: 0,
        last_activity_at: "2026-08-25T09:00:00Z",
        oldest_due_at: null,
        measurement_posture: "on_time",
        target_posture: "met",
        substantiation: "verified",
        outcome_result_direction: null,
        outcome_observed_at: null,
        execution_posture: "progressing",
        intelligence_generated_at: "2026-08-20T10:00:00Z",
        intelligence_mechanism_version: "execution-intelligence-rules-v1",
        intelligence_signal_count: 0,
        intelligence_freshness: "stale",
        intelligence_freshness_label: "Desatualizada",
        closure_readiness: "ready_for_review",
        closure_readiness_reason: "Pronto para revisão humana.",
        current_attention_signal_count: 0,
      },
    ],
    limit: 50,
    next_cursor: null,
  };
}

function emptyCases() {
  return {
    as_of: "2026-08-26T12:00:00Z",
    coverage: {
      analyzed_count: 0,
      included_count: 0,
      excluded_count: 0,
      complete: true,
    },
    items: [],
    limit: 50,
    next_cursor: null,
  };
}

function emptyActivity() {
  return {
    as_of: "2026-08-26T12:00:00Z",
    activity_window_days: 30,
    coverage: {
      analyzed_count: 0,
      included_count: 0,
      excluded_count: 0,
      complete: true,
    },
    items: [],
    limit: 15,
    next_cursor: null,
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
  return { url, method };
}

function renderCockpit(initialEntry = "/cockpit") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <OrganizationProvider>
          <MemoryRouter initialEntries={[initialEntry]}>
            <Routes>
              <Route element={<AppShell />}>
                <Route path="cockpit" element={<CockpitPage />} />
                <Route
                  path="improvement-cases/:caseId"
                  element={<div data-testid="case-detail">caso</div>}
                />
              </Route>
            </Routes>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("CockpitPage", () => {
  beforeEach(() => {
    resetConfigCache();
    resetQmindClient();
    roles = ["org_admin"];
    summaryPayload = populatedSummary();
    casesPayload = populatedCases();
    activityPayload = {
      ...emptyActivity(),
      items: populatedSummary().recent_activity,
    };
    summaryFail = false;
    casesFail = false;
    getCalls = [];
    postCalls = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const { url, method } = await resolveRequest(input, init);
        if (method === "POST") postCalls.push(url);
        if (method === "GET") getCalls.push(url);

        if (url.includes("/organizations/me/memberships")) {
          return jsonResponse([
            {
              id: MEMBER,
              organization_id: ORG,
              organization_name: "Org Demo",
              roles,
              status: "active",
            },
          ]);
        }
        if (url.includes("/iso-intelligence/cockpit/summary")) {
          if (summaryFail) {
            return jsonResponse(
              {
                code: "unavailable",
                message: "Resumo indisponível",
                correlation_id: "c1",
              },
              503,
            );
          }
          return jsonResponse(summaryPayload);
        }
        if (url.includes("/iso-intelligence/cockpit/cases")) {
          if (casesFail) {
            return jsonResponse(
              {
                code: "unavailable",
                message: "Fila indisponível",
                correlation_id: "c2",
              },
              503,
            );
          }
          return jsonResponse(casesPayload);
        }
        if (url.includes("/iso-intelligence/cockpit/activity")) {
          return jsonResponse(activityPayload);
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
        return jsonResponse(
          { code: "not_found", message: "Not found", correlation_id: "x" },
          404,
        );
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows loading then populated synthesis, reasons, freshness and no UUID", async () => {
    const user = userEvent.setup();
    renderCockpit();
    await enterApp(user);

    expect(await screen.findByTestId("cockpit-page")).toBeInTheDocument();
    expect(screen.getByText("Cockpit de Inteligência ISO")).toBeInTheDocument();
    expect(screen.getByTestId("cockpit-as-of")).toHaveTextContent(
      /Dados atualizados em/,
    );

    expect(screen.getByTestId("cockpit-synth-active")).toHaveTextContent("2");
    expect(screen.getByTestId("cockpit-filter-immediate")).toHaveTextContent("1");
    expect(screen.getByTestId("cockpit-synth-overdue-actions")).toHaveTextContent(
      "2",
    );

    expect(screen.getAllByText("Há ação vencida").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText("Execution Intelligence atual exige atenção").length,
    ).toBeGreaterThan(0);

    const freshness = screen.getAllByTestId("cockpit-freshness-label");
    expect(freshness.some((el) => el.textContent === "Atual")).toBe(true);
    expect(freshness.some((el) => el.textContent === "Desatualizada")).toBe(
      true,
    );

    expect(screen.queryByText(CASE_ID)).not.toBeInTheDocument();
    expect(screen.queryByText(/cccccccc/i)).not.toBeInTheDocument();
    expect(screen.queryByText("attention_required")).not.toBeInTheDocument();
    expect(
      screen.getAllByText("Execução requer atenção").length,
    ).toBeGreaterThan(0);

    const signals = screen.getByTestId("cockpit-dist-signals-current");
    expect(
      within(signals).getAllByText(/Prazos · Requer atenção/).length,
    ).toBeGreaterThan(0);
    expect(within(signals).queryByText(/Impedimentos/)).not.toBeInTheDocument();

    const openLinks = screen.getAllByTestId("cockpit-open-case");
    expect(openLinks[0]).toHaveAttribute(
      "href",
      `/improvement-cases/${CASE_ID}`,
    );
  });

  it("shows empty organization message when there are no cases", async () => {
    summaryPayload = emptySummary();
    casesPayload = emptyCases();
    activityPayload = emptyActivity();
    const user = userEvent.setup();
    renderCockpit();
    await enterApp(user);

    expect(
      await screen.findByText(/Nenhum caso de melhoria nesta organização/i),
    ).toBeInTheDocument();
  });

  it("sets URL filter from synthesis card and distinguishes empty filter", async () => {
    const user = userEvent.setup();
    renderCockpit();
    await enterApp(user);
    await screen.findByTestId("cockpit-page");

    await user.click(screen.getByTestId("cockpit-filter-immediate"));
    await waitFor(() => {
      expect(screen.getByTestId("cockpit-filter-active")).toBeInTheDocument();
    });

    casesPayload = emptyCases();
    await user.click(screen.getByTestId("cockpit-refresh"));

    expect(
      await screen.findByTestId("cockpit-empty-filter"),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Nenhum caso de melhoria nesta organização/i),
    ).not.toBeInTheDocument();

    await user.click(screen.getByTestId("cockpit-clear-filters"));
    await waitFor(() => {
      expect(
        screen.queryByTestId("cockpit-filter-active"),
      ).not.toBeInTheDocument();
    });
  });

  it("applies intelligence freshness filter from URL on load", async () => {
    casesPayload = {
      ...populatedCases(),
      items: [populatedCases().items![1]],
    };
    const user = userEvent.setup();
    renderCockpit("/cockpit?intelligence_freshness=stale");
    await enterApp(user);

    expect(await screen.findByTestId("cockpit-filter-active")).toBeInTheDocument();
    expect(screen.getByTestId("cockpit-synth-ei-stale")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getAllByText("Retrabalho em inspeção").length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByText("Atrasos no atendimento")).not.toBeInTheDocument();
  });

  it("refreshes with GET invalidate only — no OI POST", async () => {
    const user = userEvent.setup();
    renderCockpit();
    await enterApp(user);
    await screen.findByTestId("cockpit-page");

    const postsBefore = postCalls.length;
    const getsBefore = getCalls.filter((u) =>
      u.includes("/iso-intelligence/cockpit/"),
    ).length;

    await user.click(screen.getByTestId("cockpit-refresh"));

    await waitFor(() => {
      const getsAfter = getCalls.filter((u) =>
        u.includes("/iso-intelligence/cockpit/"),
      ).length;
      expect(getsAfter).toBeGreaterThan(getsBefore);
    });
    expect(postCalls.length).toBe(postsBefore);
    expect(
      postCalls.some((u) => u.includes("organizational-intelligence") || u.includes("execution-intelligence")),
    ).toBe(false);
  });

  it("keeps previous summary when refresh fails partially", async () => {
    const user = userEvent.setup();
    renderCockpit();
    await enterApp(user);
    await screen.findByTestId("cockpit-synth-active");

    summaryFail = true;
    await user.click(screen.getByTestId("cockpit-refresh"));

    expect(
      await screen.findByText(/Falha ao atualizar o resumo/i),
    ).toBeInTheDocument();
    expect(screen.getByTestId("cockpit-synth-active")).toHaveTextContent("2");
    expect(
      screen.getAllByText("Atrasos no atendimento").length,
    ).toBeGreaterThan(0);
  });

  it("shows nav link Cockpit", async () => {
    const user = userEvent.setup();
    renderCockpit();
    await enterApp(user);
    expect(await screen.findByTestId("nav-cockpit")).toHaveAttribute(
      "href",
      "/cockpit",
    );
  });
});
