import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { GuidedTourPage } from "@/pages/GuidedTourPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { resetTenantContext } from "@/api/tenantContext";
import { enterApp } from "@/test/enterApp";
import { JOURNEY_CHAPTER_IDS } from "@/journeyV2";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const MEMBER = "mmmmmmmm-mmmm-4mmm-8mmm-mmmmmmmmmmmm";

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

function renderTour(initial = "/guided-tour?chapter=assess") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <OrganizationProvider>
          <MemoryRouter initialEntries={[initial]}>
            <Routes>
              <Route element={<AppShell />}>
                <Route path="guided-tour" element={<GuidedTourPage />} />
                <Route
                  path="cockpit"
                  element={<div data-testid="cockpit-stub">Cockpit</div>}
                />
                <Route
                  path="assessments"
                  element={<div data-testid="assessments-home">Home</div>}
                />
              </Route>
            </Routes>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("GuidedTourPage V2", () => {
  beforeEach(() => {
    resetQmindClient();
    resetTenantContext();
    resetConfigCache();
    sessionStorage.clear();
    vi.stubEnv("VITE_AUTH_MODE", "dev");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = urlOf(input);
        const method = (init?.method ?? "GET").toUpperCase();
        if (["POST", "PATCH", "PUT", "DELETE"].includes(method)) {
          throw new Error(`mutation not allowed in tour: ${method} ${url}`);
        }
        if (url.includes("/memberships")) {
          return json([
            {
              id: MEMBER,
              organization_id: ORG,
              organization_name: "Org Demo",
              roles: ["org_admin"],
              status: "active",
            },
          ]);
        }
        if (url.includes("/iso-intelligence/cockpit/cases")) {
          return json({
            as_of: "2026-08-26T12:00:00Z",
            items: [],
            limit: 25,
            next_cursor: null,
            coverage: {
              analyzed_count: 0,
              included_count: 0,
              excluded_count: 0,
              complete: true,
            },
          });
        }
        if (url.includes("/iso-intelligence/cockpit/summary")) {
          return json({
            as_of: "2026-08-26T12:00:00Z",
            scope: { organization_id: ORG },
            case_totals: { total: 0, active: 0, reviewing: 0, closed: 0, ready_for_review: 0, unit: "cases" },
            execution: {
              active_actions: 0,
              completed_actions: 0,
              overdue_actions: 0,
              blocked_cases: 0,
              active_impediments: 0,
              open_dependencies: 0,
              overdue_dependencies: 0,
              actions_without_recent_check_in: 0,
            },
            evidence: {
              claims_execution_actions: 0,
              with_approved_evidence: 0,
              without_approved_evidence: 0,
            },
            measurement: {
              by_measurement_posture: [],
              by_target_posture: [],
              by_substantiation: [],
              overdue_indicators: 0,
            },
            intelligence_coverage: {
              current: 0,
              stale: 0,
              never_analyzed: 0,
              unit: "cases",
            },
            priority_distribution: [],
            recent_activity: [],
            coverage: { analyzed_count: 0, included_count: 0, excluded_count: 0, complete: true },
          });
        }
        if (url.includes("/assessments")) return json([]);
        if (url.includes("/improvement-cases")) return json([]);
        return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lista capítulos canônicos e unavailable sem avaliação", async () => {
    const user = userEvent.setup();
    renderTour("/guided-tour?chapter=assess");
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("guided-tour-page")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("guided-tour-chapters").querySelectorAll("li"),
    ).toHaveLength(JOURNEY_CHAPTER_IDS.length);

    await waitFor(() =>
      expect(
        screen.getByTestId("guided-tour-status-unavailable"),
      ).toBeInTheDocument(),
    );
    expect(
      screen.getByText(/Não há avaliação demonstrável/i),
    ).toBeInTheDocument();
  });

  it("abre Cockpit e retorna ao capítulo via banner", async () => {
    const user = userEvent.setup();
    renderTour("/guided-tour?chapter=control");
    await enterApp(user);

    await waitFor(() =>
      expect(screen.getByTestId("guided-tour-status-ready")).toBeInTheDocument(),
    );
    await user.click(screen.getByTestId("guided-tour-open-product"));
    await waitFor(() =>
      expect(screen.getByTestId("cockpit-stub")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("guided-tour-return-banner")).toBeInTheDocument();
    expect(screen.getByText(/Controlar/i)).toBeInTheDocument();
    await user.click(
      screen.getByRole("link", { name: /Voltar à apresentação guiada/i }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("guided-tour-page")).toBeInTheDocument(),
    );
  });

  it("capítulo inválido na URL cai no início", async () => {
    const user = userEvent.setup();
    renderTour("/guided-tour?chapter=javascript:alert(1)");
    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("guided-tour-page")).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("heading", { name: /Compreender a organização/i }),
    ).toBeInTheDocument();
  });
});
