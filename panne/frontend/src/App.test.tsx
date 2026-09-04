import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { AppRoutes } from "./App";
import { errorFromResponse } from "./api/errors";
import { cancelledSheetFixture, meFixture, ORG_A } from "./api/fixtures";
import { AuthProviderTree } from "./auth/AuthContext";
import { FakeAuthProvider } from "./auth/FakeAuthProvider";
import { isFakeBlockedInProduction } from "./config";
import { formatDecimal } from "./format";
import { AssistantProvider } from "./assistant/AssistantContext";
import { OrganizationProvider } from "./session/OrganizationContext";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("autenticação", () => {
  it("bloqueia o provedor falso em produção", () => {
    expect(isFakeBlockedInProduction(true, "fake")).toBe(true);
    expect(isFakeBlockedInProduction(false, "fake")).toBe(false);
    expect(() => new FakeAuthProvider()).not.toThrow();
  });

  it("faz login e logout sem gravar token no localStorage", async () => {
    const provider = new FakeAuthProvider();
    await provider.login();
    expect(provider.getAccessToken()).toBeTruthy();
    expect(localStorage.getItem("panne.token")).toBeNull();
    expect(Object.keys(localStorage).every((key) => !key.toLowerCase().includes("token"))).toBe(true);
    await provider.logout();
    expect(provider.getAccessToken()).toBeNull();
  });

  it("rehidrata a sessão fake a partir do sessionStorage após “refresh”", async () => {
    sessionStorage.setItem("panne.demoSubject", "demo-owner");
    const first = new FakeAuthProvider();
    await first.login();
    expect(first.getAccessToken()).toBe("panne-demo:demo-owner");
    expect(sessionStorage.getItem("panne.fakeSession")).toBe("1");
    expect(localStorage.getItem("panne.token")).toBeNull();

    const restored = new FakeAuthProvider();
    expect(restored.getSession()?.accessToken).toBe("panne-demo:demo-owner");
    expect(restored.getAccessToken()).toBe("panne-demo:demo-owner");

    await restored.logout();
    expect(sessionStorage.getItem("panne.fakeSession")).toBeNull();
    expect(sessionStorage.getItem("panne.demoSubject")).toBeNull();
    expect(new FakeAuthProvider().getSession()).toBeNull();
  });

  it("Sair limpa autenticação e não restaura após novo FakeAuthProvider", async () => {
    localStorage.setItem("panne.activeOrganization", ORG_A);
    sessionStorage.setItem("panne.demoSubject", "demo-owner");
    sessionStorage.setItem("panne.operationalContext." + ORG_A + ".anon", JSON.stringify({
      operational_date: "2026-08-24",
      establishment_id: "e1",
      establishment_name: "Central",
      shift: "manha",
      area: "padaria",
    }));
    const provider = new FakeAuthProvider();
    await provider.login();
    installApiMock();
    render(
      <AuthProviderTree provider={provider}>
        <OrganizationProvider>
          <MemoryRouter
            future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
            initialEntries={["/producao"]}
          >
            <AssistantProvider>
              <AppRoutes />
            </AssistantProvider>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProviderTree>,
    );
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Abrir menu do usuário" }));
    await user.click(screen.getByRole("menuitem", { name: "Sair" }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Entrar na Panne" })).toBeInTheDocument();
    });
    expect(sessionStorage.getItem("panne.fakeSession")).toBeNull();
    expect(sessionStorage.getItem("panne.demoSubject")).toBeNull();
    expect(localStorage.getItem("panne.activeOrganization")).toBeNull();
    expect(Object.keys(sessionStorage).filter((k) => k.startsWith("panne.operationalContext."))).toEqual([]);
    expect(new FakeAuthProvider().getSession()).toBeNull();
  });

  it("envia o token no /me depois de entrar", async () => {
    installApiMock();
    render(
      <AuthProviderTree>
        <OrganizationProvider>
          <MemoryRouter
            future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
            initialEntries={["/entrar"]}
          >
            <AssistantProvider>
              <AppRoutes />
            </AssistantProvider>
          </MemoryRouter>
        </OrganizationProvider>
      </AuthProviderTree>,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Entrar em desenvolvimento" }));
    await waitFor(() => {
      const calls = vi.mocked(fetch).mock.calls;
      const meCall = calls.find(([input]) => String(input).includes("/api/v1/me"));
      expect(meCall).toBeTruthy();
      const headers = (meCall?.[1] as RequestInit | undefined)?.headers;
      const authorization =
        headers instanceof Headers
          ? headers.get("Authorization")
          : (headers as Record<string, string> | undefined)?.Authorization;
      expect(authorization).toMatch(/^Bearer panne-fake-access-token$/);
    });
    expect(await screen.findByRole("heading", { name: "Fluxo produtivo" })).toBeInTheDocument();
  });

  it("R026-001: /organizacao fica fora de RequireOrganization e renderiza a seleção", async () => {
    localStorage.clear();
    sessionStorage.clear();
    const multiOrgNoSelection = {
      ...meFixture,
      selected_organization_id: null as string | null,
    };
    installApiMock({
      "/api/v1/me": () => json(multiOrgNoSelection),
    });
    await renderApp("/organizacao");
    expect(await screen.findByRole("heading", { name: "Escolha a organização" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Padaria Central" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Atelier Norte" })).toBeInTheDocument();

    // Com multi-org e sem ativa, /producao redireciona para a seleção (sem página vazia).
    const { view } = await renderApp("/producao");
    expect(await screen.findByRole("heading", { name: "Escolha a organização" })).toBeInTheDocument();
    view.unmount();

    await renderApp("/organizacao");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Padaria Central" }));
    expect(await screen.findByRole("heading", { name: "Fluxo produtivo" })).toBeInTheDocument();
  });

  it("R026-001: /organizacao sem sessão redireciona para /entrar", async () => {
    localStorage.clear();
    sessionStorage.clear();
    installApiMock();
    await renderApp("/organizacao", { signedIn: false });
    expect(await screen.findByRole("heading", { name: "Entrar na Panne" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Escolha a organização" })).not.toBeInTheDocument();
  });

  it("R026-001: /organizacao fica fora de RequireOrganization e renderiza a seleção", async () => {
    localStorage.clear();
    sessionStorage.clear();
    const multiOrgNoSelection = {
      ...meFixture,
      selected_organization_id: null as string | null,
    };
    installApiMock({
      "/api/v1/me": () => json(multiOrgNoSelection),
    });
    await renderApp("/organizacao");
    expect(await screen.findByRole("heading", { name: "Escolha a organização" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Padaria Central" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Atelier Norte" })).toBeInTheDocument();

    // Com multi-org e sem ativa, /producao redireciona para a seleção (sem página vazia).
    const { view } = await renderApp("/producao");
    expect(await screen.findByRole("heading", { name: "Escolha a organização" })).toBeInTheDocument();
    view.unmount();

    await renderApp("/organizacao");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Padaria Central" }));
    expect(await screen.findByRole("heading", { name: "Quadro de produção" })).toBeInTheDocument();
  });

  it("R026-001: /organizacao sem sessão redireciona para /entrar", async () => {
    localStorage.clear();
    sessionStorage.clear();
    installApiMock();
    await renderApp("/organizacao", { signedIn: false });
    expect(await screen.findByRole("heading", { name: "Entrar na Panne" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Escolha a organização" })).not.toBeInTheDocument();
  });

  it("descarta organização preferida inválida e recarrega o perfil", async () => {
    localStorage.setItem("panne.activeOrganization", "99999999-9999-9999-9999-999999999999");
    let meCalls = 0;
    installApiMock({
      "/api/v1/me": (_url, request) => {
        meCalls += 1;
        if (request.headers.get("X-Panne-Organization-Id") === "99999999-9999-9999-9999-999999999999") {
          return json({ code: "nao_autorizado", message: "Não autorizado." }, 403);
        }
        return json(meFixture);
      },
    });
    await renderApp("/producao");
    expect(await screen.findByRole("heading", { name: "Quadro de produção" })).toBeInTheDocument();
    expect(meCalls).toBeGreaterThanOrEqual(2);
    expect(localStorage.getItem("panne.activeOrganization")).toBe(ORG_A);
  });

  it("simula callback do provedor falso", async () => {
    const provider = new FakeAuthProvider();
    const session = await provider.handleCallback();
    expect(session.accessToken).toContain("fake");
  });
});

describe("interface", () => {
  it("mostra shell horizontal e quadro em sucesso", async () => {
    installApiMock();
    const { view } = await renderApp("/producao");
    expect(await screen.findByRole("heading", { name: "Quadro de produção" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Principal" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Produção" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Estoque" })).not.toBeInTheDocument();
    expect(await screen.findByText("Pão tradicional")).toBeInTheDocument();
    expect(screen.getByText("Atrasada")).toBeInTheDocument();
    expect(screen.getByText(/Livre/)).toBeInTheDocument();
    expect(screen.getByRole("main").textContent?.toLowerCase()).not.toContain("preço");
    const results = await axe(view.container);
    expect(results.violations.filter((item) => item.impact === "critical")).toEqual([]);
  });

  it("mostra carregamento, vazio e erro do quadro", async () => {
    installApiMock({
      "/production/board": () => json({ data: [] }),
    });
    await renderApp("/producao");
    expect(await screen.findByText(/Não há ordens/)).toBeInTheDocument();

    installApiMock({
      "/production/board": () => json({ code: "indisponivel", message: "API fora" }, 503),
    });
    await renderApp("/producao?q=x");
    expect(await screen.findByRole("alert")).toHaveTextContent("API fora");
  });

  it("persiste filtros na URL e troca organização limpando o cache", async () => {
    const fetchMock = installApiMock();
    await renderApp("/producao?q=OP-2026");
    expect(await screen.findByDisplayValue("OP-2026")).toBeInTheDocument();
    const user = userEvent.setup();
    await user.selectOptions(
      screen.getByLabelText("Organização ativa"),
      meFixture.associations[1].organization_id,
    );
    await waitFor(() => {
      expect(localStorage.getItem("panne.activeOrganization")).toBe(
        meFixture.associations[1].organization_id,
      );
    });
    expect(fetchMock.orgA).toBeTruthy();
  });

  it("separa planejado e realizado no detalhe", async () => {
    installApiMock();
    await renderApp("/ordens/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    expect(await screen.findByText("Materiais planejados")).toBeInTheDocument();
    expect(screen.getByText("Materiais realizados")).toBeInTheDocument();
    expect(screen.getByText(/informado/)).toBeInTheDocument();
    expect(screen.getByText(/canônico/)).toBeInTheDocument();
  });

  it("nega rastreabilidade sem permissão", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          associations: meFixture.associations.map((item) => ({
            ...item,
            permissions: item.permissions.filter((code) => code !== "production.traceability.read"),
          })),
          permissions: meFixture.permissions.filter((code) => code !== "production.traceability.read"),
        }),
    });
    await renderApp("/rastreabilidade/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa");
    expect(await screen.findByRole("alert")).toHaveTextContent("não tem permissão");
    expect(screen.queryByText("Formulação e escala")).not.toBeInTheDocument();
  });

  it("renderiza o payload da ficha e o aviso de substituição", async () => {
    installApiMock({
      "/sheets/cccccccc-cccc-cccc-cccc-cccccccccccc": () => json(cancelledSheetFixture),
    });
    await renderApp("/ordens/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/fichas/cccccccc-cccc-cccc-cccc-cccccccccccc");
    expect(await screen.findByText(/Ficha de produção/)).toBeInTheDocument();
    expect(screen.getByText(/Farinha de trigo/)).toBeInTheDocument();
    expect(screen.getByText(/Ordem cancelada/)).toBeInTheDocument();
    expect(screen.getByText(/substitui uma emissão anterior/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Imprimir" }).closest(".no-print")).toBeTruthy();
  });

  it("escapa textos da API e formata decimais sem float", () => {
    expect(formatDecimal("7000.500000")).toBe("7.000,5");
    expect(formatDecimal("not-a-number")).toBe("not-a-number");
    document.body.innerHTML = "";
    const root = document.createElement("div");
    root.textContent = "<script>alert(1)</script>";
    expect(root.innerHTML).toBe("&lt;script&gt;alert(1)&lt;/script&gt;");
  });
});

describe("erros HTTP", () => {
  it.each([
    [401, "nao_autenticado"],
    [403, "nao_autorizado"],
    [409, "conflito"],
    [422, "regra_dominio"],
    [503, "indisponivel"],
  ] as const)("mapeia %s", (status, code) => {
    const error = errorFromResponse(status, { message: "aviso" });
    expect(error.code).toBe(code);
    expect(error.message).toBe("aviso");
  });
});
