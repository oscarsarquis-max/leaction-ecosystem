import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ROUTE_GUIDES, matchGuide } from "./guide/routes";
import { INTENTS } from "./guide/intents";
import { installApiMock } from "./test/fetchMock";
import { renderApp } from "./test/renderApp";

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
  sessionStorage.clear();
});

const PRODUCTIVE = [
  "/entrar",
  "/inicio",
  "/fluxo",
  "/componentes/ingredientes",
  "/componentes/estoque",
  "/componentes/estoque/posicao",
  "/componentes/estoque/reservas",
  "/componentes/estoque/movimentacoes",
  "/componentes/estoque/separacao",
  "/componentes/lotes",
  "/componentes/fornecedores",
  "/componentes/catalogos",
  "/produtos",
  "/produtos/novo",
  "/produtos/familias",
  "/receitas",
  "/receitas/assistente",
  "/producao",
  "/planejamento",
  "/ordens",
  "/rastreabilidade",
  "/conformidade",
  "/conformidade/dossies",
  "/conformidade/avaliacoes",
  "/conformidade/rotulos",
  "/conformidade/fontes",
  "/gestao/custos",
  "/gestao/custos/politicas",
  "/gestao/custos/previstos",
  "/gestao/custos/realizados",
  "/gestao/custos/simulacoes",
  "/gestao/custos/precos",
  "/gestao/compras/necessidades",
  "/gestao/compras/requisicoes",
  "/gestao/compras/cotacoes",
  "/gestao/compras/pedidos",
  "/gestao/compras/recebimentos",
  "/gestao/compras/devolucoes",
  "/gestao/inventarios",
  "/gestao/relatorios",
  "/gestao/relatorios/executivo",
  "/gestao/relatorios/producao",
  "/gestao/relatorios/componentes",
  "/gestao/relatorios/custos",
  "/gestao/relatorios/conformidade",
  "/gestao/relatorios/rastreabilidade",
  "/gestao/relatorios/estoque",
  "/gestao/relatorios/qualidade",
  "/gestao/relatorios/salvos",
];

describe("contrato de rotas e assistente", () => {
  it("cobre todas as rotas produtivas", () => {
    for (const path of PRODUCTIVE) {
      expect(matchGuide(path), path).toBeTruthy();
    }
    expect(ROUTE_GUIDES.every((row) => row.version === 1)).toBe(true);
    expect(INTENTS.length).toBeGreaterThanOrEqual(10);
  });

  it("abre o assistente no quadro e mostra próxima ação", async () => {
    installApiMock();
    await renderApp("/producao");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Abrir Gigio, assistente da Panne" }));
    const assist = await screen.findByRole("dialog", { name: "Gigio" });
    expect(assist).toHaveTextContent(/Você está em/);
    expect(assist).toHaveTextContent(/Conduzir o turno/);
  });

  it("reusa a mesma gaveta para o fluxo específico", async () => {
    installApiMock();
    await renderApp("/gestao/compras/necessidades");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Abrir no assistente" }));
    expect(await screen.findByRole("dialog", { name: "Gigio" })).toBeInTheDocument();
    expect(screen.getByText("Voltar à orientação")).toBeInTheDocument();
  });
});
