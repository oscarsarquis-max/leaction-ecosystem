import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { meFixture, ORG_A, ORG_B, productSummaryFixture } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";
import {
  buildOrientation,
  inferModality,
} from "./fluxo/orientation";
import type { FlowEvidence } from "./fluxo/resolve";
import { resolveStepSituation } from "./fluxo/resolve";
import { FLOW_STEPS } from "./fluxo/steps";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

const emptyEvidence: FlowEvidence = {
  ingredientsTotal: null,
  recipesTotal: null,
  ordersTotal: null,
  inventoryItemsTotal: null,
  products: null,
  fiscal: null,
};

describe("Adendo fluxo + Gigio", () => {
  it("login → organização → /fluxo com mapa dominante e Gigio", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/fluxo");
    expect(await screen.findByRole("heading", { name: "Fluxo produtivo" })).toBeInTheDocument();
    expect(
      screen.getByText(/Da entrada da mercadoria ao preço e à gestão do produto acabado/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Visão geral da organização/i })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Etapas do fluxo produtivo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Custos e preços/i })).toBeInTheDocument();
    expect(screen.getAllByAltText("Gigio, assistente da Panne").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("heading", { name: "Resumo do caminho" })).toBeInTheDocument();
    expect(screen.getByText(/Sem bloqueio urgente|O que impede avançar/i)).toBeInTheDocument();
    const map = screen.getByRole("navigation", { name: "Etapas do fluxo produtivo" });
    expect(within(map).getAllByRole("button").length).toBeGreaterThanOrEqual(7);
  });

  it("foco diferente da posição real ao clicar etapa", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/fluxo?etapa=1");
    await screen.findByRole("heading", { name: "Fluxo produtivo" });
    const map = screen.getByRole("navigation", { name: "Etapas do fluxo produtivo" });
    const custos = within(map).getByRole("button", { name: /Custos e preços/i });
    await user.click(custos);
    expect(custos).toHaveAttribute("aria-current", "step");
    expect(within(custos).getByText(/Em foco para consulta|Posição e foco/i)).toBeInTheDocument();
  });

  it("jornada de produto comprado marca etapas não aplicáveis", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/fluxo");
    await user.click(await screen.findByRole("button", { name: /Jornada de um produto/i }));
    const select = await screen.findByLabelText(/Produto \(nome ou código\)/i);
    await user.selectOptions(select, "REF-COLA");
    await waitFor(() => {
      expect(
        screen.getAllByText(/Não se aplica — produto comprado|jornada de produto comprado/i).length,
      ).toBeGreaterThanOrEqual(1);
    });
  });

  it("Gigio visível nas telas da jornada sem abrir o chat", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/receitas");
    expect(await screen.findByRole("heading", { name: "Minhas receitas" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abrir Gigio" })).toBeInTheDocument();
    expect(screen.queryByRole("complementary", { name: /Orientação do processo/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Gigio" })).not.toBeInTheDocument();
  });

  it("avatar flutuante usa Gigio e abre gaveta com o nome correto", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/fluxo");
    const open = await screen.findByRole("button", { name: "Abrir Gigio" });
    expect(within(open).getByAltText("Gigio, assistente da Panne")).toBeInTheDocument();
    await user.click(open);
    expect(await screen.findByRole("dialog", { name: "Gigio" })).toBeInTheDocument();
  });

  it("produto comprado: receita não se aplica", () => {
    const products = {
      total: 4,
      active: 4,
      purchased: 4,
      intermediate: 0,
      produced_without_recipe: 0,
    };
    expect(inferModality(products)).toBe("purchased");
    const recipe = FLOW_STEPS.find((row) => row.id === 4)!;
    const resolved = resolveStepSituation(recipe, () => true, { ...emptyEvidence, products, recipesTotal: 0 }, null);
    expect(resolved.situation).toBe("Não se aplica");
    const orientation = buildOrientation({
      organizationId: ORG_A,
      organizationName: "Org A",
      establishmentId: null,
      profile: "owner",
      stepId: 4,
      stepTitle: "Receitas",
      situation: resolved.situation,
      pending: resolved.pending,
      nextAction: resolved.nextAction,
      permissions: ["recipe.read", "labeling.read"],
      productModality: "purchased",
      products,
      fiscal: null,
      recipesTotal: 0,
      ordersTotal: null,
      ingredientsTotal: null,
      inventoryItemsTotal: null,
      blocks: [],
      alerts: [],
    });
    expect(orientation.modalityNote).toMatch(/comprado/i);
    expect(orientation.recommended?.to).toContain("etapa=7");
    expect(orientation.recommended?.allowed).toBe(true);
  });

  it("produto produzido sem receita requer atenção", () => {
    const products = {
      total: 2,
      active: 2,
      purchased: 0,
      intermediate: 0,
      produced_without_recipe: 2,
    };
    expect(inferModality(products)).toBe("produced");
    const recipe = FLOW_STEPS.find((row) => row.id === 4)!;
    const resolved = resolveStepSituation(recipe, () => true, { ...emptyEvidence, products, recipesTotal: 0 }, null);
    expect(resolved.situation).toBe("Requer atenção");
    expect(resolved.pending).toMatch(/sem receita/i);
  });

  it("produto produzido com receita fica pronto", () => {
    const products = {
      total: 2,
      active: 2,
      purchased: 0,
      intermediate: 0,
      produced_without_recipe: 0,
    };
    const recipe = FLOW_STEPS.find((row) => row.id === 4)!;
    const resolved = resolveStepSituation(
      recipe,
      () => true,
      { ...emptyEvidence, products, recipesTotal: 3 },
      null,
    );
    expect(resolved.situation).toBe("Pronto");
  });

  it("etapa de custos oculta sem permissão", async () => {
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
    expect(screen.getAllByText(/Etapa \d+ de 7/).length).toBeGreaterThanOrEqual(1);
    const rail = screen.getByRole("navigation", { name: "Etapas do fluxo produtivo" });
    expect(within(rail).getAllByRole("button")).toHaveLength(7);
    const lede = document.querySelector(".flow-page .lede")?.textContent ?? "";
    expect(lede).toMatch(/Da entrada da mercadoria ao preço/i);
  });

  it("Proprietário autorizado vê a oitava etapa Custos e preços", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          associations: meFixture.associations.map((row) =>
            row.organization_id === ORG_A
              ? { ...row, roles: ["owner"], permissions: row.permissions }
              : row,
          ),
          roles: ["owner"],
        }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/fluxo");
    expect(await screen.findByRole("heading", { name: "Fluxo produtivo" })).toBeInTheDocument();
    expect(screen.getAllByText("Proprietário").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/Etapa 1 de 8/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("button", { name: /Custos e preços/i })).toBeInTheDocument();
    const rail = screen.getByRole("navigation", { name: "Etapas do fluxo produtivo" });
    expect(within(rail).getAllByRole("button")).toHaveLength(8);
    const ownerLede = document.querySelector(".flow-page .lede")?.textContent ?? "";
    expect(ownerLede).toMatch(/Da entrada da mercadoria ao preço/i);
  });

  it("trilha na tela participante usa a mesma contagem canônica do fluxo", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/gestao/compras/entradas");
    const trail = await screen.findByRole("navigation", { name: "Trilha do fluxo produtivo" });
    expect(within(trail).getByText(/Etapa 1 de 8/)).toBeInTheDocument();
    expect(trail.querySelectorAll(".flow-trail__steps a")).toHaveLength(8);
  });

  it("troca de organização limpa orientação do coach", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    const user = userEvent.setup();
    await renderApp("/receitas");
    expect(await screen.findByRole("button", { name: "Abrir Gigio" })).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Organização ativa"), ORG_B);
    await waitFor(() => {
      expect(localStorage.getItem("panne.activeOrganization")).toBe(ORG_B);
    });
    expect(await screen.findByRole("button", { name: "Abrir Gigio" })).toBeInTheDocument();
  });

  it("não cria botão morto quando a ação recomendada não é permitida", () => {
    const orientation = buildOrientation({
      organizationId: ORG_A,
      organizationName: "Org A",
      establishmentId: null,
      profile: "baker_operator",
      stepId: 8,
      stepTitle: "Custos e preços",
      situation: "Não se aplica",
      pending: "Sem acesso aos custos",
      nextAction: "Continuar pelo acabamento",
      permissions: [],
      productModality: "unknown",
      products: productSummaryFixture,
      fiscal: null,
      recipesTotal: null,
      ordersTotal: null,
      ingredientsTotal: null,
      inventoryItemsTotal: null,
      blocks: [],
      alerts: [],
    });
    expect(orientation.recommended?.allowed).toBeFalsy();
  });

  it("entrada fiscal: subetapas visíveis na etapa 1", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/fluxo?etapa=1");
    expect(await screen.findByRole("heading", { name: /Etapa 1 · Compras e entradas/ })).toBeInTheDocument();
    expect(screen.getByText("Correspondência dos itens")).toBeInTheDocument();
    expect(screen.getByText("Conferência física")).toBeInTheDocument();
    expect(screen.getByText(/Atualização de estoque e custos/)).toBeInTheDocument();
  });
});
