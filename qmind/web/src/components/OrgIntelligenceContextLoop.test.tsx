import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider, useOrganization } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { OrgIntelligenceContextLoop } from "@/components/OrgIntelligenceContextLoop";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";
import {
  ORG_PROFILE_FIELD_LABELS,
  collectMissingProfileFields,
  formatProfileFieldDisplay,
} from "@/lib/orgProfileLabels";
import { canEditOrganizationProfile } from "@/lib/permissions";
import type { OrganizationProfile } from "@/api/orgProfileApi";

const ORG_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const ORG_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

function membershipsFor(rolesA: string[], rolesB: string[] = ["org_admin"]) {
  return [
    {
      id: "m-a",
      organization_id: ORG_A,
      organization_name: "Org A",
      roles: rolesA,
      status: "active",
    },
    {
      id: "m-b",
      organization_id: ORG_B,
      organization_name: "Org B",
      roles: rolesB,
      status: "active",
    },
  ];
}

function emptyProfile(orgId: string): OrganizationProfile {
  return {
    organization_id: orgId,
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
  };
}

function partialProfile(orgId: string): OrganizationProfile {
  return {
    ...emptyProfile(orgId),
    trade_name: "Padaria Central",
    industry: "Alimentos",
    business_model: "b2c",
  };
}

function fullProfile(orgId: string): OrganizationProfile {
  return {
    organization_id: orgId,
    trade_name: "Acme Diagnóstico",
    legal_name: "Acme Diagnóstico Ltda",
    summary: "Laboratório regional",
    industry: "Saúde",
    business_model: "b2b",
    employee_range: "51-200",
    unit_count: 3,
    certification_status: "in_progress",
    quality_structure: "formal_partial",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function runFor(
  orgId: string,
  missing: string[] = ["employee_range", "unit_count"],
) {
  return {
    id: `run-${orgId.slice(0, 8)}-old`,
    organization_id: orgId,
    schema_version: "1.0",
    request_id: "req-old",
    correlation_id: "corr-old",
    generated_at: "2026-08-17T10:00:00Z",
    created_at: "2026-08-17T10:00:01Z",
    insights: {
      schema_version: "1.0",
      core_organization_id: orgId,
      request_id: "req-old",
      correlation_id: "corr-old",
      generated_at: "2026-08-17T10:00:00Z",
      insights: [
        {
          insight_id: "insight-clause-4-gap",
          type: "CONTEXT",
          title: "Cláusula 4 incompleta",
          summary: "Faltam informações",
          confidence: null,
          evidence_refs: [],
          explanation: {
            reasons: ["clause:4", "category:CONTEXT", "priority:MEDIUM"],
            evidence_refs: [],
            supporting_facts: missing,
            mechanism_version: null,
          },
        },
      ],
      explanations: [],
      metadata: null,
    },
  };
}

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
                      {children ?? <OrgIntelligenceContextLoop />}
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

function agendaEmpty() {
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

describe("org profile labels and permissions", () => {
  it("uses friendly labels and maps only direct OI gaps", () => {
    expect(ORG_PROFILE_FIELD_LABELS.employee_range).toBe(
      "Número de colaboradores",
    );
    expect(ORG_PROFILE_FIELD_LABELS.quality_structure).toBe(
      "Estrutura responsável pela qualidade",
    );
    const mapped = collectMissingProfileFields([
      "employee_range",
      "not_a_field",
      "trade_name",
    ]);
    expect([...mapped].sort()).toEqual(["employee_range", "trade_name"]);

    const empty = emptyProfile(ORG_A);
    expect(formatProfileFieldDisplay(empty, "trade_name")).toBe("Não informado");
    expect(formatProfileFieldDisplay(partialProfile(ORG_A), "trade_name")).toBe(
      "Padaria Central",
    );
    expect(formatProfileFieldDisplay(fullProfile(ORG_A), "employee_range")).toMatch(
      /51 a 200/,
    );

    expect(canEditOrganizationProfile(["reader"])).toBe(false);
    expect(canEditOrganizationProfile(["org_admin"])).toBe(true);
  });
});

describe("OrgIntelligenceContextLoop", () => {
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

  it("shows empty profile summary as not informed", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      if (url.includes("/memberships")) {
        return jsonResponse(membershipsFor(["org_admin"]));
      }
      if (url.includes("/organizations/current/profile")) {
        return jsonResponse(emptyProfile(ORG_A));
      }
      if (url.includes("/intelligence/runs")) return jsonResponse([]);
      if (url.includes("/agenda/board")) return agendaEmpty();
      if (url.includes("/assessments")) return jsonResponse([]);
      return jsonResponse({ code: "not_found", message: url }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Harness />);
    await enterApp(user);
    await waitFor(() => {
      expect(screen.getByTestId("org-context-summary-trade_name").textContent).toBe(
        "Não informado",
      );
      expect(screen.getByTestId("org-context-summary-industry").textContent).toBe(
        "Não informado",
      );
    });
  });

  it("edits profile, PATCHes, marks analysis stale, and reanalyzes without rewriting history", async () => {
    const user = userEvent.setup();
    let profile = partialProfile(ORG_A);
    const runs = [runFor(ORG_A)];
    const patches: unknown[] = [];

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const method =
        (input instanceof Request ? input.method : init?.method) ?? "GET";
      const headers = requestHeaders(input, init);
      const orgHeader = headers.get("X-Organization-Id");

      if (url.includes("/memberships")) {
        return jsonResponse(membershipsFor(["org_admin"]));
      }
      if (url.includes("/organizations/current/profile") && method === "PATCH") {
        let body: Record<string, unknown> = {};
        if (input instanceof Request) {
          body = (await input.clone().json()) as Record<string, unknown>;
        } else if (typeof init?.body === "string") {
          body = JSON.parse(init.body) as Record<string, unknown>;
        }
        patches.push(body);
        profile = {
          ...profile,
          ...(body as Partial<OrganizationProfile>),
          organization_id: ORG_A,
          updated_at: "2026-08-17T12:00:00Z",
        };
        return jsonResponse(profile);
      }
      if (url.includes("/organizations/current/profile")) {
        return jsonResponse(profile);
      }
      if (url.includes("/intelligence/analyze") && method === "POST") {
        const next = {
          ...runFor(ORG_A, []),
          id: "run-new",
          request_id: "req-new",
          generated_at: "2026-08-17T12:05:00Z",
          created_at: "2026-08-17T12:05:01Z",
        };
        next.insights.request_id = "req-new";
        next.insights.generated_at = "2026-08-17T12:05:00Z";
        next.insights.insights = [
          {
            insight_id: "insight-clause-4-ready",
            type: "CONTEXT",
            title: "Cláusula 4 disponível",
            summary: "Completa",
            confidence: null,
            evidence_refs: [],
            explanation: {
              reasons: ["clause:4", "category:CONTEXT", "priority:LOW"],
              evidence_refs: [],
              supporting_facts: [],
              mechanism_version: null,
            },
          },
        ];
        runs.unshift(next);
        return jsonResponse(next.insights);
      }
      if (url.includes("/intelligence/runs")) {
        if (orgHeader !== ORG_A && orgHeader !== ORG_B) {
          return jsonResponse({ code: "forbidden_organization" }, 403);
        }
        return jsonResponse(orgHeader === ORG_A ? [runs[0]] : []);
      }
      if (url.includes("/agenda/board")) return agendaEmpty();
      if (url.includes("/assessments")) return jsonResponse([]);
      return jsonResponse({ code: "not_found", message: url }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Harness />);
    await enterApp(user);

    await waitFor(() => {
      expect(screen.getByTestId("org-context-summary-trade_name").textContent).toBe(
        "Padaria Central",
      );
      expect(screen.getByTestId("oi-insights-list")).toBeTruthy();
    });

    await user.click(screen.getByTestId("org-context-edit"));
    const form = screen.getByTestId("org-context-form");
    expect(within(form).getByText("Nome da organização")).toBeTruthy();
    expect(within(form).getByText("Número de colaboradores")).toBeTruthy();
    expect(within(form).queryByText("employee_range")).toBeNull();
    expect(within(form).queryByText("quality_structure")).toBeNull();

    expect(screen.getByTestId("org-context-needed-employee_range")).toBeTruthy();
    expect(
      screen.getByTestId("org-context-field-employee_range").getAttribute("data-needed"),
    ).toBe("true");

    await user.selectOptions(
      within(screen.getByTestId("org-context-field-employee_range")).getByRole(
        "combobox",
      ),
      "11-50",
    );
    await user.clear(
      within(screen.getByTestId("org-context-field-unit_count")).getByRole(
        "spinbutton",
      ),
    );
    await user.type(
      within(screen.getByTestId("org-context-field-unit_count")).getByRole(
        "spinbutton",
      ),
      "2",
    );

    await user.click(screen.getByTestId("org-context-save"));
    await waitFor(() => {
      expect(screen.getByTestId("org-context-saved")).toBeTruthy();
      expect(screen.getByTestId("oi-analysis-stale")).toBeTruthy();
    });
    expect(patches[0]).toMatchObject({
      employee_range: "11-50",
      unit_count: 2,
      trade_name: "Padaria Central",
    });
    expect(runs).toHaveLength(1);
    expect(runs[0]!.id).toBe("run-aaaaaaaa-old");

    await user.click(screen.getByTestId("oi-stale-analyze-button"));
    await waitFor(() => {
      expect(screen.queryByTestId("oi-analysis-stale")).toBeNull();
      expect(screen.getByText("Cláusula 4 disponível")).toBeTruthy();
    });
    expect(runs[0]!.id).toBe("run-new");
    expect(runs.some((r) => r.id === "run-aaaaaaaa-old")).toBe(true);
  });

  it("hides edit for reader and isolates tenant switch", async () => {
    const user = userEvent.setup();
    const profiles: Record<string, OrganizationProfile> = {
      [ORG_A]: fullProfile(ORG_A),
      [ORG_B]: emptyProfile(ORG_B),
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = requestUrl(input);
      const headers = requestHeaders(input);
      const orgHeader = headers.get("X-Organization-Id") ?? ORG_A;
      if (url.includes("/memberships")) {
        return jsonResponse(membershipsFor(["reader"], ["org_admin"]));
      }
      if (url.includes("/organizations/current/profile")) {
        return jsonResponse(profiles[orgHeader] ?? emptyProfile(orgHeader));
      }
      if (url.includes("/intelligence/runs")) {
        return jsonResponse(orgHeader === ORG_A ? [runFor(ORG_A)] : []);
      }
      if (url.includes("/agenda/board")) return agendaEmpty();
      if (url.includes("/assessments")) return jsonResponse([]);
      return jsonResponse({ code: "not_found", message: url }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Harness />);
    await enterApp(user);

    await waitFor(() => {
      expect(screen.getByTestId("org-context-summary-trade_name").textContent).toBe(
        "Acme Diagnóstico",
      );
    });
    expect(screen.queryByTestId("org-context-edit")).toBeNull();

    await user.click(screen.getByRole("button", { name: "Switch B" }));
    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_B);
      expect(screen.getByTestId("org-context-summary-trade_name").textContent).toBe(
        "Não informado",
      );
      expect(
        screen.getByText(
          /ainda não possui uma análise de Inteligência Organizacional/i,
        ),
      ).toBeTruthy();
    });
    expect(screen.queryByTestId("oi-insights-list")).toBeNull();
    expect(screen.getByTestId("org-context-edit")).toBeTruthy();
  });
});
