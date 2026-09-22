import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { meFixture, ORG_A, ORG_B } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";
import { matchFlowStep } from "./fluxo/steps";
import { preferredStepForRole, resolveFlowRole } from "./fluxo/profileFocus";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

describe("CURSOR-028-B fluxo produtivo", () => {
  it("mapeia rotas existentes para etapas sem inventar URLs", () => {
    expect(matchFlowStep("/gestao/compras/recebimentos")).toBe(1);
    expect(matchFlowStep("/componentes/ingredientes")).toBe(2);
    expect(matchFlowStep("/receitas")).toBe(4);
    expect(matchFlowStep("/ordens")).toBe(5);
    expect(matchFlowStep("/producao")).toBe(5);
    expect(matchFlowStep("/producao/ordens/aaa/executar")).toBe(6);
    expect(matchFlowStep("/conformidade")).toBe(7);
    expect(matchFlowStep("/gestao/custos")).toBe(8);
    expect(matchFlowStep("/produtos")).toBe(3);
  });

  it("preferência de etapa por perfil", () => {
    expect(preferredStepForRole(resolveFlowRole(["baker_operator"]))).toBe(6);
    expect(preferredStepForRole(resolveFlowRole(["owner"]))).toBe(1);
    expect(preferredStepForRole(resolveFlowRole(["regulatory_reviewer"]))).toBe(7);
  });

  it("redirect inicial / e login do gestor vão para o painel", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const { view } = await renderApp("/");
    expect(await screen.findByRole("heading", { name: "Hoje na Panne" })).toBeInTheDocument();
    view.unmount();

    const login = await renderApp("/entrar", { signedIn: false });
    const user = userEvent.setup();
    const enter = screen.getByRole("button", {
      name: /Entrar em desenvolvimento|Entrar na demonstração/,
    });
    await user.click(enter);
    expect(await screen.findByRole("heading", { name: "Hoje na Panne" })).toBeInTheDocument();
    login.view.unmount();
  });

  it("Quadro permanece acessível em /producao", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/producao");
    expect(await screen.findByRole("heading", { name: "Quadro de produção" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Fluxo produtivo" }).length).toBeGreaterThan(0);
  });

  it("abre a etapa Produtos com ação real e segue para Receitas", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/fluxo?etapa=3");
    expect(await screen.findByRole("heading", { name: /Etapa 3 · Produtos/ })).toBeInTheDocument();
    expect(screen.queryByText(/Estrutura em preparação/i)).not.toBeInTheDocument();
    const panel = screen.getByRole("article");
    expect(within(panel).getByRole("link", { name: "Abrir produtos" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Próxima etapa/i }));
    expect(await screen.findByRole("heading", { name: /Etapa 4 · Receitas/ })).toBeInTheDocument();
  });

  it("trilha Anterior / Próxima / Voltar ao fluxo nas rotas existentes", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/receitas");
    expect(await screen.findByRole("heading", { name: "Minhas receitas" })).toBeInTheDocument();
    const trail = screen.getByRole("navigation", { name: "Trilha do fluxo produtivo" });
    expect(within(trail).getByText(/Etapa 4 de \d+/)).toBeInTheDocument();
    expect(within(trail).getByRole("link", { name: "Voltar ao fluxo" })).toHaveAttribute(
      "href",
      expect.stringContaining("/fluxo"),
    );
    expect(within(trail).getByRole("link", { name: "Anterior" })).toBeInTheDocument();
    expect(within(trail).getByRole("link", { name: "Próxima etapa" })).toBeInTheDocument();
  });

  it("oculta custos sem permissão e mantém as demais etapas", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          associations: meFixture.associations.map((row) =>
            row.organization_id === ORG_A
              ? {
                  ...row,
                  permissions: row.permissions.filter(
                    (code) =>
                      !code.startsWith("costing.")
                      && !code.startsWith("pricing.")
                      && code !== "reporting.costing.read"
                      && code !== "reporting.pricing.read",
                  ),
                }
              : row,
          ),
          permissions: meFixture.permissions.filter(
            (code) =>
              !code.startsWith("costing.")
              && !code.startsWith("pricing.")
              && code !== "reporting.costing.read"
              && code !== "reporting.pricing.read",
          ),
        }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/fluxo");
    expect(await screen.findByRole("heading", { name: "Fluxo produtivo" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Custos e preços/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Receitas/i })).toBeInTheDocument();
    expect(screen.getAllByText(/Etapa \d+ de 7/).length).toBeGreaterThanOrEqual(1);
    const rail = screen.getByRole("navigation", { name: "Etapas do fluxo produtivo" });
    expect(within(rail).getAllByRole("button")).toHaveLength(7);
  });

  it("navegação por teclado na trilha de etapas", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/fluxo");
    expect(await screen.findByRole("heading", { name: "Fluxo produtivo" })).toBeInTheDocument();
    const recipes = screen.getByRole("button", { name: /Receitas/i });
    recipes.focus();
    expect(recipes).toHaveFocus();
    await user.keyboard("{Enter}");
    expect(await screen.findByRole("heading", { name: /Etapa 4 · Receitas/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Receitas/i })).toHaveAttribute("aria-current", "step");
  });

  it("refresh/rota direta /fluxo e troca de organização", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/fluxo?etapa=4");
    expect(await screen.findByRole("heading", { name: /Etapa 4 · Receitas/ })).toBeInTheDocument();
    const select = screen.getByLabelText("Organização ativa");
    await user.selectOptions(select, ORG_B);
    await waitFor(() => {
      expect(localStorage.getItem("panne.activeOrganization")).toBe(ORG_B);
    });
    expect(screen.getByRole("heading", { name: "Fluxo produtivo" })).toBeInTheDocument();
  });

  it("abre ingredientes a partir do fluxo com retorno", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/fluxo?etapa=2");
    expect(await screen.findByRole("heading", { name: /Etapa 2/ })).toBeInTheDocument();
    const panel = screen.getByRole("article");
    await user.click(within(panel).getByRole("link", { name: "Abrir ingredientes" }));
    expect(await screen.findByRole("heading", { name: "Ingredientes" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Voltar ao fluxo" }).length).toBeGreaterThanOrEqual(1);
  });
});
