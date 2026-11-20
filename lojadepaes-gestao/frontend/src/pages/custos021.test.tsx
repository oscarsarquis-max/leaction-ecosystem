import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CustosVisao } from "../lib/api";
import { Custos } from "./Custos";

vi.mock("../lib/api", async () => {
  const atual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return {
    ...atual,
    carregarCustos: vi.fn(),
    salvarParametrosCusto: vi.fn(),
    criarCustoFixo: vi.fn(),
    editarCustoFixo: vi.fn(),
    apagarCustoFixo: vi.fn(),
    definirRegraFamilia: vi.fn(),
    definirRegraProduto: vi.fn(),
    definirPrecoProduto: vi.fn(),
  };
});

import { carregarCustos, criarCustoFixo, definirPrecoProduto, definirRegraFamilia, definirRegraProduto, salvarParametrosCusto } from "../lib/api";

/** O exemplo da conversa: R$ 3.000 de fixos, 600 kg/mês (R$ 5/kg); pão de 1 kg de massa e R$ 12 de ingredientes, R$ 70 na Loja. */
function visao(): CustosVisao {
  return {
    parametros: { massa_mensal_kg: 600, regra: { tipo: "margem", valor: 60 }, custo_fixo_total: 3000, custo_fixo_por_kg: 5 },
    custos_fixos: [
      { id: "c1", nome: "Aluguel", valor_mensal: 2000 },
      { id: "c2", nome: "Energia", valor_mensal: 1000 },
    ],
    familias: [{ id: "f1", nome: "Pães", regra: null }],
    produtos: [
      {
        produto_id: "p1",
        nome: "Pão Rústico",
        familia_id: "f1",
        familia: "Pães",
        receita_publicada: true,
        massa_g: 1000,
        custo_variavel: 12,
        custo_parcial: false,
        rateio: 5,
        custo_total: 17,
        regra_propria: null,
        regra: { tipo: "margem", valor: 60 },
        regra_origem: "geral",
        preco_sugerido: 30,
        loja: [{ variante: "Unidade", unidades: 1, preco: 70, preco_por_unidade: 70, mc: 58, mc_pct: 82.9, markup: 4.12, resultado: 53 }],
        preco_manual: null,
        preco_proprio: null,
      },
      {
        produto_id: "p2",
        nome: "Focaccia",
        familia_id: "f1",
        familia: "Pães",
        receita_publicada: true,
        massa_g: 700,
        custo_variavel: 20,
        custo_parcial: true,
        rateio: 3.5,
        custo_total: 23.5,
        regra_propria: { tipo: "markup", valor: 3 },
        regra: { tipo: "markup", valor: 3 },
        regra_origem: "produto",
        preco_sugerido: 70.5,
        loja: [{ variante: "Inteira", unidades: 1, preco: 22, preco_por_unidade: 22, mc: 2, mc_pct: 9.1, markup: 0.94, resultado: -1.5 }],
        preco_manual: null,
        preco_proprio: null,
      },
      {
        produto_id: "p3",
        nome: "Brioche",
        familia_id: null,
        familia: null,
        receita_publicada: true,
        massa_g: 400,
        custo_variavel: 6,
        custo_parcial: false,
        rateio: 2,
        custo_total: 8,
        regra_propria: null,
        regra: { tipo: "margem", valor: 60 },
        regra_origem: "geral",
        preco_sugerido: 15,
        loja: [],
        preco_manual: 20,
        preco_proprio: { variante: "Preço informado", unidades: 1, preco: 20, preco_por_unidade: 20, mc: 14, mc_pct: 70, markup: 2.5, resultado: 12 },
      },
    ],
  };
}

afterEach(() => vi.clearAllMocks());

describe("Custos (GESTAO-021)", () => {
  it("mostra o custo fixo por kg, o resultado por pão e o preço sugerido", async () => {
    vi.mocked(carregarCustos).mockResolvedValue(visao());
    render(<Custos />);
    const fixos = (await screen.findByRole("heading", { name: "Custos fixos do mês" })).closest("section")!;
    expect(within(fixos).getByText("R$ 3.000,00")).toBeInTheDocument();
    expect(within(fixos).getByText("R$ 5,00")).toBeInTheDocument();
    const linha = (nome: string) => screen.getByText(nome, { selector: "strong" }).closest("tr")!;
    expect(within(linha("Pão Rústico")).getByText("Sobra R$ 53,00")).toBeInTheDocument();
    expect(within(linha("Pão Rústico")).getByText("R$ 30,00")).toBeInTheDocument();
    expect(within(linha("Pão Rústico")).getByText(/Margem 60 % · geral/)).toBeInTheDocument();
    expect(within(linha("Focaccia")).getByText("Prejuízo R$ 1,50")).toBeInTheDocument();
    expect(within(linha("Focaccia")).getByText(/Markup 3× · do produto/)).toBeInTheDocument();
    expect(within(linha("Focaccia")).getByText("parcial")).toBeInTheDocument();
  });

  it("grava a massa do mês e adiciona um custo fixo", async () => {
    const usuario = userEvent.setup();
    vi.mocked(carregarCustos).mockResolvedValue(visao());
    vi.mocked(salvarParametrosCusto).mockResolvedValue(visao());
    vi.mocked(criarCustoFixo).mockResolvedValue(visao());
    render(<Custos />);
    const massa = await screen.findByLabelText("Massa produzida por mês");
    await usuario.clear(massa);
    await usuario.type(massa, "750");
    massa.blur();
    await waitFor(() =>
      expect(salvarParametrosCusto).toHaveBeenCalledWith({ massa_mensal_kg: 750, regra: { tipo: "margem", valor: 60 } }),
    );
    await usuario.type(screen.getByLabelText("Nome do novo custo"), "Limpeza");
    await usuario.type(screen.getByLabelText("Valor por mês do novo custo"), "350,50");
    await usuario.click(screen.getByRole("button", { name: "Adicionar" }));
    expect(criarCustoFixo).toHaveBeenCalledWith({ nome: "Limpeza", valor_mensal: 350.5 });
  });

  it("troca a regra geral para markup", async () => {
    const usuario = userEvent.setup();
    vi.mocked(carregarCustos).mockResolvedValue(visao());
    vi.mocked(salvarParametrosCusto).mockResolvedValue(visao());
    render(<Custos />);
    const geral = await screen.findByRole("group", { name: "Regra geral" });
    await usuario.selectOptions(within(geral).getByLabelText("Tipo, Regra geral"), "markup");
    const valor = within(geral).getByLabelText("Valor, Regra geral");
    await usuario.clear(valor);
    await usuario.type(valor, "3,5");
    await usuario.click(within(geral).getByRole("button", { name: "Salvar" }));
    expect(salvarParametrosCusto).toHaveBeenCalledWith({ massa_mensal_kg: 600, regra: { tipo: "markup", valor: 3.5 } });
  });

  it("define a margem da família e, no produto, volta a usar a de cima", async () => {
    const usuario = userEvent.setup();
    vi.mocked(carregarCustos).mockResolvedValue(visao());
    vi.mocked(definirRegraFamilia).mockResolvedValue(visao());
    vi.mocked(definirRegraProduto).mockResolvedValue(visao());
    render(<Custos />);
    const familia = await screen.findByRole("group", { name: "Regra da família Pães" });
    await usuario.selectOptions(within(familia).getByLabelText("Tipo, Regra da família Pães"), "margem");
    await usuario.type(within(familia).getByLabelText("Valor, Regra da família Pães"), "65");
    await usuario.click(within(familia).getByRole("button", { name: "Salvar" }));
    expect(definirRegraFamilia).toHaveBeenCalledWith("f1", { tipo: "margem", valor: 65 });

    await usuario.click(screen.getByRole("button", { name: /Focaccia/ }));
    const regra = await screen.findByRole("group", { name: "Regra de Focaccia" });
    await usuario.selectOptions(within(regra).getByLabelText("Tipo, Regra de Focaccia"), "herdar");
    await usuario.click(within(regra).getByRole("button", { name: "Salvar" }));
    expect(definirRegraProduto).toHaveBeenCalledWith("p2", null);
  });

  it("sem preço na Loja, usa o preço informado e deixa trocá-lo no painel (multicliente)", async () => {
    const usuario = userEvent.setup();
    vi.mocked(carregarCustos).mockResolvedValue(visao());
    vi.mocked(definirPrecoProduto).mockResolvedValue(visao());
    render(<Custos />);
    const linha = (await screen.findByText("Brioche", { selector: "strong" })).closest("tr")!;
    expect(within(linha).getByText("R$ 20,00")).toBeInTheDocument();
    expect(within(linha).getByText("informado")).toBeInTheDocument();
    expect(within(linha).getByText("Sobra R$ 12,00")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: /Brioche/ }));
    const campo = await screen.findByLabelText("Preço de venda por pão");
    await usuario.clear(campo);
    await usuario.type(campo, "22,50");
    await usuario.click(within(campo.closest(".regra-editor") as HTMLElement).getByRole("button", { name: "Salvar" }));
    expect(definirPrecoProduto).toHaveBeenCalledWith("p3", 22.5);
  });

  it("não aceita margem de 100 % ou mais", async () => {
    const usuario = userEvent.setup();
    vi.mocked(carregarCustos).mockResolvedValue(visao());
    render(<Custos />);
    const geral = await screen.findByRole("group", { name: "Regra geral" });
    const valor = within(geral).getByLabelText("Valor, Regra geral");
    await usuario.clear(valor);
    await usuario.type(valor, "100");
    expect(within(geral).getByRole("button", { name: "Salvar" })).toBeDisabled();
  });
});
