import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { AssessmentsPage } from "@/pages/AssessmentsPage";
import { NewAssessmentPage } from "@/pages/NewAssessmentPage";
import { AssessmentDetailPage } from "@/pages/AssessmentDetailPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { resetTenantContext } from "@/api/tenantContext";

const ORG_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const ORG_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const MODEL = "11111111-1111-4111-8111-111111111111";
const SV = "22222222-2222-4222-8222-222222222222";
const REQ = "33333333-3333-4333-8333-333333333333";
const AID = "44444444-4444-4444-8444-444444444444";
const MEMBERSHIP = "55555555-5555-4555-8555-555555555555";
const MEMBERSHIP_B = "77777777-7777-4777-8777-777777777777";
const SCOPE_ID = "66666666-6666-4666-8666-666666666666";
const EXTRA_MEMBER = "88888888-8888-4888-8888-888888888888";

type Roles = string[];

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function urlOf(input: RequestInfo | URL) {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.href;
  return input.url;
}

async function readJsonBody(input: RequestInfo | URL, init?: RequestInit) {
  if (typeof init?.body === "string") return JSON.parse(init.body) as Record<string, unknown>;
  if (input instanceof Request) {
    try {
      return (await input.clone().json()) as Record<string, unknown>;
    } catch {
      return {};
    }
  }
  return {};
}

function orgHeader(input: RequestInfo | URL, init?: RequestInit): string | null {
  if (input instanceof Request) return input.headers.get("X-Organization-Id");
  const h = new Headers(init?.headers);
  return h.get("X-Organization-Id");
}

function harness(initial: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });

  function App() {
    return (
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <OrganizationProvider>
            <MemoryRouter initialEntries={[initial]}>
              <Routes>
                <Route element={<AppShell />}>
                  <Route path="assessments" element={<AssessmentsPage />} />
                  <Route path="assessments/new" element={<NewAssessmentPage />} />
                  <Route
                    path="assessments/:assessmentId"
                    element={<AssessmentDetailPage />}
                  />
                </Route>
              </Routes>
            </MemoryRouter>
          </OrganizationProvider>
        </AuthProvider>
      </QueryClientProvider>
    );
  }

  return { App, qc };
}

type AssessmentRow = {
  id: string;
  organization_id: string;
  assessment_model_id: string;
  standard_version_id: string;
  maturity_model_id: string | null;
  type: string;
  status: string;
  lead_membership_id: string;
  created_at: string;
  updated_at: string;
};

type Store = {
  roles: Roles;
  assessment: AssessmentRow;
  scopes: Array<{
    id: string;
    assessment_id: string;
    org_process_id: string | null;
    requirement_id: string | null;
    created_at: string;
  }>;
  team: Array<{
    id: string;
    assessment_id: string;
    membership_id: string;
    team_role: string | null;
    created_at: string;
  }>;
  createCalls: number;
  planCalls: number;
  planFailOnce?: { status: number; code: string; message: string; correlation_id: string };
  listByOrg: Record<string, AssessmentRow[]>;
};

function installApi(store: Store) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = urlOf(input);
      const method = (
        init?.method ||
        (input instanceof Request ? input.method : "GET")
      ).toUpperCase();
      const org = orgHeader(input, init);

      if (url.includes("/memberships")) {
        return json([
          {
            id: MEMBERSHIP,
            organization_id: ORG_A,
            organization_name: "Org A",
            roles: store.roles,
            status: "active",
          },
          {
            id: MEMBERSHIP_B,
            organization_id: ORG_B,
            organization_name: "Org B",
            roles: store.roles,
            status: "active",
          },
        ]);
      }

      if (url.endsWith("/api/v1/assessments") && method === "GET") {
        const key = org || ORG_A;
        const list =
          store.listByOrg[key] ??
          (store.assessment.organization_id === key ? [store.assessment] : []);
        return json(list);
      }

      if (url.endsWith("/api/v1/assessments") && method === "POST") {
        store.createCalls += 1;
        const body = await readJsonBody(input, init);
        expect(body).not.toHaveProperty("organization_id");
        const scopeIn = Array.isArray(body.scope) ? body.scope : [];
        store.scopes = scopeIn.map((s, i) => {
          const item = s as { requirement_id?: string; org_process_id?: string };
          return {
            id: `${SCOPE_ID.slice(0, -1)}${i}`,
            assessment_id: AID,
            org_process_id: item.org_process_id ?? null,
            requirement_id: item.requirement_id ?? null,
            created_at: "2026-01-01T00:00:00Z",
          };
        });
        store.assessment = {
          ...store.assessment,
          organization_id: org || ORG_A,
          status: "draft",
        };
        store.listByOrg[org || ORG_A] = [store.assessment];
        return json(store.assessment, 201);
      }

      if (url.includes(`/api/v1/assessments/${AID}/scopes`) && method === "GET") {
        return json(store.scopes);
      }

      if (url.includes(`/api/v1/assessments/${AID}/scopes`) && method === "POST") {
        if (store.assessment.status !== "draft") {
          return json(
            {
              code: "mutation_blocked",
              message: "Scope locked after plan",
              correlation_id: "corr-scope-409",
            },
            409,
          );
        }
        const body = (await readJsonBody(input, init)) as {
          requirement_id?: string;
          org_process_id?: string;
        };
        const row = {
          id: SCOPE_ID,
          assessment_id: AID,
          org_process_id: body.org_process_id ?? null,
          requirement_id: body.requirement_id ?? null,
          created_at: "2026-01-01T00:00:00Z",
        };
        store.scopes = [...store.scopes, row];
        return json(row, 201);
      }

      if (url.includes(`/api/v1/assessments/${AID}/team`) && method === "GET") {
        return json(store.team);
      }

      if (url.includes(`/api/v1/assessments/${AID}/team`) && method === "POST") {
        if (store.assessment.status !== "draft") {
          return json(
            {
              code: "mutation_blocked",
              message: "Team locked after plan",
              correlation_id: "corr-team-409",
            },
            409,
          );
        }
        const body = (await readJsonBody(input, init)) as {
          membership_id: string;
          team_role?: string;
        };
        const row = {
          id: "team-extra",
          assessment_id: AID,
          membership_id: body.membership_id,
          team_role: body.team_role ?? null,
          created_at: "2026-01-01T00:00:00Z",
        };
        store.team = [...store.team, row];
        return json(row, 201);
      }

      if (url.includes(`/transitions/plan`) && method === "POST") {
        store.planCalls += 1;
        if (store.planFailOnce) {
          const fail = store.planFailOnce;
          store.planFailOnce = undefined;
          return json(fail, fail.status);
        }
        if (store.scopes.length < 1) {
          return json(
            {
              code: "plan_guard_scope",
              message: "plan requires at least one scope item",
              correlation_id: "corr-422-scope",
            },
            422,
          );
        }
        if (store.team.length < 1 || !store.assessment.lead_membership_id) {
          return json(
            {
              code: "plan_guard_team",
              message: "plan requires minimum team",
              correlation_id: "corr-422-team",
            },
            422,
          );
        }
        store.assessment = { ...store.assessment, status: "planned" };
        store.listByOrg[store.assessment.organization_id] = [store.assessment];
        return json({
          assessment: store.assessment,
          from_status: "draft",
          to_status: "planned",
          event: "plan",
        });
      }

      if (url.includes(`/api/v1/assessments/${AID}`) && method === "GET") {
        if (org && org !== store.assessment.organization_id) {
          return json(
            { code: "not_found", message: "not found", correlation_id: "corr-404" },
            404,
          );
        }
        return json(store.assessment);
      }

      if (
        url.includes("/maturity-assessments") ||
        url.includes("/findings") ||
        url.includes("/interviews") ||
        url.includes("/questions") ||
        url.includes("/evidences")
      ) {
        return json([]);
      }

      return json({ code: "not_found", message: url, correlation_id: "" }, 404);
    }),
  );
}

function baseStore(roles: Roles = ["org_admin"]): Store {
  const assessment = {
    id: AID,
    organization_id: ORG_A,
    assessment_model_id: MODEL,
    standard_version_id: SV,
    maturity_model_id: null,
    type: "diagnosis",
    status: "draft",
    lead_membership_id: MEMBERSHIP,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  return {
    roles,
    assessment,
    scopes: [],
    team: [
      {
        id: "team-1",
        assessment_id: AID,
        membership_id: MEMBERSHIP,
        team_role: "lead",
        created_at: "2026-01-01T00:00:00Z",
      },
    ],
    createCalls: 0,
    planCalls: 0,
    listByOrg: { [ORG_A]: [assessment] },
  };
}

describe("assessment setup and planning UI", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_ENVIRONMENT", "local");
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    vi.stubEnv("VITE_API_BASE_URL", "http://localhost:8008");
    vi.stubEnv("VITE_DEFAULT_ASSESSMENT_MODEL_ID", MODEL);
    vi.stubEnv("VITE_DEFAULT_STANDARD_VERSION_ID", SV);
    vi.stubEnv("VITE_DEFAULT_REQUIREMENT_ID", "");
    resetConfigCache();
    resetQmindClient();
    resetTenantContext();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("creates draft and navigates to detail", async () => {
    const user = userEvent.setup();
    const store = baseStore();
    installApi(store);
    const { App } = harness("/assessments/new");
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Criar rascunho/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("radio", { name: "Requirement" }));
    await user.type(screen.getByPlaceholderText(/requirement_id/i), REQ);
    await user.click(screen.getByRole("button", { name: /Criar rascunho/i }));

    await waitFor(() => {
      expect(screen.getByTestId("assessment-status")).toHaveTextContent("draft");
      expect(screen.getByText(`requirement:${REQ}`)).toBeInTheDocument();
    });
    expect(store.createCalls).toBe(1);
  });

  it("allows scope/team edits in draft and blocks after plan", async () => {
    const user = userEvent.setup();
    const store = baseStore();
    store.scopes = [
      {
        id: SCOPE_ID,
        assessment_id: AID,
        org_process_id: null,
        requirement_id: REQ,
        created_at: "2026-01-01T00:00:00Z",
      },
    ];
    installApi(store);
    const { App } = harness(`/assessments/${AID}`);
    render(<App />);

    await waitFor(() => expect(screen.getByTestId("team-list")).toBeInTheDocument());

    await user.type(screen.getByLabelText("membership_id"), EXTRA_MEMBER);
    await user.click(screen.getByTestId("team-add"));
    await waitFor(() => {
      expect(screen.getByText(EXTRA_MEMBER)).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("plan-open-confirm"));
    await user.click(screen.getByTestId("plan-confirm-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("assessment-status")).toHaveTextContent("planned");
      expect(screen.getByTestId("plan-locked")).toBeInTheDocument();
    });
    expect(screen.queryByLabelText("Valor do escopo")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("membership_id")).not.toBeInTheDocument();
  });

  it("shows plan guards when scope/team incomplete", async () => {
    const store = baseStore();
    store.scopes = [];
    installApi(store);
    const { App } = harness(`/assessments/${AID}`);
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("plan-guard-scope")).toHaveTextContent(/faltando/i);
      expect(screen.getByTestId("plan-open-confirm")).toBeDisabled();
    });
  });

  it("reader sees detail without mutation controls", async () => {
    const store = baseStore(["reader"]);
    store.scopes = [
      {
        id: SCOPE_ID,
        assessment_id: AID,
        org_process_id: null,
        requirement_id: REQ,
        created_at: "2026-01-01T00:00:00Z",
      },
    ];
    installApi(store);
    const { App } = harness(`/assessments/${AID}`);
    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("reader-notice")).toBeInTheDocument();
      expect(screen.getByText(`requirement:${REQ}`)).toBeInTheDocument();
    });
    expect(screen.queryByTestId("plan-open-confirm")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Valor do escopo")).not.toBeInTheDocument();
    expect(screen.queryByTestId("new-assessment")).not.toBeInTheDocument();
  });

  it("displays 422 plan guard with correlation_id", async () => {
    const user = userEvent.setup();
    const store = baseStore();
    // Force UI ready then fail server-side once
    store.scopes = [
      {
        id: SCOPE_ID,
        assessment_id: AID,
        org_process_id: null,
        requirement_id: REQ,
        created_at: "2026-01-01T00:00:00Z",
      },
    ];
    store.planFailOnce = {
      status: 422,
      code: "plan_guard_scope",
      message: "plan requires at least one scope item",
      correlation_id: "corr-422-scope",
    };
    installApi(store);
    const { App } = harness(`/assessments/${AID}`);
    render(<App />);

    await waitFor(() => expect(screen.getByTestId("plan-open-confirm")).toBeEnabled());
    await user.click(screen.getByTestId("plan-open-confirm"));
    await user.click(screen.getByTestId("plan-confirm-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("api-error-code")).toHaveTextContent("plan_guard_scope");
      expect(screen.getByTestId("api-error-correlation")).toHaveTextContent(
        "corr-422-scope",
      );
    });
  });

  it("double click does not duplicate create or plan", async () => {
    const user = userEvent.setup();

    // create double-submit
    const createStore = baseStore();
    installApi(createStore);
    const { App: CreateApp } = harness("/assessments/new");
    const { unmount } = render(<CreateApp />);
    await waitFor(() => screen.getByRole("button", { name: /Criar rascunho/i }));
    const createBtn = screen.getByRole("button", { name: /Criar rascunho/i });
    await user.dblClick(createBtn);
    await waitFor(() => expect(createStore.createCalls).toBeGreaterThanOrEqual(1));
    expect(createStore.createCalls).toBe(1);
    unmount();

    // plan double-submit (fresh store with ready guards)
    vi.unstubAllGlobals();
    resetQmindClient();
    resetTenantContext();
    const planStore = baseStore();
    planStore.scopes = [
      {
        id: SCOPE_ID,
        assessment_id: AID,
        org_process_id: null,
        requirement_id: REQ,
        created_at: "2026-01-01T00:00:00Z",
      },
    ];
    installApi(planStore);
    const { App: DetailApp } = harness(`/assessments/${AID}`);
    render(<DetailApp />);
    await waitFor(() => expect(screen.getByTestId("plan-open-confirm")).toBeEnabled());
    await user.click(screen.getByTestId("plan-open-confirm"));
    const confirm = screen.getByTestId("plan-confirm-submit");
    await user.dblClick(confirm);
    await waitFor(() => expect(planStore.planCalls).toBeGreaterThanOrEqual(1));
    expect(planStore.planCalls).toBe(1);
  });

  it("tenant switch during edit ignores previous org responses", async () => {
    const user = userEvent.setup();
    const store = baseStore();
    store.scopes = [
      {
        id: SCOPE_ID,
        assessment_id: AID,
        org_process_id: null,
        requirement_id: REQ,
        created_at: "2026-01-01T00:00:00Z",
      },
    ];
    store.listByOrg[ORG_B] = [];
    installApi(store);
    const { App } = harness(`/assessments/${AID}`);
    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(`requirement:${REQ}`)).toBeInTheDocument();
    });

    await user.selectOptions(
      screen.getByLabelText("Selecionar organização"),
      ORG_B,
    );

    await waitFor(() => {
      // Detail for AID under org B → not found / error, not stale Org A content as success
      const status = screen.queryByTestId("assessment-status");
      if (status) {
        expect(status).not.toHaveTextContent("draft");
      } else {
        expect(screen.getByTestId("api-error")).toBeInTheDocument();
      }
    });
  });

  it("successful plan updates listing status", async () => {
    const user = userEvent.setup();
    const store = baseStore();
    store.scopes = [
      {
        id: SCOPE_ID,
        assessment_id: AID,
        org_process_id: null,
        requirement_id: REQ,
        created_at: "2026-01-01T00:00:00Z",
      },
    ];
    installApi(store);
    const { App } = harness(`/assessments/${AID}`);
    render(<App />);

    await waitFor(() => expect(screen.getByTestId("plan-open-confirm")).toBeEnabled());
    await user.click(screen.getByTestId("plan-open-confirm"));
    await user.click(screen.getByTestId("plan-confirm-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("assessment-status")).toHaveTextContent("planned");
    });

    await user.click(screen.getByTestId("nav-assessments"));
    await waitFor(() => {
      const list = screen.getByTestId("assessments-list");
      expect(within(list).getByText("planned")).toBeInTheDocument();
    });
  });
});
