import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { AssessmentDetailPage } from "@/pages/AssessmentDetailPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { resetTenantContext } from "@/api/tenantContext";
import { enterApp } from "@/test/enterApp";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const AID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const MEMBERSHIP = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function urlOf(input: RequestInfo | URL) {
  if (typeof input === "string") return input;
  if (input instanceof URL) return input.toString();
  return input.url;
}

describe("field execution entry (handoff via audit-plan)", () => {
  beforeEach(() => {
    resetQmindClient();
    resetTenantContext();
    resetConfigCache();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("planned assessment directs start to Plano da Auditoria (not legacy start CTA)", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = urlOf(input);
        if (url.includes("/memberships") || url.includes("/me/memberships")) {
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
        if (url.includes(`/assessments/${AID}/audit-plan`)) {
          return json({
            plan_status: "ready",
            readiness: { ready: true, percent: 100, items: [], blockers: [] },
          });
        }
        if (url.includes(`/assessments/${AID}`)) {
          return json({
            id: AID,
            organization_id: ORG,
            assessment_model_id: "11111111-1111-4111-8111-111111111111",
            standard_version_id: "22222222-2222-4222-8222-222222222222",
            type: "diagnosis",
            status: "planned",
            lead_membership_id: MEMBERSHIP,
            started_at: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          });
        }
        return json({ code: "not_found", message: url, correlation_id: "corr-1" }, 404);
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
    await waitFor(() =>
      expect(screen.getByTestId("assessment-status")).toHaveTextContent(/planejada/i),
    );
    expect(screen.getByTestId("open-audit-plan")).toHaveTextContent(
      /handoff|Plano da Auditoria/i,
    );
    expect(screen.queryByTestId("start-open-confirm")).toBeNull();
  });

  it("reader on planned assessment has no mutation start CTA", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
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
    await waitFor(() => expect(screen.getByTestId("open-audit-plan")).toBeInTheDocument());
    expect(screen.queryByTestId("start-open-confirm")).toBeNull();
    expect(screen.queryByTestId("start-locked")).toBeNull();
  });
});
