import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/auth/AuthProvider";
import { OrganizationProvider } from "@/org/OrganizationProvider";
import { Hotpage } from "@/public/Hotpage";
import { LoginPage } from "@/pages/LoginPage";
import { AppShell } from "@/components/AppShell";
import { resetQmindClient } from "@/api/qmindApi";
import { resetConfigCache } from "@/config/env";
import { resetTenantContext } from "@/api/tenantContext";
import { enterApp } from "@/test/enterApp";

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

function renderPublic(initial = "/") {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 0 } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <OrganizationProvider>
          <MemoryRouter initialEntries={[initial]}>
            <Routes>
              <Route path="/" element={<Hotpage />} />
              <Route path="login" element={<LoginPage />} />
              <Route element={<AppShell />}>
                <Route
                  path="assessments"
                  element={<div data-testid="assessments-home">Home</div>}
                />
                <Route
                  path="guided-tour"
                  element={<div data-testid="guided-tour-stub">Tour</div>}
                />
              </Route>
            </Routes>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("Hotpage pública e login", () => {
  beforeEach(() => {
    resetQmindClient();
    resetTenantContext();
    resetConfigCache();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("abre / sem autenticação e sem chamar memberships", async () => {
    const fetchMock = vi.fn(async () =>
      json({ code: "unexpected", message: "should not fetch", correlation_id: "x" }, 500),
    );
    vi.stubGlobal("fetch", fetchMock);

    renderPublic("/");

    expect(screen.getByTestId("qmind-hotpage")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: /Prepare a organização antes que a auditoria comece/i,
      }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("qmind-assistant-open")).toBeNull();
    expect(screen.queryByTestId("access-gate")).toBeNull();

    await waitFor(() => {
      const tenantCalls = fetchMock.mock.calls.filter((c) =>
        urlOf(c[0] as RequestInfo).includes("/memberships"),
      );
      expect(tenantCalls).toHaveLength(0);
    });
  });

  it("seletor de diferenciais atualiza o painel", async () => {
    const user = userEvent.setup();
    renderPublic("/");

    await user.click(screen.getByRole("tab", { name: /Agenda unificada/i }));
    expect(
      screen.getByRole("heading", { name: /Agenda unificada/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/compromissos visíveis/i),
    ).toBeInTheDocument();
  });

  it("CTA Entrar leva ao login; após auth abre o app", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = urlOf(input);
        if (url.includes("/memberships") || url.includes("/me/memberships")) {
          return json([
            {
              id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
              organization_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
              organization_name: "Org Demo",
              roles: ["org_admin"],
              status: "active",
            },
          ]);
        }
        return json({ code: "not_found", message: url, correlation_id: "c" }, 404);
      }),
    );

    renderPublic("/");
    await user.click(screen.getAllByRole("button", { name: /Entrar no QMind/i })[0]!);
    expect(screen.getByTestId("login-page")).toBeInTheDocument();
    expect(screen.getByTestId("access-gate")).toBeInTheDocument();

    await enterApp(user);
    await waitFor(() =>
      expect(screen.getByTestId("assessments-home")).toBeInTheDocument(),
    );
  });

  it("guided-tour exige autenticação", async () => {
    renderPublic("/guided-tour");
    expect(screen.getByTestId("access-gate")).toBeInTheDocument();
    expect(screen.queryByTestId("guided-tour-stub")).toBeNull();
  });
});
