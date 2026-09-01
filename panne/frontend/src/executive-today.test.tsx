import { screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { dashboardTodayEmptyFixture, dashboardTodayFixture, meFixture, ORG_A } from "./api/fixtures";
import { FORBIDDEN_SURFACE_ENGLISH } from "./language/surface";
import { EXEC_LIMITS } from "./pages/executiveLimits";
import { prioritizeCostRows } from "./pages/executiveCharts";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

const bannedSurface = ["backend", "frontend", "payload", "append-only", "source", "active", "missing", "planned", "current_price"];

describe("CURSOR-028-R3 painel executivo", () => {
  it("compõe a primeira dobra com resumo, faixa e produção", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/inicio");
    expect(await screen.findByRole("heading", { name: "Hoje na Panne" })).toBeInTheDocument();
    expect(screen.getByText("Painel do proprietário")).toBeInTheDocument();
    expect(screen.getByText(/O negócio pede/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver prioridades" })).toBeInTheDocument();

    const rail = screen.getByRole("region", { name: "Indicadores principais" });
    expect(within(rail).getAllByRole("heading", { level: 3 })).toHaveLength(6);
    expect(within(rail).getByText("Ordens de hoje")).toBeInTheDocument();
    expect(within(rail).getByText("Em andamento")).toBeInTheDocument();
    expect(within(rail).getByText("Entradas aguardadas")).toBeInTheDocument();
    expect(within(rail).getByText("Estoque crítico")).toBeInTheDocument();
    expect(within(rail).getByText("Custos completos")).toBeInTheDocument();
    expect(within(rail).getByText("Preços sem base comercial")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Hoje" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Atenções" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Negócio" })).not.toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Produção planejada × registrada" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Abrir produção" }).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Sem medição").length).toBeGreaterThan(0);
    expect(screen.getByText(/ordem sem medição/)).toBeInTheDocument();
    expect(screen.queryByText("0,00")).not.toBeInTheDocument();
    expect(screen.queryByText(/produto\(s\)/)).not.toBeInTheDocument();
  });

  it("limita agenda, custos e separa produto comprado", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/inicio");
    await screen.findByRole("heading", { name: "Agenda operacional" });
    const agenda = screen.getByRole("table", { name: "Agenda operacional" });
    expect(within(agenda).getAllByRole("row")).toHaveLength(EXEC_LIMITS.agenda + 1);
    expect(screen.queryByText("OP-29")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Agenda completa" })).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Composição do custo" })).toBeInTheDocument();
    expect(screen.getAllByText("Pão francês").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Parcial").length).toBeGreaterThan(0);
    expect(screen.queryByText("Bagel")).not.toBeInTheDocument();
    expect(screen.getByText(/Produto comprado/)).toBeInTheDocument();
    expect(screen.getByText(/Manteiga tablete/)).toBeInTheDocument();
    expect(screen.getByText(/Aquisição R\$ 18,00 por unidade/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Analisar todos os custos" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Preços e histórico" })).toBeInTheDocument();
    expect(screen.getByText("Não calculável")).toBeInTheDocument();
  });

  it("ontem vazio vira uma frase só e movimentações vazias ficam compactas", async () => {
    installApiMock({
      "/dashboard/today": () => json(dashboardTodayEmptyFixture),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/inicio");
    expect(await screen.findByRole("heading", { name: "Hoje na Panne" })).toBeInTheDocument();
    expect(screen.getByText(/Horizonte/)).toBeInTheDocument();
    expect(screen.getByText("Ontem — não há produção, recebimentos ou perdas registrados.")).toBeInTheDocument();
    expect(screen.getAllByText("Ontem — não há produção, recebimentos ou perdas registrados.")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Consultar o período" })).toBeInTheDocument();

    expect(screen.getByText("Não há movimentações neste período")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir movimentações" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ver tabela" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Ver gráfico" })).not.toBeInTheDocument();
    expect(screen.queryByText("R$ 0")).not.toBeInTheDocument();
  });

  it("esconde economia sem permissão e não inventa zero", async () => {
    installApiMock({
      "/api/v1/me": () =>
        json({
          ...meFixture,
          permissions: meFixture.permissions.filter((code) => !code.startsWith("costing.") && !code.startsWith("pricing.")),
          associations: meFixture.associations.map((row) => ({
            ...row,
            permissions: row.permissions.filter((code) => !code.startsWith("costing.") && !code.startsWith("pricing.")),
          })),
        }),
    });
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/inicio");
    expect(await screen.findByRole("heading", { name: "Hoje na Panne" })).toBeInTheDocument();
    const rail = screen.getByRole("region", { name: "Indicadores principais" });
    expect(within(rail).queryByText("Custos completos")).not.toBeInTheDocument();
    expect(within(rail).queryByText("Preços sem base comercial")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Composição do custo" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Preço, custo e margem" })).not.toBeInTheDocument();
    expect(screen.queryByText("0,00")).not.toBeInTheDocument();
  });

  it("Gigio permanece flutuante e a superfície não vaza inglês", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/inicio");
    await screen.findByRole("heading", { name: "Hoje na Panne" });
    expect(screen.getByRole("button", { name: "Abrir Gigio" })).toBeInTheDocument();
    expect(document.querySelector(".flow-gigio")).toBeNull();
    expect(document.querySelector(".product-gigio-fab")).toBeNull();
    const surface = document.querySelector(".exec-today")?.textContent || "";
    for (const word of bannedSurface) {
      expect(surface.toLowerCase()).not.toContain(word);
    }
    expect(surface).not.toMatch(FORBIDDEN_SURFACE_ENGLISH);
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(document.documentElement.clientWidth);
  });

  it("preserva os acessos de detalhamento", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/inicio");
    await screen.findByRole("heading", { name: "Hoje na Panne" });
    expect(screen.getByRole("link", { name: "Abrir Fluxo produtivo" })).toHaveAttribute("href", "/fluxo");
    expect(screen.getAllByRole("link", { name: "Abrir produção" })[0]).toHaveAttribute("href", "/producao");
    expect(screen.getByRole("link", { name: "Abrir custos e preços" })).toHaveAttribute("href", "/gestao/custos");
    expect(screen.getByRole("link", { name: "Ver todas as pendências" })).toHaveAttribute("href", "/gestao/relatorios");
  });

  it("prioriza custo parcial antes do completo", () => {
    const ordered = prioritizeCostRows(
      [
        { label: "Completo", completeness: "complete" },
        { label: "Parcial", completeness: "partial" },
        { label: "Vazio", completeness: "empty" },
      ],
      ["Parcial"],
    );
    expect(ordered.map((row) => row.label)).toEqual(["Parcial", "Vazio", "Completo"]);
  });

  it("oferece tabela só quando o recorte tem série", async () => {
    installApiMock();
    localStorage.setItem("panne.activeOrganization", ORG_A);
    await renderApp("/inicio");
    await screen.findByRole("heading", { name: "Produção planejada × registrada" });
    expect(screen.getAllByRole("button", { name: "Ver tabela" }).length).toBeGreaterThan(0);
  });
});

describe("CURSOR-028-R3 contrato da faixa", () => {
  it("não ultrapassa seis indicadores", () => {
    expect(EXEC_LIMITS.kpis).toBe(6);
    expect(dashboardTodayFixture.charts.costs?.series.filter((row) => row.supply_mode === "purchased").length).toBeGreaterThan(0);
  });
});
