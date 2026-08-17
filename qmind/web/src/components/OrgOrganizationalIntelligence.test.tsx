import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider, useOrganization } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { OrgOrganizationalIntelligence } from "@/components/OrgOrganizationalIntelligence";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";
import { insightReasonValue } from "@/api/organizationalIntelligenceApi";

const ORG_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const ORG_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

const memberships = [
  {
    id: "m-a",
    organization_id: ORG_A,
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
];

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

function requestHeaders(input: RequestInfo | URL, init?: RequestInit): Headers {
  if (input instanceof Request) return new Headers(input.headers);
  return new Headers(init?.headers);
}

function insight(clause: string, missing: string[] = []) {
  return {
    insight_id: `insight-clause-${clause}-ready`,
    type: clause === "4" ? "CONTEXT" : "SUPPORT",
    title: `Cláusula ${clause} disponível`,
    summary: `Informações mínimas presentes para a cláusula ${clause}.`,
    confidence: null,
    evidence_refs: [],
    explanation: {
      reasons: [`clause:${clause}`, "category:CONTEXT", "priority:LOW"],
      evidence_refs: [],
      supporting_facts: missing,
      mechanism_version: null,
    },
  };
}

function runFor(orgId: string, opts?: { missing7?: string[] }) {
  return {
    id: `run-${orgId.slice(0, 8)}`,
    organization_id: orgId,
    schema_version: "1.0",
    request_id: "req-1",
    correlation_id: "corr-1",
    generated_at: "2026-08-17T19:00:00Z",
    created_at: "2026-08-17T19:00:01Z",
    insights: {
      schema_version: "1.0",
      core_organization_id: orgId,
      request_id: "req-1",
      correlation_id: "corr-1",
      generated_at: "2026-08-17T19:00:00Z",
      insights: [
        insight("4"),
        insight("7", opts?.missing7 ?? ["trade_name"]),
      ],
      explanations: [],
      metadata: null,
    },
  };
}

function SwitchProbe({ children }: { children: ReactNode }) {
  const org = useOrganization();
  return (
    <div>
      <span data-testid="current-org">{org.currentOrganizationId}</span>
      <button type="button" onClick={() => void org.switchOrganization(ORG_B)}>
        Switch B
      </button>
      <button type="button" onClick={() => void org.switchOrganization(ORG_A)}>
        Switch A
      </button>
      {children}
    </div>
  );
}

function Harness({ children }: { children?: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <OrganizationProvider>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route element={<AppShell />}>
                <Route
                  path="/"
                  element={
                    <SwitchProbe>
                      {children ?? <OrgOrganizationalIntelligence />}
                    </SwitchProbe>
                  }
                />
              </Route>
            </Routes>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe("insightReasonValue", () => {
  it("reads clause and priority tokens from contract reasons", () => {
    const sample = insight("4", ["industry"]);
    expect(insightReasonValue(sample, "clause")).toBe("4");
    expect(insightReasonValue(sample, "priority")).toBe("LOW");
  });
});

describe("OrgOrganizationalIntelligence", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_ENVIRONMENT", "local");
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8008");
    resetConfigCache();
    resetQmindClient();
    sessionStorage.clear();
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("shows empty state when there is no analysis", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      if (url.includes("/memberships")) return jsonResponse(memberships);
      if (url.includes("/intelligence/runs")) return jsonResponse([]);
      if (url.includes("/agenda/board")) {
        return jsonResponse({
          timezone: "America/Sao_Paulo",
          selected_date: "2026-01-01",
          next_up: null,
          today: [],
          selected_day: [],
          overdue: [],
          in_progress_assessments: [],
          month_markers: [],
        });
      }
      if (url.includes("/assessments")) return jsonResponse([]);
      return jsonResponse({ code: "not_found", message: url }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Harness />);
    await enterApp(user);

    await waitFor(() => {
      expect(
        screen.getByText(
          /ainda não possui uma análise de Inteligência Organizacional/i,
        ),
      ).toBeTruthy();
    });
    expect(screen.getByTestId("oi-analyze-button").textContent).toMatch(/Gerar análise/);
    expect(
      screen.getByText(/Prontidão do contexto em relação à ISO 9001/i),
    ).toBeTruthy();
  });

  it("loads latest analysis and renders clause 4/7 with missing facts", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      const headers = requestHeaders(input);
      const orgHeader = headers.get("X-Organization-Id");
      if (url.includes("/memberships")) return jsonResponse(memberships);
      if (url.includes("/intelligence/runs")) {
        return jsonResponse([runFor(orgHeader === ORG_B ? ORG_B : ORG_A)]);
      }
      if (url.includes("/agenda/board")) {
        return jsonResponse({
          timezone: "America/Sao_Paulo",
          selected_date: "2026-01-01",
          next_up: null,
          today: [],
          selected_day: [],
          overdue: [],
          in_progress_assessments: [],
          month_markers: [],
        });
      }
      if (url.includes("/assessments")) return jsonResponse([]);
      return jsonResponse({ code: "not_found", message: url }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Harness />);
    await enterApp(user);

    await waitFor(() => {
      expect(screen.getByTestId("oi-last-analyzed")).toBeTruthy();
    });

    const cards = screen.getAllByTestId("oi-insight");
    expect(cards).toHaveLength(2);
    expect(cards[0]!.getAttribute("data-clause")).toBe("4");
    expect(cards[1]!.getAttribute("data-clause")).toBe("7");
    expect(within(cards[0]!).getByTestId("oi-insight-clause").textContent).toMatch(
      /Cláusula 4/,
    );
    expect(within(cards[1]!).getByTestId("oi-insight-clause").textContent).toMatch(
      /Cláusula 7/,
    );
    expect(within(cards[1]!).getByTestId("oi-insight-missing").textContent).toMatch(
      /trade_name/,
    );
    expect(screen.getByTestId("oi-analyze-button").textContent).toMatch(
      /Atualizar análise/,
    );
  });

  it("runs analyze, refetches latest, and shows controlled errors", async () => {
    const user = userEvent.setup();
    let hasRun = false;
    let failNextAnalyze = false;

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const method = (input instanceof Request ? input.method : init?.method) ?? "GET";
      if (url.includes("/memberships")) return jsonResponse(memberships);
      if (url.includes("/intelligence/analyze") && method === "POST") {
        if (failNextAnalyze) {
          return jsonResponse(
            {
              code: "oi_timeout",
              message: "QMind OI request timed out",
              correlation_id: "c-to",
            },
            504,
          );
        }
        hasRun = true;
        return jsonResponse(runFor(ORG_A).insights);
      }
      if (url.includes("/intelligence/runs")) {
        return jsonResponse(hasRun ? [runFor(ORG_A)] : []);
      }
      if (url.includes("/agenda/board")) {
        return jsonResponse({
          timezone: "America/Sao_Paulo",
          selected_date: "2026-01-01",
          next_up: null,
          today: [],
          selected_day: [],
          overdue: [],
          in_progress_assessments: [],
          month_markers: [],
        });
      }
      if (url.includes("/assessments")) return jsonResponse([]);
      return jsonResponse({ code: "not_found", message: url }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Harness />);
    await enterApp(user);

    await waitFor(() => {
      expect(screen.getByTestId("oi-analyze-button")).toBeTruthy();
    });

    await user.click(screen.getByTestId("oi-analyze-button"));
    await waitFor(() => {
      expect(screen.getByTestId("oi-insights-list")).toBeTruthy();
      expect(screen.getAllByTestId("oi-insight")).toHaveLength(2);
    });

    failNextAnalyze = true;
    await user.click(screen.getByTestId("oi-analyze-button"));
    await waitFor(() => {
      expect(screen.getByTestId("api-error-code").textContent).toBe("oi_timeout");
    });
    expect(
      screen.getByText(/Tempo esgotado ao consultar a Inteligência Organizacional/i),
    ).toBeTruthy();
  });

  it("tenant switch A → B never shows stale A insights", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      const headers = requestHeaders(input);
      const orgHeader = headers.get("X-Organization-Id");
      if (url.includes("/memberships")) return jsonResponse(memberships);
      if (url.includes("/intelligence/runs")) {
        if (orgHeader === ORG_A) return jsonResponse([runFor(ORG_A)]);
        if (orgHeader === ORG_B) return jsonResponse([]);
        return jsonResponse({ code: "forbidden_organization" }, 403);
      }
      if (url.includes("/agenda/board")) {
        return jsonResponse({
          timezone: "America/Sao_Paulo",
          selected_date: "2026-01-01",
          next_up: null,
          today: [],
          selected_day: [],
          overdue: [],
          in_progress_assessments: [],
          month_markers: [],
        });
      }
      if (url.includes("/assessments")) return jsonResponse([]);
      return jsonResponse({ code: "not_found", message: url }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Harness />);
    await enterApp(user);

    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_A);
      expect(screen.getByTestId("oi-insights-list")).toBeTruthy();
    });

    await user.click(screen.getByRole("button", { name: "Switch B" }));
    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_B);
      expect(
        screen.getByText(
          /ainda não possui uma análise de Inteligência Organizacional/i,
        ),
      ).toBeTruthy();
    });
    expect(screen.queryByTestId("oi-insights-list")).toBeNull();
  });
});
