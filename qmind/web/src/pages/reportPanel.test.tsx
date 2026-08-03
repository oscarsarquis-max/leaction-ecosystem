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
const OTHER = "66666666-6666-4666-8666-666666666666";
const RID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const RID2 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";

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

function assessmentJson(status = "report") {
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

function baseReport(overrides: Record<string, unknown> = {}) {
  return {
    id: RID,
    organization_id: ORG,
    assessment_id: AID,
    version_no: 1,
    status: "in_review",
    structured_content: {
      findings: [{ id: "f1", title: "NC", status: "approved" }],
      maturity: { id: "m1", global_score: "3.00" },
      action_plan: { id: "p1", status: "active", items: [] },
      immutable: true,
    },
    maturity_assessment_id: "m1",
    export_storage_key: null,
    supersedes_report_id: null,
    discard_reason: null,
    published_at: null,
    published_by: null,
    author_membership_id: MEMBERSHIP,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function renderPage() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return render(
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
}

function stubEmpty(url: string) {
  return (
    url.includes("/scopes") ||
    url.includes("/team") ||
    url.includes("/questions") ||
    url.includes("/interviews") ||
    url.includes("/evidences") ||
    url.includes("/findings") ||
    url.includes("/maturity-assessments") ||
    url.includes("/action-plans")
  );
}

describe("report panel UI", () => {
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

  it("blocks author publish (SoD), shows snapshot, gates double publish", async () => {
    const user = userEvent.setup();
    let report = baseReport();
    let publishCalls = 0;

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
        if (stubEmpty(url)) return json([]);
        if (url.includes("/reports") && method === "GET" && !url.includes("/transitions")) {
          return json([report]);
        }
        if (url.includes(`/reports/${RID}/transitions/publish`) && method === "POST") {
          publishCalls += 1;
          return json(
            {
              code: "sod_violation",
              message: "Publisher must differ from report author",
              correlation_id: "corr-sod-rep",
            },
            403,
          );
        }
        if (url.includes(`/assessments/${AID}`) && method === "GET") {
          return json(assessmentJson("report"));
        }
        return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
      }),
    );

    renderPage();
    await waitFor(() => expect(screen.getByTestId("report-panel")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByTestId("report-meta")).toBeInTheDocument());
    expect(screen.getByTestId("report-version")).toHaveTextContent("v1");
    expect(screen.getByTestId("report-snapshot-summary").textContent).toMatch(/1 finding/);
    expect(screen.getByTestId("report-snapshot-summary").textContent).toMatch(/imutável/);
    expect(screen.getByTestId("report-sod-banner")).toBeInTheDocument();

    const publish = screen.getByTestId("report-publish");
    expect(publish).toBeDisabled();
    await user.click(publish);
    expect(publishCalls).toBe(0);
  });

  it("non-author publishes once; export queues job; supersede shows new version", async () => {
    const user = userEvent.setup();
    let reports = [
      baseReport({
        author_membership_id: OTHER,
        status: "in_review",
      }),
    ];
    let publishCalls = 0;
    let exportCalls = 0;
    let assessmentStatus = "report";

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
              roles: ["quality_manager"],
              status: "active",
            },
          ]);
        }
        if (stubEmpty(url)) return json([]);
        if (
          url.includes("/api/v1/reports") &&
          method === "GET" &&
          !url.includes(RID) &&
          !url.includes(RID2)
        ) {
          return json(reports);
        }
        if (url.includes(`/reports/${RID}/transitions/publish`) && method === "POST") {
          publishCalls += 1;
          await new Promise((r) => setTimeout(r, 40));
          reports = [
            {
              ...reports[0]!,
              status: "published",
              published_at: "2026-01-02T00:00:00Z",
              published_by: MEMBERSHIP,
            },
          ];
          return json({
            report: reports[0],
            from_status: "in_review",
            to_status: "published",
            event: "publish",
          });
        }
        if (url.includes(`/reports/${RID}/export-pdf`) && method === "POST") {
          exportCalls += 1;
          return json(
            {
              id: "jjjjjjjj-jjjj-4jjj-8jjj-jjjjjjjjjjjj",
              organization_id: ORG,
              job_type: "report_pdf_export",
              status: "queued",
              idempotency_key: "k1",
              input_ref: { report_id: RID },
              created_at: "2026-01-02T00:00:00Z",
            },
            202,
          );
        }
        if (url.endsWith("/api/v1/reports") && method === "POST") {
          const v2 = baseReport({
            id: RID2,
            version_no: 2,
            status: "draft",
            supersedes_report_id: RID,
            author_membership_id: MEMBERSHIP,
            structured_content: {
              findings: [{ id: "f1", title: "NC", status: "approved" }],
              maturity: null,
              action_plan: { id: "p1" },
            },
          });
          reports = [
            { ...reports[0]!, status: "published" },
            v2,
          ];
          return json(v2, 201);
        }
        if (url.includes(`/assessments/${AID}`) && method === "GET") {
          return json(assessmentJson(assessmentStatus));
        }
        return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
      }),
    );

    renderPage();
    await waitFor(() => expect(screen.getByTestId("report-publish")).toBeInTheDocument());
    expect(screen.queryByTestId("report-sod-banner")).toBeNull();

    const publish = screen.getByTestId("report-publish");
    await Promise.all([user.click(publish), user.click(publish)]);
    await waitFor(() =>
      expect(screen.getByTestId("report-status")).toHaveTextContent("publicado"),
    );
    expect(publishCalls).toBe(1);

    await user.click(screen.getByTestId("report-export-pdf"));
    await waitFor(() => expect(screen.getByTestId("report-export-job")).toBeInTheDocument());
    expect(screen.getByTestId("report-export-status")).toHaveTextContent("queued");
    expect(exportCalls).toBe(1);

    await user.click(screen.getByTestId("report-create"));
    await waitFor(() => expect(screen.getByTestId(`report-select-${RID2}`)).toBeInTheDocument());
    await user.click(screen.getByTestId(`report-select-${RID2}`));
    expect(screen.getByTestId("report-version")).toHaveTextContent("v2");
    expect(screen.getByTestId("report-supersedes").textContent).toMatch(new RegExp(RID));
  });

  it("begin_report from actions; close then reopen with reason", async () => {
    const user = userEvent.setup();
    let assessmentStatus = "actions";
    let beginCalls = 0;
    let closeCalls = 0;
    let reopenCalls = 0;
    let report = baseReport({ status: "published", author_membership_id: OTHER });

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
        if (stubEmpty(url)) return json([]);
        if (url.includes("/transitions/begin_report") && method === "POST") {
          beginCalls += 1;
          assessmentStatus = "report";
          return json({
            assessment: assessmentJson("report"),
            from_status: "actions",
            to_status: "report",
            event: "begin_report",
          });
        }
        if (url.includes("/reports") && method === "GET") {
          return json(assessmentStatus === "actions" ? [] : [report]);
        }
        if (url.includes("/transitions/close") && method === "POST") {
          closeCalls += 1;
          assessmentStatus = "closed";
          return json({
            assessment: assessmentJson("closed"),
            from_status: "report",
            to_status: "closed",
            event: "close",
          });
        }
        if (url.includes("/transitions/reopen") && method === "POST") {
          reopenCalls += 1;
          assessmentStatus = "report";
          return json({
            assessment: assessmentJson("report"),
            from_status: "closed",
            to_status: "report",
            event: "reopen",
          });
        }
        if (url.includes(`/assessments/${AID}`) && method === "GET") {
          return json(assessmentJson(assessmentStatus));
        }
        return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
      }),
    );

    renderPage();
    await waitFor(() => expect(screen.getByTestId("report-begin")).toBeInTheDocument());
    await user.click(screen.getByTestId("report-begin"));
    await waitFor(() => expect(beginCalls).toBe(1));
    await waitFor(() => expect(screen.getByTestId("assessment-close")).toBeInTheDocument());

    await user.click(screen.getByTestId("assessment-close"));
    await waitFor(() => expect(closeCalls).toBe(1));
    await waitFor(() => expect(screen.getByTestId("assessment-reopen")).toBeInTheDocument());

    await user.type(screen.getByTestId("assessment-reopen-reason"), "corrigir evidência");
    await user.click(screen.getByTestId("assessment-reopen"));
    await waitFor(() => expect(reopenCalls).toBe(1));
    await waitFor(() =>
      expect(screen.getByTestId("assessment-status")).toHaveTextContent("report"),
    );
  });
});
