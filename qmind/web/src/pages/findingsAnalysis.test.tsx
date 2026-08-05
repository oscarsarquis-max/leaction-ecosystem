import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { AssessmentDetailPage } from "@/pages/AssessmentDetailPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { resetTenantContext } from "@/api/tenantContext";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const AID = "44444444-4444-4444-8444-444444444444";
const MEMBERSHIP = "55555555-5555-4555-8555-555555555555";
const REQ = "33333333-3333-4333-8333-333333333333";
const EID = "99999999-9999-4999-8999-999999999999";
const FID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee";

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

function methodOf(input: RequestInfo | URL, init?: RequestInit) {
  return (init?.method || (input instanceof Request ? input.method : "GET")).toUpperCase();
}

async function enterApp(user: ReturnType<typeof userEvent.setup>) {
  await waitFor(() => expect(screen.getByTestId("login-cta")).toBeInTheDocument());
  await user.click(screen.getByTestId("login-cta"));
}

describe("findings analysis UI", () => {
  beforeEach(() => {
    resetConfigCache();
    resetQmindClient();
    resetTenantContext();
    vi.stubEnv("VITE_ENVIRONMENT", "local");
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    vi.stubEnv("VITE_API_BASE_URL", "");
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("creates draft, shows SoD, and ignores double-submit", async () => {
    const user = userEvent.setup();
    let findings: Array<Record<string, unknown>> = [];
    let submitCalls = 0;
    let createCalls = 0;

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = urlOf(input);
      const method = methodOf(input, init);

      if (url.includes("/organizations/current/members")) {
        return json([
          {
            membership_id: MEMBERSHIP,
            email: "lead@example.com",
            display_name: "Líder",
            roles: ["org_admin"],
            status: "active",
          },
        ]);
      }
      if (url.includes("/memberships")) {
        return json([
          {
            id: MEMBERSHIP,
            organization_id: ORG,
            organization_name: "Org A",
            roles: ["org_admin"],
            status: "active",
          },
        ]);
      }
      if (url.includes(`/assessments/${AID}/scopes`)) {
        return json([
          {
            id: "scope-1",
            assessment_id: AID,
            requirement_id: REQ,
            org_process_id: null,
            created_at: "2026-01-01T00:00:00Z",
            label: "Requisito 4 — Context of the organization (ref)",
          },
        ]);
      }
      if (url.includes(`/assessments/${AID}/team`)) return json([]);
      if (url.includes(`/assessments/${AID}/questions`)) return json([]);
      if (url.includes(`/assessments/${AID}/interviews`)) return json([]);
      if (url.includes("/maturity-assessments") || url.includes("/action-plans") || url.includes("/reports")) {
        return json([]);
      }
      if (url.includes(`/assessments/${AID}/evidences`)) {
        return json([
          {
            id: EID,
            organization_id: ORG,
            assessment_id: AID,
            status: "approved",
            classification: "confidential",
            content_type: "application/pdf",
            byte_size: 10,
            content_hash: "sha256:x",
            storage_key: "k",
            version_no: 1,
            legal_hold: false,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          },
        ]);
      }
      if (url.includes("/api/v1/findings") && method === "GET" && !url.includes(FID)) {
        return json(findings);
      }
      if (url.endsWith("/api/v1/findings") && method === "POST") {
        createCalls += 1;
        const body = init?.body
          ? JSON.parse(String(init.body))
          : input instanceof Request
            ? await input.clone().json()
            : {};
        const row = {
          id: FID,
          organization_id: ORG,
          assessment_id: AID,
          finding_type: body.finding_type,
          severity: null,
          status: "draft",
          title: body.title,
          body: body.body,
          insufficient_evidence: false,
          insufficient_evidence_rationale: null,
          author_membership_id: MEMBERSHIP,
          requirement_ids: body.requirement_ids ?? [],
          evidence_ids: body.evidence_ids ?? [],
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        };
        findings = [row];
        return json(row, 201);
      }
      if (url.includes(`/findings/${FID}/transitions/submit`) && method === "POST") {
        submitCalls += 1;
        await new Promise((r) => setTimeout(r, 80));
        findings = findings.map((f) => ({ ...f, status: "in_review" }));
        return json({
          finding: findings[0],
          from_status: "draft",
          to_status: "in_review",
          event: "submit",
        });
      }

      if (url.includes(`/findings/${FID}/transitions/approve`) && method === "POST") {
        return json(
          {
            code: "sod_violation",
            message: "Approver must differ from author",
            correlation_id: "corr-sod-1",
          },
          403,
        );
      }
      if (url.includes(`/assessments/${AID}`) && method === "GET") {
        return json({
          id: AID,
          organization_id: ORG,
          assessment_model_id: "11111111-1111-4111-8111-111111111111",
          standard_version_id: "22222222-2222-4222-8222-222222222222",
          maturity_model_id: null,
          type: "diagnosis",
          status: "in_progress",
          lead_membership_id: MEMBERSHIP,
          started_at: "2026-01-01T00:00:00Z",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        });
      }
      return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 0 } },
    });

    render(
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <OrganizationProvider>
            <MemoryRouter initialEntries={[`/assessments/${AID}`]}>
              <Routes>
                <Route element={<AppShell />}>
                  <Route path="assessments/:assessmentId" element={<AssessmentDetailPage />} />
                </Route>
              </Routes>
            </MemoryRouter>
          </OrganizationProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await enterApp(user);
    await waitFor(() => expect(screen.getByTestId("findings-analysis")).toBeInTheDocument());

    await user.selectOptions(screen.getByTestId("finding-type"), "conformity");
    await user.type(screen.getByTestId("finding-title"), "Doc OK");
    await user.type(screen.getByTestId("finding-body"), "Process documented");
    await user.click(screen.getByTestId(`finding-evidence-${EID}`));
    expect(screen.getByTestId("finding-insuff-forbidden")).toBeInTheDocument();

    await user.click(screen.getByTestId("finding-save"));
    await waitFor(() => expect(createCalls).toBe(1));

    await waitFor(() => expect(screen.getByTestId(`finding-select-${FID}`)).toBeInTheDocument());
    await user.click(screen.getByTestId(`finding-select-${FID}`));
    await waitFor(() => expect(screen.getByTestId("finding-sod-banner")).toBeInTheDocument());

    const submitBtn = screen.getByTestId("finding-submit");
    // Overlapping clicks while first submit is in flight (busyRef gate).
    await Promise.all([user.click(submitBtn), user.click(submitBtn)]);
    await waitFor(() => expect(submitCalls).toBe(1));

    await waitFor(() => expect(screen.getByTestId("finding-approve")).toBeDisabled());
    expect(screen.getByTestId("finding-sod-banner").textContent).toMatch(/SoD/i);
  });

  /**
   * Conflict/stale transition contract (409/422):
   * 1) UI shows ApiErrorBanner with correlation_id (finding-transition-error)
   * 2) hook invalidates org-scoped findings query
   * 3) list resource is refetched (GET /findings increases after submit)
   * Do not assert only on banner timing — gate on submit POST + refetch counters.
   */
  it("surfaces correlation_id on transition conflict and reloads list", async () => {
    const user = userEvent.setup();
    let listCalls = 0;
    let submitCalls = 0;
    const finding = {
      id: FID,
      organization_id: ORG,
      assessment_id: AID,
      finding_type: "observation",
      status: "draft",
      title: "Obs",
      body: "body",
      insufficient_evidence: true,
      insufficient_evidence_rationale: "gap",
      author_membership_id: MEMBERSHIP,
      requirement_ids: [REQ],
      evidence_ids: [],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = urlOf(input);
        const method = methodOf(input, init);
        if (url.includes("/organizations/current/members")) {
          return json([
            {
              membership_id: MEMBERSHIP,
              email: "auditor@example.com",
              display_name: "Auditor",
              roles: ["consultant_auditor"],
              status: "active",
            },
          ]);
        }
        if (url.includes("/memberships")) {
          return json([
            {
              id: MEMBERSHIP,
              organization_id: ORG,
              organization_name: "Org A",
              roles: ["consultant_auditor"],
              status: "active",
            },
          ]);
        }
        if (url.includes("/scopes")) {
          return json([
            {
              id: "s1",
              assessment_id: AID,
              requirement_id: REQ,
              org_process_id: null,
              created_at: "2026-01-01T00:00:00Z",
              label: "Requisito 4 — Context of the organization (ref)",
            },
          ]);
        }
        if (
          url.includes("/team") ||
          url.includes("/questions") ||
          url.includes("/interviews") ||
          url.includes("/maturity-assessments") ||
          url.includes("/action-plans") || url.includes("/reports")
        ) {
          return json([]);
        }
        if (url.includes("/evidences")) return json([]);
        if (url.includes("/api/v1/findings") && method === "GET") {
          listCalls += 1;
          return json([finding]);
        }
        if (
          url.includes(`/findings/${FID}/transitions/submit`) &&
          method === "POST"
        ) {
          submitCalls += 1;
          return json(
            {
              code: "evidence_base_required",
              message: "observation requires evidence or insufficient rationale",
              correlation_id: "corr-conflict-9",
            },
            422,
          );
        }
        if (url.includes(`/assessments/${AID}`) && method === "GET") {
          return json({
            id: AID,
            organization_id: ORG,
            assessment_model_id: "11111111-1111-4111-8111-111111111111",
            standard_version_id: "22222222-2222-4222-8222-222222222222",
            maturity_model_id: null,
            type: "diagnosis",
            status: "analysis",
            lead_membership_id: MEMBERSHIP,
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          });
        }
        return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
      }),
    );

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false, staleTime: 0 } },
    });

    render(
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <OrganizationProvider>
            <MemoryRouter initialEntries={[`/assessments/${AID}`]}>
              <Routes>
                <Route element={<AppShell />}>
                  <Route path="assessments/:assessmentId" element={<AssessmentDetailPage />} />
                </Route>
              </Routes>
            </MemoryRouter>
          </OrganizationProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await enterApp(user);
    await waitFor(() => expect(screen.getByTestId(`finding-select-${FID}`)).toBeInTheDocument());
    await user.click(screen.getByTestId(`finding-select-${FID}`));
    const submitBtn = await screen.findByTestId("finding-submit");
    const listCallsBeforeSubmit = listCalls;

    await user.click(submitBtn);

    await waitFor(() => expect(submitCalls).toBe(1));
    const transitionError = await screen.findByTestId("finding-transition-error");
    expect(transitionError).toBeInTheDocument();
    expect(screen.getByTestId("api-error-correlation")).toHaveTextContent("corr-conflict-9");
    expect(screen.getByTestId("api-error-code")).toHaveTextContent("evidence_base_required");

    await waitFor(() => expect(listCalls).toBeGreaterThan(listCallsBeforeSubmit));
  });
});
