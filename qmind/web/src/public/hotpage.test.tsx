import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
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
import { ILLUSTRATIVE_EXAMPLE_BADGE, JOURNEY_CHAPTER_IDS } from "@/journeyV2";
import { readReturnUrl } from "@/lib/returnUrl";

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

const PRIVATE_PATHS = [
  "/organizations/current",
  "/cockpit",
  "/improvement-cases",
  "/assessments",
  "/execution",
  "/memberships",
  "execution-intelligence",
  "problem-analysis",
];

describe("Hotpage pública V2", () => {
  beforeEach(() => {
    resetQmindClient();
    resetTenantContext();
    resetConfigCache();
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renderiza hero e Jornada V2 sem chamar endpoints privados", async () => {
    const fetchMock = vi.fn(async () =>
      json({ code: "unexpected", message: "should not fetch", correlation_id: "x" }, 500),
    );
    vi.stubGlobal("fetch", fetchMock);

    renderPublic("/");

    expect(screen.getByTestId("qmind-hotpage")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: /Da compreensão à decisão/i,
      }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("journey-panel")).toBeInTheDocument();
    for (const id of JOURNEY_CHAPTER_IDS) {
      expect(screen.getByTestId(`journey-tab-${id}`)).toBeInTheDocument();
    }

    await waitFor(() => {
      const privateCalls = fetchMock.mock.calls.filter((c) => {
        const url = urlOf(c[0] as RequestInfo);
        return PRIVATE_PATHS.some((p) => url.includes(p));
      });
      expect(privateCalls).toHaveLength(0);
    });
  });

  it("navega capítulos por clique e teclado", async () => {
    const user = userEvent.setup();
    renderPublic("/");

    await user.click(screen.getByTestId("journey-tab-control"));
    expect(screen.getByRole("heading", { name: /Controlar prioridades/i })).toBeInTheDocument();

    const tab = screen.getByTestId("journey-tab-control");
    tab.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("heading", { name: /Decidir e aprender/i })).toBeInTheDocument();
  });

  it("marca exemplo ilustrativo e não dispara rede ao selecionar", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async () => json({}, 200));
    vi.stubGlobal("fetch", fetchMock);

    renderPublic("/");
    const example = screen.getByTestId("illustrative-example");
    expect(within(example.closest("section")!).getAllByText(ILLUSTRATIVE_EXAMPLE_BADGE).length).toBeGreaterThan(0);

    const before = fetchMock.mock.calls.length;
    await user.click(screen.getByRole("tab", { name: /Impedimento visível/i }));
    expect(screen.getByText(/bloqueio de capacidade/i)).toBeInTheDocument();
    expect(fetchMock.mock.calls.length).toBe(before);
  });

  it("usuário anônimo preserva return URL local ao iniciar apresentação", async () => {
    const user = userEvent.setup();
    renderPublic("/");
    await user.click(screen.getByTestId("hotpage-start-tour"));
    expect(screen.getByTestId("login-page")).toBeInTheDocument();
    expect(readReturnUrl()).toBe("/guided-tour");
  });

  it("CTA autenticado abre app e tour sem login", async () => {
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

  it("tablist de capacidades atualiza painel", async () => {
    const user = userEvent.setup();
    renderPublic("/");
    const caps = screen.getByRole("tablist", { name: /Capacidades QMind/i });
    await user.click(within(caps).getByRole("tab", { name: /^Cockpit$/i }));
    expect(screen.getByText(/Prioridade do Cockpit não é decisão automática/i)).toBeInTheDocument();
  });
});
