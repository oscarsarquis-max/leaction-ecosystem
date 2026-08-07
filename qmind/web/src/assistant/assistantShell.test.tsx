import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { AppShell } from "@/components/AppShell";
import { AccessGate } from "@/components/AccessGate";
import { useRegisterAssistantContext } from "@/assistant/AssistantProvider";
import type { AssistantContext } from "@/assistant/types";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { resetTenantContext } from "@/api/tenantContext";
import { enterApp } from "@/test/enterApp";
import { useOrganization } from "@/org/OrganizationProvider";
import { useMemo } from "react";

const ORG = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
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

function StubHome() {
  const org = useOrganization();
  const ctx = useMemo((): AssistantContext | null => {
    if (!org.currentOrganizationId) return null;
    return {
      organization_id: org.currentOrganizationId,
      organization_name: org.currentOrganization?.organizationName || "Org",
      assessment_id: null,
      assessment_label: null,
      route: "/assessments",
      page: "org_home",
      phase_label: null,
      assessment_status: null,
      user_roles: org.currentOrganization?.roles ?? [],
      can_mutate: true,
      next_action: {
        label: "Criar a primeira avaliação",
        hint: "Comece pela preparação.",
        href: "/assessments/new",
        mutates: true,
      },
      pendencies: [
        {
          key: "no-assessment",
          problem: "Nenhuma avaliação",
          impact: "Sem percurso",
          actionLabel: "Criar",
          href: "/assessments/new",
        },
      ],
      blockers: [],
      progress_summary: "Nenhuma avaliação",
      allowed_links: ["/assessments", "/assessments/new"],
      stage_title: "Home da organização",
      stage_explanation: "Escolha ou crie uma avaliação.",
    };
  }, [org.currentOrganizationId, org.currentOrganization]);
  useRegisterAssistantContext(ctx);
  return <div data-testid="stub-home">Home stub</div>;
}

describe("Assistente QMind no AppShell", () => {
  beforeEach(() => {
    resetQmindClient();
    resetTenantContext();
    resetConfigCache();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("não aparece no AccessGate", () => {
    render(<AccessGate status="anonymous" onLogin={() => undefined} />);
    expect(screen.queryByTestId("qmind-assistant-open")).toBeNull();
  });

  it("aparece após login e orienta home sem avaliação", async () => {
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
              organization_name: "Org Assistente",
              roles: ["org_admin"],
              status: "active",
            },
          ]);
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
            <MemoryRouter initialEntries={["/assessments"]}>
              <Routes>
                <Route element={<AppShell />}>
                  <Route path="assessments" element={<StubHome />} />
                </Route>
              </Routes>
            </MemoryRouter>
          </OrganizationProvider>
        </AuthProvider>
      </QueryClientProvider>,
    );

    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("qmind-assistant-open")).toBeInTheDocument(),
    );

    await user.click(screen.getByTestId("qmind-assistant-open"));
    expect(screen.getByTestId("qmind-assistant-panel")).toBeInTheDocument();
    expect(
      screen.getAllByText(/Estou aqui para orientar você/i).length,
    ).toBeGreaterThan(0);

    await user.click(screen.getByTestId("qmind-assistant-action-what_now"));
    await waitFor(() =>
      expect(screen.getByTestId("qmind-assistant-body")).toHaveTextContent(
        /Criar a primeira avaliação|avaliação/i,
      ),
    );
  });
});
