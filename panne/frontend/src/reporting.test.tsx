import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { axe } from "vitest-axe";
import { operatorMeFixture } from "./api/fixtures";
import { installApiMock, json } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("relatórios e painéis", () => {
  it("mostra Gestão, Relatórios e subáreas", async () => {
    installApiMock();
    const { view } = await renderApp("/gestao/relatorios");
    expect(await screen.findByRole("heading", { name: "Relatórios e painéis" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Relatórios" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Produção" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("link", { name: "Qualidade dos dados" })).toBeInTheDocument();
    expect(document.body.textContent).toMatch(/Ausência não é zero/);
    expect(await axe(view.container)).toEqual(expect.objectContaining({ violations: [] }));
  });

  it("compara períodos e mostra tabela equivalente do gráfico", async () => {
    installApiMock();
    await renderApp("/gestao/relatorios/executivo?comparar=1");
    expect(await screen.findByRole("heading", { name: "Visão executiva" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Comparação escolhida" })).toBeInTheDocument();
    expect(screen.getByText("Tabela equivalente da composição")).toBeInTheDocument();
    expect(screen.getByLabelText("Comparar com o período anterior")).toBeChecked();
  });

  it("mostra cartões, cobertura, ausência e filtros na URL", async () => {
    installApiMock();
    const user = userEvent.setup();
    await renderApp("/gestao/relatorios/executivo");
    expect(await screen.findByRole("heading", { name: "Visão executiva" })).toBeInTheDocument();
    expect(screen.getByText(/Dados até/)).toBeInTheDocument();
    expect(screen.getAllByText(/indisponível/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Cobertura/i).length).toBeGreaterThan(0);
    await user.click(screen.getByRole("button", { name: "Aplicar filtros" }));
    await user.click(screen.getAllByRole("button", { name: "Abrir detalhes" })[0]);
    await waitFor(() => {
      expect(screen.getByText("OP-1")).toBeInTheDocument();
    });
  });

  it("esconde custos do perfil operacional", async () => {
    installApiMock({
      "/api/v1/me": () => json(operatorMeFixture),
    });
    await renderApp("/gestao/relatorios");
    expect(await screen.findByRole("heading", { name: "Relatórios e painéis" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Custos e preços" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Visão executiva" })).not.toBeInTheDocument();
  });

  it("lista visão salva e snapshot", async () => {
    installApiMock();
    await renderApp("/gestao/relatorios/salvos");
    expect(await screen.findByRole("heading", { name: "Relatórios salvos" })).toBeInTheDocument();
    expect(await screen.findByText(/Turno da manhã/)).toBeInTheDocument();
  });
});
