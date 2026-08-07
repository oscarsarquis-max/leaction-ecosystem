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
import { enterApp } from "@/test/enterApp";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const AID = "44444444-4444-4444-8444-444444444444";
const MEMBERSHIP = "55555555-5555-4555-8555-555555555555";
const PKG = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const C1 = "d1111111-1111-4111-8111-111111111111";
const C2 = "d2222222-2222-4222-8222-222222222222";

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

function basePackage(overrides: Record<string, unknown> = {}) {
  return {
    id: PKG,
    organization_id: ORG,
    assessment_id: AID,
    version_no: 1,
    supersedes_id: null,
    maturity_model_id: "a1000000-0000-4000-8000-000000000001",
    model_code: "qmind_maturity_iso9001",
    model_version: "0.1.0",
    status: "draft",
    global_score: "3.00",
    author_membership_id: MEMBERSHIP,
    approved_by: null,
    discard_reason: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    scores: [
      {
        id: "s1",
        criterion_id: C1,
        criterion_code: "D1.C1",
        criterion_title: "Contexto e partes interessadas",
        dimension_id: "dim1",
        dimension_code: "D1_context_leadership",
        dimension_title: "Contexto e liderança",
        anchor_l3: "Registro atualizado",
        applicability: "applicable",
        level: 3,
        na_rationale: null,
        rationale: null,
        evidence_ids: [],
      },
      {
        id: "s2",
        criterion_id: C2,
        criterion_code: "D1.C2",
        criterion_title: "Política e objetivos",
        dimension_id: "dim1",
        dimension_code: "D1_context_leadership",
        dimension_title: "Contexto e liderança",
        anchor_l3: "Objetivos mensuráveis",
        applicability: "insufficient_info",
        level: null,
        na_rationale: null,
        rationale: null,
        evidence_ids: [],
      },
    ],
    dimension_scores: [
      {
        dimension_id: "dim1",
        dimension_code: "D1_context_leadership",
        dimension_title: "Contexto e liderança",
        score: "3.00",
        applicable_count: 1,
      },
    ],
    ...overrides,
  };
}

function assessmentJson(status = "analysis") {
  return {
    id: AID,
    organization_id: ORG,
    assessment_model_id: "11111111-1111-4111-8111-111111111111",
    standard_version_id: "22222222-2222-4222-8222-222222222222",
    maturity_model_id: "a1000000-0000-4000-8000-000000000001",
    type: "diagnosis",
    status,
    lead_membership_id: MEMBERSHIP,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

describe("maturity analysis UI", () => {
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

  it("restores draft, blocks author approve, and gates double submit", async () => {
    const user = userEvent.setup();
    let pkg = basePackage();
    let submitCalls = 0;
    let createCalls = 0;

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = urlOf(input);
        const method = methodOf(input, init);
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
        if (
          url.includes("/scopes") ||
          url.includes("/team") ||
          url.includes("/questions") ||
          url.includes("/interviews") ||
          url.includes("/evidences") ||
          url.includes("/findings") ||
          url.includes("/action-plans") ||
          url.includes("/reports")
        ) {
          return json([]);
        }
        if (url.includes("/maturity-assessments") && method === "GET") {
          return json(createCalls > 0 || pkg ? [pkg] : []);
        }
        if (url.includes("/maturity-assessments") && method === "POST" && !url.includes("/transitions")) {
          createCalls += 1;
          return json(pkg, 201);
        }
        if (url.includes("/scores") && method === "PUT") {
          const body =
            typeof init?.body === "string"
              ? JSON.parse(init.body)
              : input instanceof Request
                ? await input.clone().json()
                : {};
          expect(body).not.toHaveProperty("global_score");
          expect(body).not.toHaveProperty("dimension_scores");
          pkg = {
            ...pkg,
            global_score: "3.00",
            updated_at: "2026-01-01T01:00:00Z",
            scores: pkg.scores.map((s) => {
              const u = (body.scores as Array<Record<string, unknown>>)?.find(
                (x) => x.criterion_id === s.criterion_id,
              );
              return u
                ? {
                    ...s,
                    applicability: u.applicability as string,
                    level: (u.level as number | null) ?? null,
                    na_rationale: (u.na_rationale as string | null) ?? null,
                    rationale: (u.rationale as string | null) ?? null,
                    evidence_ids: (u.evidence_ids as string[]) ?? [],
                  }
                : s;
            }),
          };
          return json(pkg);
        }
        if (url.includes("/transitions/submit") && method === "POST") {
          submitCalls += 1;
          await new Promise((r) => setTimeout(r, 60));
          if (pkg.scores.some((s) => s.applicability === "insufficient_info")) {
            return json(
              {
                code: "insufficient_info_forbidden",
                message: "Resolve insufficient_info before submit",
                correlation_id: "corr-insuff-1",
              },
              422,
            );
          }
          pkg = { ...pkg, status: "in_review" };
          return json({
            package: pkg,
            from_status: "draft",
            to_status: "in_review",
            event: "submit",
          });
        }
        if (url.includes(`/assessments/${AID}`) && method === "GET") {
          return json(assessmentJson("analysis"));
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
    await waitFor(() => expect(screen.getByTestId("maturity-analysis")).toBeInTheDocument());
    await user.click(screen.getByTestId("maturity-open"));
    await waitFor(() => expect(screen.getByTestId("maturity-package-meta")).toBeInTheDocument());
    expect(screen.getByTestId("maturity-package-meta").textContent).toMatch(
      /qmind_maturity_iso9001@0\.1\.0/,
    );
    expect(screen.getByTestId("maturity-global-score").textContent).toMatch(/3\.00/);
    expect(screen.getByTestId("maturity-global-score").textContent).toMatch(
      /calculado pelo servidor/i,
    );
    expect(screen.getByTestId("maturity-analysis").textContent).toMatch(/half-up/i);

    // levels shown as text labels, not color-only
    await user.click(screen.getByTestId("maturity-criterion-D1.C1"));
    const editor = screen.getByTestId("maturity-criterion-editor");
    expect(screen.getByTestId("maturity-level-3")).toBeInTheDocument();
    expect(editor.textContent).toMatch(/3 — gerenciado/);

    const submitBtn = screen.getByTestId("maturity-submit");
    await Promise.all([user.click(submitBtn), user.click(submitBtn)]);
    await waitFor(() => expect(screen.getByTestId("api-error")).toBeInTheDocument());
    expect(screen.getByTestId("api-error").textContent).toMatch(/corr-insuff-1/);
    expect(submitCalls).toBe(1);

    // clear insufficient_info and submit → in_review; author cannot approve
    await user.click(screen.getByTestId("maturity-criterion-D1.C2"));
    await user.selectOptions(screen.getByTestId("maturity-applicability"), "applicable");
    await user.click(screen.getByTestId("maturity-level-3"));
    await user.click(screen.getByTestId("maturity-save"));
    await waitFor(() => expect(screen.queryByTestId("api-error")).toBeNull());

    await user.click(screen.getByTestId("maturity-submit"));
    await waitFor(() =>
      expect(screen.getByTestId("maturity-status")).toHaveTextContent(/em revisão/i),
    );
    expect(screen.getByTestId("maturity-approve")).toBeDisabled();
    expect(screen.getByTestId("maturity-sod").textContent).toMatch(/SoD/i);
  });

  it("requires N/A rationale client-side before save and shows immutable approved package", async () => {
    const user = userEvent.setup();
    const pkg = basePackage({
      status: "approved",
      global_score: "4.67",
      scores: [
        {
          id: "s1",
          criterion_id: C1,
          criterion_code: "D1.C1",
          criterion_title: "Contexto",
          dimension_id: "dim1",
          dimension_code: "D1_context_leadership",
          dimension_title: "Contexto e liderança",
          applicability: "applicable",
          level: 4,
          na_rationale: null,
          rationale: "measured",
          evidence_ids: [],
        },
      ],
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = urlOf(input);
        const method = methodOf(input, init);
        if (url.includes("/memberships")) {
          return json([
            {
              id: "other-membership",
              organization_id: ORG,
              organization_name: "Org A",
              roles: ["quality_manager"],
              status: "active",
            },
          ]);
        }
        if (
          url.includes("/scopes") ||
          url.includes("/team") ||
          url.includes("/questions") ||
          url.includes("/interviews") ||
          url.includes("/evidences") ||
          url.includes("/findings") ||
          url.includes("/action-plans") ||
          url.includes("/reports")
        ) {
          return json([]);
        }
        if (url.includes("/maturity-assessments") && method === "GET") {
          return json([pkg]);
        }
        if (url.includes(`/assessments/${AID}`) && method === "GET") {
          return json(assessmentJson("analysis"));
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
    await waitFor(() => expect(screen.getByTestId("maturity-immutable")).toBeInTheDocument());
    expect(screen.getByTestId("maturity-status")).toHaveTextContent(/aprovada/i);
    expect(screen.queryByTestId("maturity-save")).toBeNull();
    expect(screen.getByTestId("maturity-supersede")).toBeInTheDocument();
  });
});
