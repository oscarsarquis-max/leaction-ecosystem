import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { meFixture, ORG_A } from "./api/fixtures";
import {
  brandHomeForRoles,
  landingPathForRoles,
} from "./navigation/landing";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("CURSOR-028-R2 destinos pós-login", () => {
  it("mapeia papéis gerenciais e operacionais", () => {
    expect(landingPathForRoles(["owner"])).toBe("/inicio");
    expect(landingPathForRoles(["production_manager"])).toBe("/inicio");
    expect(landingPathForRoles(["baker_operator"])).toBe("/producao");
    expect(landingPathForRoles(["technical_responsible"])).toBe("/receitas");
    expect(landingPathForRoles(["regulatory_reviewer"])).toBe("/conformidade");
    expect(landingPathForRoles(["commercial"])).toBe("/gestao/compras/necessidades");
    expect(landingPathForRoles(["viewer"])).toBe("/gestao/custos");
    expect(brandHomeForRoles(["owner"])).toBe("/inicio");
    expect(brandHomeForRoles(["baker_operator"])).toBe("/fluxo");
  });

  it("login do gestor cai no painel e a marca aponta para /inicio", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const login = await renderApp("/entrar", { signedIn: false });
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /Entrar em desenvolvimento|Entrar na demonstração/ }));
    expect(await screen.findByRole("heading", { name: "Hoje na Panne" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Panne" })).toHaveAttribute("href", "/inicio");
    login.view.unmount();
  });

  it("padeiro não é forçado ao painel", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          roles: ["baker_operator"],
          associations: meFixture.associations.map((row) => ({ ...row, roles: ["baker_operator"] })),
        }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/");
    expect(await screen.findByRole("heading", { name: "Quadro de produção" })).toBeInTheDocument();
  });
});
