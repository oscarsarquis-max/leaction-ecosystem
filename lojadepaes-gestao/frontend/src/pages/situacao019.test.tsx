import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GestaoContext } from "../contexto";
import type { ProdutoLinha, ReceitaFicha, SessaoInfo } from "../lib/api";
import { selosDaReceita } from "../lib/situacaoReceita";
import { Produtos } from "./Produtos";
import { EditorReceita } from "./Receitas";

vi.mock("../lib/api", async () => {
  const atual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return {
    ...atual,
    listarProdutos: vi.fn(),
    listarFamilias: vi.fn(async () => ({ familias: [], sugestoes: [] })),
    detalheReceita: vi.fn(),
    salvarReceita: vi.fn(),
    publicarReceita: vi.fn(),
    situacaoGigio: vi.fn(async () => ({ disponivel: false, motivo: "desligado", usadas: 0, limite: 30 })),
  };
});

import { detalheReceita, listarProdutos, publicarReceita } from "../lib/api";

const SESSAO: SessaoInfo = {
  usuario: "ana",
  nome: "Ana",
  admin_plataforma: false,
  papel: "dono",
  permissoes: ["ver_estoque", "lancar"],
  csrf: "c",
  fuso: "America/Sao_Paulo",
  organizacao: null,
  organizacoes: [],
  precisa_escolher_organizacao: false,
};

function contexto(children: React.ReactNode) {
  return (
    <GestaoContext.Provider
      value={{ sessao: SESSAO, search: "", navegar: vi.fn(), atualizarFluxo: () => {}, pode: () => true, definirTitulo: () => {} }}
    >
      {children}
    </GestaoContext.Provider>
  );
}

function produto(id: string, nome: string, extra: Partial<ProdutoLinha>): ProdutoLinha {
  return {
    id,
    nome,
    codigo: null,
    modalidade: "produzido",
    uso_venda: true,
    uso_componente: false,
    familia_id: null,
    familia: null,
    unidade_venda: "un",
    ativo: true,
    selos: [],
    pendente: false,
    foto_url: null,
    tem_foto: false,
    foto_enviada_em: null,
    ...extra,
  };
}

function ficha(situacao: "rascunho" | "publicada", versao: number, publicada: boolean, pendencias: { codigo: string; mensagem: string }[] = []): ReceitaFicha {
  return {
    id: "r1",
    produto_id: "p1",
    produto: "Levain",
    cultura_viva: true,
    ingrediente_id: "ing-levain",
    situacao,
    versao,
    rendimento_quantidade: 399,
    rendimento_unidade: "g",
    rendimento: "399 g",
    peso_unidade_g: null,
    perda_percentual: 0,
    modo_fazer: [],
    selos: [],
    publicada: publicada ? { versao: situacao === "publicada" ? versao : versao - 1, linhas: [] } : null,
    linhas: [
      {
        id: "l1",
        ingrediente_id: "ing-t0",
        nome: "Farinha de trigo tipo 0",
        categoria: "Farinhas",
        componente: false,
        unidade_base: "g",
        texto: null,
        a_decidir: false,
        quantidade: 100,
        unidade: "g",
        ordem: 1,
        observacao: null,
        percentual_padeiro: 100,
        custo: 3.79,
        origem: "manual",
        faixa_min: null,
        faixa_max: null,
        funcao: "massa",
      },
    ],
    total_massa_g: 100,
    custo_total: 3.79,
    custo_parcial: false,
    linhas_sem_custo: 0,
    custo_por_unidade: null,
    verificacoes: { pendencias, avisos: [] },
    modo_rendimento: "massa",
    rendimento_massa: { massa_g: 100, processo_pct: 5, rende_g: 95, reserva_g: 0, disponivel_g: 95, custo_por_kg: 39.89 },
  } as unknown as ReceitaFicha;
}

beforeEach(() => {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: String(query).includes("1024"),
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
});

afterEach(() => vi.clearAllMocks());

describe("situação da receita (GESTAO-019)", () => {
  it("as quatro situações viram selos claros", () => {
    expect(selosDaReceita(null)).toEqual([{ stage: "cancelled", label: "Sem receita" }]);
    expect(selosDaReceita({ situacao: "rascunho", versao: 1, publicada: false, linhas: 0 })).toEqual([{ stage: "cancelled", label: "Sem receita" }]);
    expect(selosDaReceita({ situacao: "rascunho", versao: 1, publicada: false, linhas: 6 })).toEqual([{ stage: "warning", label: "Rascunho" }]);
    expect(selosDaReceita({ situacao: "publicada", versao: 1, publicada: true, linhas: 6 })).toEqual([{ stage: "ok", label: "Publicada v1" }]);
    expect(selosDaReceita({ situacao: "rascunho", versao: 2, publicada: true, linhas: 6 })).toEqual([
      { stage: "ok", label: "Publicada v1" },
      { stage: "warning", label: "Rascunho v2" },
    ]);
  });

  it("a coluna Situação de Produtos mostra a receita publicada, o rascunho, a falta e o item", async () => {
    vi.mocked(listarProdutos).mockResolvedValue({
      filtro: "todos",
      familias: [],
      produtos: [
        produto("a", "Levain", { uso_venda: false, uso_componente: true, receita: { situacao: "publicada", versao: 1, publicada: true, linhas: 6 } }),
        produto("b", "Focaccia", { receita: { situacao: "rascunho", versao: 2, publicada: true, linhas: 7 } }),
        produto("c", "Pão Rústico", { selos: ["sem_receita"], pendente: true, receita: { situacao: "rascunho", versao: 1, publicada: false, linhas: 4 } }),
        produto("d", "Pão Sovado", { selos: ["sem_receita"], pendente: true, receita: { situacao: "rascunho", versao: 1, publicada: false, linhas: 0 } }),
        produto("e", "Manteiga", { modalidade: "comprado", receita: null }),
      ],
    });
    render(contexto(<Produtos />));
    const linha = async (nome: string) => (await screen.findByText(nome, { selector: "strong" })).closest("tr") as HTMLElement;
    expect(within(await linha("Levain")).getByText("Publicada v1")).toBeInTheDocument();
    expect(within(await linha("Focaccia")).getByText("Publicada v1")).toBeInTheDocument();
    expect(within(await linha("Focaccia")).getByText("Rascunho v2")).toBeInTheDocument();
    expect(within(await linha("Pão Rústico")).getByText("Rascunho")).toBeInTheDocument();
    expect(within(await linha("Pão Rústico")).queryByText("Sem receita")).not.toBeInTheDocument();
    expect(within(await linha("Pão Sovado")).getByText("Sem receita")).toBeInTheDocument();
    expect(within(await linha("Manteiga")).getByText("Item ligado")).toBeInTheDocument();
  });

  it("o rodapé do editor mostra a situação e publica sem ir ao Revisar", async () => {
    const usuario = userEvent.setup();
    vi.mocked(detalheReceita).mockResolvedValue(ficha("rascunho", 1, false));
    vi.mocked(publicarReceita).mockResolvedValue(ficha("publicada", 1, true));
    render(contexto(<EditorReceita produtoId="p1" />));
    const rodape = await screen.findByRole("region", { name: "Resumo da receita" });
    const situacao = screen.getByLabelText("Situação da receita");
    expect(within(situacao).getByText("Rascunho")).toBeInTheDocument();
    await usuario.click(within(rodape).getByRole("button", { name: "Publicar versão 1" }));
    await waitFor(() => expect(publicarReceita).toHaveBeenCalledWith("p1", false));
    expect(await within(situacao).findByText("Publicada v1")).toBeInTheDocument();
    expect(within(rodape).queryByRole("button", { name: /Publicar/ })).not.toBeInTheDocument();
    expect(within(rodape).queryByRole("button", { name: "Salvar rascunho" })).not.toBeInTheDocument();
  });

  it("com falta de fermento, o Publicar do rodapé leva ao Revisar em vez de publicar", async () => {
    const usuario = userEvent.setup();
    vi.mocked(detalheReceita).mockResolvedValue(ficha("rascunho", 1, false, [{ codigo: "sem_fermento", mensagem: "Falta o fermento." }]));
    render(contexto(<EditorReceita produtoId="p1" />));
    const rodape = await screen.findByRole("region", { name: "Resumo da receita" });
    await usuario.click(within(rodape).getByRole("button", { name: "Publicar versão 1" }));
    expect(publicarReceita).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Revisar" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Publicar mesmo assim, sem fermento")).toBeInTheDocument();
  });

  it("rascunho da versão 2 mostra a v1 valendo e o rascunho", async () => {
    vi.mocked(detalheReceita).mockResolvedValue(ficha("rascunho", 2, true));
    render(contexto(<EditorReceita produtoId="p1" />));
    const rodape = await screen.findByRole("region", { name: "Resumo da receita" });
    const situacao = screen.getByLabelText("Situação da receita");
    expect(within(situacao).getByText("Publicada v1")).toBeInTheDocument();
    expect(within(situacao).getByText("Rascunho v2")).toBeInTheDocument();
    expect(within(rodape).getByRole("button", { name: "Publicar versão 2" })).toBeInTheDocument();
  });
});
