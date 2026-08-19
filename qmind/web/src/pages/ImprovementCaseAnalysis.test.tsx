import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { ImprovementCaseDetailPage } from "@/pages/ImprovementCaseDetailPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

type CaseRow = {
  id: string;
  organization_id: string;
  problem_statement: string;
  impact_statement: string;
  related_process: string;
  status: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

type RunRow = {
  id: string;
  organization_id: string;
  improvement_case_id: string;
  schema_version: string;
  request_id: string;
  correlation_id: string;
  generated_at: string;
  input_fingerprint: string;
  created_at: string;
  is_stale: boolean;
  analysis: {
    schema_version: string;
    core_organization_id: string;
    improvement_case_id: string;
    analysis_id: string;
    request_id: string;
    correlation_id: string;
    generated_at: string;
    context_status: string;
    interpretation_summary: string;
    hypotheses: Array<{
      code: string;
      statement: string;
      rationale: string;
      support_status: string;
      supporting_facts: string[];
      missing_information: string[];
      iso_basis: string[];
    }>;
    findings: Array<{
      code: string;
      title: string;
      description: string;
      relationship_to_problem: string;
      business_impact: string;
      supporting_facts: string[];
      missing_information: string[];
      iso_basis: string[];
      recommended_next_step: string;
      requires_human_validation: boolean;
    }>;
    limitations: string[];
  };
};

let caseRow: CaseRow;
let runs: RunRow[] = [];
let roles: string[] = ["org_admin"];
let profilePatchCount = 0;

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requestUrl(input: RequestInfo | URL): string {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

async function resolveRequest(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<{ url: string; method: string; body: Record<string, unknown> }> {
  const url = requestUrl(input);
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

function makeRun(overrides: Partial<RunRow> = {}): RunRow {
  return {
    id: `run-${runs.length + 1}`,
    organization_id: ORG,
    improvement_case_id: caseRow.id,
    schema_version: "1.0",
    request_id: "req-1",
    correlation_id: "corr-1",
    generated_at: "2026-08-19T15:00:00Z",
    input_fingerprint: "fp1",
    created_at: "2026-08-19T15:00:00Z",
    is_stale: false,
    analysis: {
      schema_version: "1.0",
      core_organization_id: ORG,
      improvement_case_id: caseRow.id,
      analysis_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaa01",
      request_id: "req-1",
      correlation_id: "corr-1",
      generated_at: "2026-08-19T15:00:00Z",
      context_status: "ready_for_initial_analysis",
      interpretation_summary:
        "Síntese interpretativa do problema e do processo informado.",
      hypotheses: [
        {
          code: "H-1",
          statement: "Hipótese sobre o processo informado",
          rationale: "Racional",
          support_status: "requires_validation",
          supporting_facts: ["problem.statement"],
          missing_information: ["evidence.process_flow"],
          iso_basis: ["4.1", "4.4"],
        },
      ],
      findings: [
        {
          code: "F-1",
          title: "Atenção ao contexto do processo",
          description: "Achado interpretativo de atenção",
          relationship_to_problem: "Organiza a atenção no processo",
          business_impact: "Impacto ainda sem verificação operacional",
          supporting_facts: ["problem.related_process"],
          missing_information: [],
          iso_basis: ["4.4"],
          recommended_next_step: "Mapear o fluxo atual do processo",
          requires_human_validation: true,
        },
      ],
      limitations: ["Sem evidências nesta versão."],
    },
    ...overrides,
  };
}

function shell(ui: ReactNode, initial: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <OrganizationProvider>
          <MemoryRouter initialEntries={[initial]}>
            <Routes>
              <Route element={<AppShell />}>
                <Route path="improvement-cases/:caseId" element={ui} />
              </Route>
            </Routes>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

function installFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const { url, method, body } = await resolveRequest(input, init);

      if (url.includes("/organizations/me/memberships")) {
        return jsonResponse([
          {
            id: "m-1",
            organization_id: ORG,
            organization_name: "Org Test",
            roles,
            status: "active",
          },
        ]);
      }
      if (url.includes("/profile") && method === "GET") {
        return jsonResponse({
          organization_id: ORG,
          trade_name: "Acme",
          legal_name: "",
          summary: "Resumo",
          industry: "Saúde",
          business_model: "b2b",
          employee_range: "11-50",
          unit_count: 1,
          certification_status: "none",
          quality_structure: "formal",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        });
      }
      if (
        url.includes(`/improvement-cases/${caseRow.id}`) &&
        method === "GET" &&
        !url.includes("analysis-runs")
      ) {
        return jsonResponse(caseRow);
      }
      if (url.includes("analysis-runs") && method === "GET") {
        return jsonResponse(runs);
      }
      if (url.includes("/actions") && method === "GET") {
        return jsonResponse({ plan: null, items: [] });
      }
      if (url.includes("/members")) {
        return jsonResponse([]);
      }
      if (url.includes("analysis-runs") && method === "POST") {
        const run = makeRun({
          id: `run-${runs.length + 1}`,
          is_stale: false,
        });
        runs = [run, ...runs.map((r) => ({ ...r, is_stale: false }))];
        return jsonResponse(run, 201);
      }
      if (
        url.includes(`/improvement-cases/${caseRow.id}`) &&
        method === "PATCH"
      ) {
        caseRow = { ...caseRow, ...body, updated_at: "2026-08-19T16:00:00Z" };
        if (body.problem_statement || body.impact_statement || body.related_process) {
          if (runs[0]) runs[0] = { ...runs[0], is_stale: true };
          profilePatchCount += 1;
        }
        return jsonResponse(caseRow);
      }
      return jsonResponse({ detail: `unmocked ${method} ${url}` }, 404);
    }),
  );
}

describe("ImprovementCaseDetailPage analysis", () => {
  beforeEach(() => {
    resetConfigCache();
    resetQmindClient();
    roles = ["org_admin"];
    runs = [];
    profilePatchCount = 0;
    caseRow = {
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
    installFetch();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows empty analysis and generates for authorized user", async () => {
    const user = userEvent.setup();
    render(shell(<ImprovementCaseDetailPage />, "/improvement-cases/case-1"));
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("ic-analysis-empty")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ic-generate-analysis")).toHaveTextContent(
      "Gerar análise",
    );

    await user.click(screen.getByTestId("ic-generate-analysis"));
    await waitFor(() =>
      expect(screen.getByTestId("ic-analysis-content")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("ic-interpretation")).toHaveTextContent(
      /Síntese interpretativa/,
    );
    expect(screen.getByText(/Requer validação/)).toBeInTheDocument();
    expect(screen.getByTestId("ic-finding-F-1")).toBeInTheDocument();
    expect(screen.getByTestId("ic-recommended-next-step")).toHaveTextContent(
      /Mapear o fluxo/,
    );
    expect(screen.getByTestId("ic-limitations")).toBeInTheDocument();
    expect(screen.getByTestId("ic-context-status")).toHaveTextContent(
      "Pronto para análise inicial",
    );

    await user.click(screen.getByTestId("ic-iso-toggle"));
    expect(screen.getByTestId("ic-iso-disclaimer")).toHaveTextContent(
      /estrutura de interpretação/,
    );

    const finding = screen.getByTestId("ic-finding-F-1").textContent ?? "";
    expect(finding.toLowerCase()).not.toMatch(/não conforme|nao conforme/);
    expect(finding.toLowerCase()).not.toMatch(/\bnc\b/);
  });

  it("hides generate for reader", async () => {
    roles = ["reader"];
    const user = userEvent.setup();
    runs = [makeRun()];
    render(shell(<ImprovementCaseDetailPage />, "/improvement-cases/case-1"));
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("ic-analysis-content")).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("ic-generate-analysis")).not.toBeInTheDocument();
  });

  it("marks stale after fact edit and preserves history on reanalyze", async () => {
    const user = userEvent.setup();
    runs = [makeRun({ id: "run-1" })];
    render(shell(<ImprovementCaseDetailPage />, "/improvement-cases/case-1"));
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("ic-analysis-content")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("ic-edit-toggle"));
    fireEvent.change(screen.getByTestId("ic-detail-problem"), {
      target: { value: "Problema atualizado" },
    });
    await user.click(screen.getByTestId("ic-detail-save"));

    await waitFor(() =>
      expect(screen.getByTestId("ic-analysis-stale")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("ic-refresh-analysis"));
    await waitFor(() => {
      expect(screen.queryByTestId("ic-analysis-stale")).not.toBeInTheDocument();
      expect(screen.getByTestId("ic-history-run-1")).toBeInTheDocument();
      expect(screen.getByTestId("ic-history-run-2")).toBeInTheDocument();
    });
  });
});
