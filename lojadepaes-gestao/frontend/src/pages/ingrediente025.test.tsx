import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { GestaoContext } from "../contexto";
import { ApiError, type IngredienteDetalhe, type SessaoInfo } from "../lib/api";
import { Ingredientes } from "./Ingredientes";

vi.mock("../lib/api", async () => {
  const atual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return { ...atual, listarIngredientes: vi.fn(), detalheIngrediente: vi.fn(), excluirIngrediente: vi.fn() };
});

import { detalheIngrediente, excluirIngrediente, listarIngredientes } from "../lib/api";

const SESSAO: SessaoInfo = {
  usuario: "ana", nome: "Ana", admin_plataforma: false, papel: "dono", permissoes: ["ver_estoque", "lancar", "ajustar", "juntar"], csrf: "c",
  fuso: "America/Sao_Paulo", organizacao: null, organizacoes: [], precisa_escolher_organizacao: false,
};

const linha = (id: string, nome: string, saldo: number, itens: number) => ({
  id, nome, categoria: "Farinhas", apelidos: [], unidade_base: "g", ativo: true, saldo, itens, lotes: itens, vence_primeiro: null, vence_em_7_dias: false,
});

function detalhe(id: string, nome: string, comMovimento: boolean): IngredienteDetalhe {
  return {
    ...linha(id, nome, comMovimento ? 4000 : 0, comMovimento ? 1 : 0),
    custo_medio_base: null, lotes_com_custo: 0, lotes_com_saldo: 0,
    itens_detalhe: comMovimento ? [{ id: "it1", nome: "Farinha Tipo Nuvola", marca: "Caputo", unidade_controle: "massa", conteudo_embalagem: null, saldo: 4000 }] : [],
    lotes_detalhe: [], movimentos: [], juntado_em_id: null,
  } as unknown as IngredienteDetalhe;
}

function renderizar() {
  return render(
    <GestaoContext.Provider value={{ sessao: SESSAO, search: "", navegar: vi.fn(), atualizarFluxo: () => {}, pode: (a) => SESSAO.permissoes.includes(a), definirTitulo: () => {} }}>
      <Ingredientes />
    </GestaoContext.Provider>,
  );
}

afterEach(() => vi.clearAllMocks());

describe("excluir ingrediente cadastrado por engano (GESTAO-025)", () => {
  it("sem item, lote nem movimento: Excluir aparece, confirma e some da lista", async () => {
    const usuario = userEvent.setup();
    vi.mocked(listarIngredientes).mockResolvedValue({ filtro: "todos", ingredientes: [linha("dup", "Farinha de Trigo Especial Nuvola", 0, 0), linha("t0", "Farinha de trigo tipo 0", 4000, 1)], pares_parecidos: [], categorias: [] } as never);
    vi.mocked(detalheIngrediente).mockResolvedValue(detalhe("dup", "Farinha de Trigo Especial Nuvola", false));
    vi.mocked(excluirIngrediente).mockResolvedValue(undefined);
    renderizar();
    await usuario.click(await screen.findByRole("button", { name: /^Farinha de Trigo Especial Nuvola/ }));
    const painel = await screen.findByRole("dialog", { name: "Farinha de Trigo Especial Nuvola" });
    await usuario.click(await within(painel).findByRole("button", { name: "Excluir" }));
    const confirma = await screen.findByRole("dialog", { name: "Excluir ingrediente" });
    await usuario.click(within(confirma).getByRole("button", { name: "Excluir" }));
    await waitFor(() => expect(excluirIngrediente).toHaveBeenCalledWith("dup"));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Farinha de Trigo Especial Nuvola" })).not.toBeInTheDocument());
    expect(listarIngredientes).toHaveBeenCalledTimes(2);
  });

  it("com item ou saldo, não há Excluir (aí é Juntar com…)", async () => {
    const usuario = userEvent.setup();
    vi.mocked(listarIngredientes).mockResolvedValue({ filtro: "todos", ingredientes: [linha("t0", "Farinha de trigo tipo 0", 4000, 1)], pares_parecidos: [], categorias: [] } as never);
    vi.mocked(detalheIngrediente).mockResolvedValue(detalhe("t0", "Farinha de trigo tipo 0", true));
    renderizar();
    await usuario.click(await screen.findByRole("button", { name: /^Farinha de trigo tipo 0/ }));
    const painel = await screen.findByRole("dialog", { name: "Farinha de trigo tipo 0" });
    expect(await within(painel).findByRole("button", { name: "Juntar com…" })).toBeInTheDocument();
    expect(within(painel).queryByRole("button", { name: "Excluir" })).not.toBeInTheDocument();
  });

  it("se o servidor recusar (está numa receita), mostra o motivo e não fecha", async () => {
    const usuario = userEvent.setup();
    vi.mocked(listarIngredientes).mockResolvedValue({ filtro: "todos", ingredientes: [linha("dup", "Farinha Duplicada", 0, 0)], pares_parecidos: [], categorias: [] } as never);
    vi.mocked(detalheIngrediente).mockResolvedValue(detalhe("dup", "Farinha Duplicada", false));
    vi.mocked(excluirIngrediente).mockRejectedValue(new ApiError(409, "Está na receita Pão Rústico. Use Juntar com…", "em_uso"));
    renderizar();
    await usuario.click(await screen.findByRole("button", { name: /^Farinha Duplicada/ }));
    const painel = await screen.findByRole("dialog", { name: "Farinha Duplicada" });
    await usuario.click(await within(painel).findByRole("button", { name: "Excluir" }));
    const confirma = await screen.findByRole("dialog", { name: "Excluir ingrediente" });
    await usuario.click(within(confirma).getByRole("button", { name: "Excluir" }));
    expect(await within(confirma).findByRole("alert")).toHaveTextContent("Está na receita Pão Rústico");
  });
});
