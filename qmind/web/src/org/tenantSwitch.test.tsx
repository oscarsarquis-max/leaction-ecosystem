import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider, useOrganization } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { AssessmentsPage } from "@/pages/AssessmentsPage";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import {
  assertNoSensitiveLocalPersistence,
  readPreferredOrganizationId,
} from "@/auth/storage";
import { queryKeys } from "@/api/queryKeys";

const ORG_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const ORG_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";

type MembershipJson = {
  id: string;
  organization_id: string;
  organization_name: string;
  roles: string[];
  status: string;
};

const memberships: MembershipJson[] = [
  {
    id: "m-a",
    organization_id: ORG_A,
    organization_name: "Org A",
    roles: ["admin"],
    status: "active",
  },
  {
    id: "m-b",
    organization_id: ORG_B,
    organization_name: "Org B",
    roles: ["viewer"],
    status: "active",
  },
];

function assessmentsFor(orgId: string) {
  return [
    {
      id: `assessment-${orgId.slice(0, 4)}`,
      organization_id: orgId,
      status: "draft",
      type: "diagnosis",
      assessment_model_id: "model-1",
      lead_membership_id: null,
      maturity_model_id: null,
      standard_version_id: "sv-1",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    },
  ];
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

function requestSignal(input: RequestInfo | URL, init?: RequestInit): AbortSignal | undefined {
  if (input instanceof Request) return input.signal ?? undefined;
  return init?.signal ?? undefined;
}

function installFetchMock(opts?: {
  assessmentDelayMs?: number;
  onAssessments?: (orgHeader: string | null) => void;
}) {
  const delay = opts?.assessmentDelayMs ?? 0;

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = requestUrl(input);
    const headers = requestHeaders(input, init);
    const signal = requestSignal(input, init);
    const orgHeader = headers.get("X-Organization-Id");

    if (signal?.aborted) {
      throw new DOMException("Aborted", "AbortError");
    }

    if (url.includes("/memberships")) {
      return jsonResponse(memberships);
    }

    if (url.includes("/api/v1/assessments")) {
      opts?.onAssessments?.(orgHeader);
      if (delay > 0) {
        await new Promise<void>((resolve, reject) => {
          const t = setTimeout(resolve, delay);
          signal?.addEventListener(
            "abort",
            () => {
              clearTimeout(t);
              reject(new DOMException("Aborted", "AbortError"));
            },
            { once: true },
          );
        });
      }
      return jsonResponse(assessmentsFor(orgHeader || ORG_A));
    }

    return jsonResponse({ code: "not_found", message: "no", correlation_id: "" }, 404);
  });

  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock };
}

function Harness({ children }: { children?: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <OrganizationProvider>
          <MemoryRouter initialEntries={["/assessments"]}>
            <Routes>
              <Route element={<AppShell />}>
                <Route path="assessments" element={children ?? <AssessmentsPage />} />
              </Route>
            </Routes>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

function OrgProbe() {
  const org = useOrganization();
  return (
    <div>
      <span data-testid="current-org">{org.currentOrganizationId}</span>
      <span data-testid="gen">{org.requestGeneration}</span>
      <button
        type="button"
        onClick={() => void org.switchOrganization(ORG_B)}
      >
        Switch B
      </button>
      <button
        type="button"
        onClick={() => void org.switchOrganization(ORG_A)}
      >
        Switch A
      </button>
      <AssessmentsPage />
    </div>
  );
}

describe("tenant switch gate", () => {
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

  it("A → B → A keeps assessments scoped and preferred org in session only", async () => {
    const user = userEvent.setup();
    const seenOrgs: Array<string | null> = [];
    installFetchMock({
      onAssessments: (org) => seenOrgs.push(org),
    });

    render(
      <Harness>
        <OrgProbe />
      </Harness>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_A);
    });
    await waitFor(() => {
      expect(screen.getByText(`assessment-${ORG_A.slice(0, 4)}`)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Switch B" }));
    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_B);
    });
    await waitFor(() => {
      expect(screen.getByText(`assessment-${ORG_B.slice(0, 4)}`)).toBeInTheDocument();
    });
    expect(screen.queryByText(`assessment-${ORG_A.slice(0, 4)}`)).not.toBeInTheDocument();
    expect(readPreferredOrganizationId()).toBe(ORG_B);

    await user.click(screen.getByRole("button", { name: "Switch A" }));
    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_A);
    });
    await waitFor(() => {
      expect(screen.getByText(`assessment-${ORG_A.slice(0, 4)}`)).toBeInTheDocument();
    });
    expect(readPreferredOrganizationId()).toBe(ORG_A);
    assertNoSensitiveLocalPersistence();
    expect(seenOrgs).toContain(ORG_A);
    expect(seenOrgs).toContain(ORG_B);
  });

  it("switch during slow request aborts and ignores stale org A payload", async () => {
    const user = userEvent.setup();
    let resolveSlow: (() => void) | undefined;
    const slowGate = new Promise<void>((resolve) => {
      resolveSlow = () => resolve();
    });

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = requestUrl(input);
      const headers = requestHeaders(input, init);
      const signal = requestSignal(input, init);
      const orgHeader = headers.get("X-Organization-Id");

      if (url.includes("memberships")) {
        return jsonResponse(memberships);
      }
      if (url.includes("/api/v1/assessments")) {
        if (orgHeader === ORG_A) {
          await Promise.race([
            slowGate,
            new Promise<void>((_r, reject) => {
              signal?.addEventListener(
                "abort",
                () => reject(new DOMException("Aborted", "AbortError")),
                { once: true },
              );
            }),
          ]);
          return jsonResponse(assessmentsFor(ORG_A));
        }
        return jsonResponse(assessmentsFor(ORG_B));
      }
      return jsonResponse({}, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <Harness>
        <OrgProbe />
      </Harness>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_A);
    });

    // Start switch to B while A's assessments request is still pending
    await user.click(screen.getByRole("button", { name: "Switch B" }));

    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_B);
    });

    // Late completion of A must not win
    resolveSlow?.();

    await waitFor(() => {
      expect(screen.getByText(`assessment-${ORG_B.slice(0, 4)}`)).toBeInTheDocument();
    });
    expect(screen.queryByText(`assessment-${ORG_A.slice(0, 4)}`)).not.toBeInTheDocument();
  });

  it("logout during request clears preference and does not keep tenant data", async () => {
    const user = userEvent.setup();
    installFetchMock({ assessmentDelayMs: 80 });

    render(
      <Harness>
        <OrgProbe />
      </Harness>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("current-org").textContent).toBe(ORG_A);
    });

    await user.click(screen.getByRole("button", { name: "Sair" }));

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Entrar" })).toBeInTheDocument();
    });
    expect(readPreferredOrganizationId()).toBeNull();
    assertNoSensitiveLocalPersistence();
  });

  it("cache keys include organization_id", () => {
    expect(queryKeys.assessments(ORG_A)).toEqual(["org", ORG_A, "assessments"]);
    expect(queryKeys.assessments(ORG_A)).not.toEqual(queryKeys.assessments(ORG_B));
  });
});
