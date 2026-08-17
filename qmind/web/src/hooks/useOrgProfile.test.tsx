import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider, useOrganization } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { useOrgProfile } from "@/hooks/useOrgProfile";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { enterApp } from "@/test/enterApp";

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

function profileFor(orgId: string) {
  return {
    organization_id: orgId,
    trade_name: orgId === ORG_A ? "Profile A" : "Profile B",
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

function ProfileProbe() {
  const org = useOrganization();
  const profile = useOrgProfile();
  return (
    <div>
      <span data-testid="current-org">{org.currentOrganizationId}</span>
      <span data-testid="profile-trade">{profile.data?.trade_name ?? ""}</span>
      <span data-testid="profile-org">{profile.data?.organization_id ?? ""}</span>
      <button type="button" onClick={() => void org.switchOrganization(ORG_B)}>
        Switch B
      </button>
      <button type="button" onClick={() => void org.switchOrganization(ORG_A)}>
        Switch A
      </button>
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
                <Route path="/" element={children ?? <ProfileProbe />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

describe("useOrgProfile tenant switch", () => {
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

  it("A → B → A never leaves another org profile visible", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const headers = requestHeaders(input, init);
      const orgHeader = headers.get("X-Organization-Id");

      if (url.includes("/memberships")) {
        return jsonResponse(memberships);
      }
      if (url.includes("/organizations/current/profile")) {
        if (orgHeader !== ORG_A && orgHeader !== ORG_B) {
          return jsonResponse({ code: "forbidden_organization" }, 403);
        }
        return jsonResponse(profileFor(orgHeader!));
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
      if (url.includes("/assessments")) {
        return jsonResponse([]);
      }
      return jsonResponse({ code: "not_found", message: url }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <Harness>
        <ProfileProbe />
      </Harness>,
    );

    await enterApp(user);

    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_A);
      expect(screen.getByTestId("profile-trade").textContent).toBe("Profile A");
      expect(screen.getByTestId("profile-org").textContent).toBe(ORG_A);
    });

    await user.click(screen.getByRole("button", { name: "Switch B" }));
    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_B);
      expect(screen.getByTestId("profile-trade").textContent).toBe("Profile B");
      expect(screen.getByTestId("profile-org").textContent).toBe(ORG_B);
    });

    await user.click(screen.getByRole("button", { name: "Switch A" }));
    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_A);
      expect(screen.getByTestId("profile-trade").textContent).toBe("Profile A");
      expect(screen.getByTestId("profile-org").textContent).toBe(ORG_A);
    });
  });
});
