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

describe("field execution UI", () => {
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

  it("confirms start planned → in_progress and shows field workspace", async () => {
    const user = userEvent.setup();
    let status = "planned";
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = urlOf(input);
      const method = init?.method ?? (input instanceof Request ? input.method : "GET");

      if (url.includes("/memberships") || url.endsWith("/api/v1/me/memberships")) {
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
      if (url.includes(`/assessments/${AID}/scopes`)) return json([]);
      if (url.includes(`/assessments/${AID}/team`)) return json([]);
      if (url.includes(`/assessments/${AID}/questions`)) return json([]);
      if (url.includes(`/assessments/${AID}/interviews`)) return json([]);
      if (url.includes(`/assessments/${AID}/evidences`)) return json([]);
      if (
        url.includes("/maturity-assessments") ||
        url.includes("/findings") ||
        url.includes("/action-plans") ||
        url.includes("/reports")
      ) {
        return json([]);
      }
      if (url.includes(`/assessments/${AID}/transitions/start`) && method === "POST") {
        status = "in_progress";
        return json({
          assessment: {
            id: AID,
            organization_id: ORG,
            assessment_model_id: "11111111-1111-4111-8111-111111111111",
            standard_version_id: "22222222-2222-4222-8222-222222222222",
            type: "diagnosis",
            status,
            lead_membership_id: MEMBERSHIP,
            started_at: new Date().toISOString(),
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
          from_status: "planned",
          to_status: "in_progress",
          event: "start",
        });
      }
      if (url.includes(`/assessments/${AID}`) && method === "GET") {
        return json({
          id: AID,
          organization_id: ORG,
          assessment_model_id: "11111111-1111-4111-8111-111111111111",
          standard_version_id: "22222222-2222-4222-8222-222222222222",
          type: "diagnosis",
          status,
          lead_membership_id: MEMBERSHIP,
          started_at: status === "in_progress" ? new Date().toISOString() : null,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      }
      return json({ code: "not_found", message: url, correlation_id: "corr-1" }, 404);
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
    await waitFor(() =>
      expect(screen.getByTestId("assessment-status")).toHaveTextContent(/planejada/i),
    );
    await user.click(screen.getByTestId("start-open-confirm"));
    expect(screen.getByTestId("start-confirm")).toBeInTheDocument();
    await user.click(screen.getByTestId("start-confirm-submit"));
    await waitFor(() =>
      expect(screen.getByTestId("assessment-status")).toHaveTextContent(/em andamento/i),
    );
    expect(screen.getByTestId("field-execution")).toBeInTheDocument();
  });

  it("blocks start UI for reader on planned assessment", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = urlOf(input);
      if (url.includes("/memberships") || url.includes("/me/memberships")) {
        return json([
          {
            id: MEMBERSHIP,
            organization_id: ORG,
            organization_name: "Org A",
            roles: ["reader"],
            status: "active",
          },
        ]);
      }
      if (url.includes(`/assessments/${AID}/scopes`)) return json([]);
      if (url.includes(`/assessments/${AID}/team`)) return json([]);
      if (url.includes(`/assessments/${AID}`)) {
        return json({
          id: AID,
          organization_id: ORG,
          assessment_model_id: "11111111-1111-4111-8111-111111111111",
          standard_version_id: "22222222-2222-4222-8222-222222222222",
          type: "diagnosis",
          status: "planned",
          lead_membership_id: MEMBERSHIP,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
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
    await waitFor(() => expect(screen.getByTestId("start-locked")).toBeInTheDocument());
    expect(screen.queryByTestId("start-open-confirm")).toBeNull();
  });
});
