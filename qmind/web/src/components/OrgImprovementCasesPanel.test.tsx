import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider, useOrganization } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { OrgImprovementCasesPanel } from "@/components/OrgImprovementCasesPanel";
import { ImprovementCaseDetailPage } from "@/pages/ImprovementCaseDetailPage";
import { useImprovementCases } from "@/hooks/useImprovementCases";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const ORG_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

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

let cases: CaseRow[] = [];
let roles: string[] = ["org_admin"];

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
  if (raw == null && req) {
    raw = await req.clone().text();
  }
  let body: Record<string, unknown> = {};
  if (typeof raw === "string" && raw.length > 0) {
    body = JSON.parse(raw) as Record<string, unknown>;
  }
  return { url, method, body };
}

function shell(ui: ReactNode, initial = "/assessments") {
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
                <Route path="assessments" element={ui} />
                <Route
                  path="improvement-cases/:caseId"
                  element={<ImprovementCaseDetailPage />}
                />
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
      if (url.includes("/improvement-cases") && method === "POST") {
        const row: CaseRow = {
          id: `case-${cases.length + 1}`,
          organization_id: ORG,
          problem_statement: String(body.problem_statement ?? ""),
          impact_statement: String(body.impact_statement ?? ""),
          related_process: String(body.related_process ?? ""),
          status: "open",
          created_by: "user-1",
          created_at: "2026-08-19T12:00:00Z",
          updated_at: "2026-08-19T12:00:00Z",
        };
        cases = [row, ...cases];
        return jsonResponse(row, 201);
      }
      if (
        url.includes("/improvement-cases") &&
        method === "GET" &&
        !/improvement-cases\/[^/?]+$/.test(url)
      ) {
        return jsonResponse(cases);
      }
      const detailMatch = url.match(/improvement-cases\/([^/?]+)$/);
      if (detailMatch && method === "GET") {
        const found = cases.find((c) => c.id === detailMatch[1]);
        if (!found) return jsonResponse({ detail: "missing" }, 404);
        return jsonResponse(found);
      }
      if (detailMatch && method === "PATCH") {
        const idx = cases.findIndex((c) => c.id === detailMatch[1]);
        if (idx < 0) return jsonResponse({ detail: "missing" }, 404);
        cases[idx] = {
          ...cases[idx]!,
          ...body,
          updated_at: "2026-08-19T13:00:00Z",
        } as CaseRow;
        return jsonResponse(cases[idx]);
      }
      if (url.includes("/profile")) {
        return jsonResponse({
          organization_id: ORG,
          trade_name: "",
          legal_name: "",
          summary: "",
          industry: "",
          business_model: "",
          employee_range: "",
          unit_count: null,
          certification_status: "unknown",
          quality_structure: "unknown",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        });
      }
      return jsonResponse({ detail: `unmocked ${method} ${url}` }, 404);
    }),
  );
}

describe("OrgImprovementCasesPanel", () => {
  beforeEach(() => {
    resetConfigCache();
    resetQmindClient();
    cases = [];
    roles = ["org_admin"];
    installFetch();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows empty state and hides register for reader", async () => {
    roles = ["reader"];
    const user = userEvent.setup();
    render(shell(<OrgImprovementCasesPanel />));
    await enterApp(user);

    await waitFor(() => {
      expect(screen.getByTestId("improvement-cases-empty")).toHaveTextContent(
        "Nenhum problema está sendo acompanhado.",
      );
    });
    expect(
      screen.queryByTestId("register-improvement-case"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText(/conforme|não conforme|certifica/i)).toBeNull();
  });

  it("allows authorized user to register with three business questions", async () => {
    const user = userEvent.setup();
    render(shell(<OrgImprovementCasesPanel />));
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("register-improvement-case")).toBeInTheDocument(),
    );
    await user.click(screen.getByTestId("register-improvement-case"));

    expect(
      screen.getByText("Qual problema está acontecendo?"),
    ).toBeInTheDocument();
    expect(screen.getByText("Qual é o impacto observado?")).toBeInTheDocument();
    expect(
      screen.getByText("Em qual processo ele acontece?"),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByTestId("ic-problem"), {
      target: { value: "Atrasos nas entregas" },
    });
    fireEvent.change(screen.getByTestId("ic-impact"), {
      target: { value: "Quebra de SLA" },
    });
    fireEvent.change(screen.getByTestId("ic-process"), {
      target: { value: "Pedidos" },
    });
    await user.click(screen.getByTestId("ic-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("improvement-cases-list")).toBeInTheDocument();
      expect(screen.getByText(/Atrasos nas entregas/)).toBeInTheDocument();
      expect(screen.getByText(/Aberto/)).toBeInTheDocument();
    });
  });
});

describe("ImprovementCaseDetailPage", () => {
  beforeEach(() => {
    resetConfigCache();
    resetQmindClient();
    roles = ["org_admin"];
    cases = [
      {
        id: "case-1",
        organization_id: ORG,
        problem_statement: "Atrasos",
        impact_statement: "SLA",
        related_process: "Pedidos",
        status: "open",
        created_by: "user-1",
        created_at: "2026-08-19T12:00:00Z",
        updated_at: "2026-08-19T12:00:00Z",
      },
    ];
    installFetch();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows honest future sections and allows status transition", async () => {
    const user = userEvent.setup();
    render(shell(<div />, "/improvement-cases/case-1"));
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("improvement-case-detail")).toBeInTheDocument(),
    );

    expect(screen.getByTestId("ic-section-context")).toHaveTextContent(
      /próxima etapa da ISO Intelligence/i,
    );
    expect(screen.getByTestId("ic-section-analysis")).toHaveTextContent(
      /Nenhuma análise foi gerada/i,
    );
    expect(screen.getByTestId("ic-section-actions")).toHaveTextContent(
      /após a primeira análise/i,
    );
    expect(screen.getByTestId("ic-section-evolution")).toHaveTextContent(
      /após existirem análises e ações/i,
    );
    expect(screen.queryByText(/conforme|não conforme|certifica/i)).toBeNull();

    await user.click(screen.getByTestId("ic-status-analyzing"));
    await waitFor(() => {
      expect(screen.getByTestId("ic-detail-status")).toHaveTextContent(
        "Em análise",
      );
    });
  });
});

function CasesProbe() {
  const org = useOrganization();
  const cases = useImprovementCases();
  const first = cases.data?.[0];
  return (
    <div>
      <span data-testid="current-org">{org.currentOrganizationId}</span>
      <span data-testid="case-problem">{first?.problem_statement ?? ""}</span>
      <span data-testid="case-org">{first?.organization_id ?? ""}</span>
      <button type="button" onClick={() => void org.switchOrganization(ORG_B)}>
        Switch B
      </button>
    </div>
  );
}

describe("useImprovementCases tenant switch", () => {
  beforeEach(() => {
    resetConfigCache();
    resetQmindClient();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("A → B never shows org A problems after switch; discards stale A", async () => {
    const user = userEvent.setup();
    let resolveA: ((r: Response) => void) | null = null;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const { url, method } = await resolveRequest(input, init);
        const headers =
          input instanceof Request
            ? new Headers(input.headers)
            : new Headers(init?.headers);
        const orgHeader = headers.get("X-Organization-Id");

        if (url.includes("/organizations/me/memberships")) {
          return jsonResponse([
            {
              id: "m-a",
              organization_id: ORG,
              organization_name: "Org A",
              roles: ["org_admin"],
              status: "active",
            },
            {
              id: "m-b",
              organization_id: ORG_B,
              organization_name: "Org B",
              roles: ["org_admin"],
              status: "active",
            },
          ]);
        }
        if (
          url.includes("/improvement-cases") &&
          method === "GET" &&
          !/improvement-cases\/[^/?]+$/.test(url)
        ) {
          if (orgHeader === ORG) {
            return new Promise<Response>((resolve) => {
              resolveA = resolve;
            });
          }
          return jsonResponse([
            {
              id: "case-b",
              organization_id: ORG_B,
              problem_statement: "Problema B",
              impact_statement: "Impacto B",
              related_process: "Proc B",
              status: "open",
              created_by: "user-1",
              created_at: "2026-08-19T12:00:00Z",
              updated_at: "2026-08-19T12:00:00Z",
            },
          ]);
        }
        if (url.includes("/profile")) {
          return jsonResponse({
            organization_id: orgHeader,
            trade_name: "",
            legal_name: "",
            summary: "",
            industry: "",
            business_model: "",
            employee_range: "",
            unit_count: null,
            certification_status: "unknown",
            quality_structure: "unknown",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          });
        }
        return jsonResponse({ detail: `unmocked ${method} ${url}` }, 404);
      }),
    );

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 0 } },
    });
    render(
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <OrganizationProvider>
            <MemoryRouter initialEntries={["/"]}>
              <Routes>
                <Route element={<AppShell />}>
                  <Route path="/" element={<CasesProbe />} />
                </Route>
              </Routes>
            </MemoryRouter>
          </OrganizationProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("current-org")).toHaveTextContent(ORG),
    );

    await user.click(screen.getByRole("button", { name: "Switch B" }));
    await waitFor(() => {
      expect(screen.getByTestId("current-org")).toHaveTextContent(ORG_B);
      expect(screen.getByTestId("case-problem")).toHaveTextContent("Problema B");
      expect(screen.getByTestId("case-org")).toHaveTextContent(ORG_B);
    });

    // Late A response must not overwrite B
    resolveA?.(
      jsonResponse([
        {
          id: "case-a",
          organization_id: ORG,
          problem_statement: "Problema A stale",
          impact_statement: "Impacto A",
          related_process: "Proc A",
          status: "open",
          created_by: "user-1",
          created_at: "2026-08-19T12:00:00Z",
          updated_at: "2026-08-19T12:00:00Z",
        },
      ]),
    );

    await new Promise((r) => setTimeout(r, 50));
    expect(screen.getByTestId("case-problem")).toHaveTextContent("Problema B");
    expect(screen.queryByText(/Problema A stale/)).toBeNull();
  });
});
