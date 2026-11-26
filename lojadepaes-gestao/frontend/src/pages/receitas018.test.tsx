import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GestaoContext } from "../contexto";
import type { ReceitaFicha, SessaoInfo } from "../lib/api";
import { EditorReceita } from "./Receitas";

vi.mock("../lib/api", async () => {
  const atual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return {
    ...atual,
    detalheReceita: vi.fn(),
    salvarReceita: vi.fn(),
    situacaoGigio: vi.fn(async () => ({ disponivel: false, motivo: "desligado", usadas: 0, limite: 30 })),
    publicarReceita: vi.fn(),
    buscarIngredientes: vi.fn(),
    sugerirIngrediente: vi.fn(async () => []),
  };
});

import { detalheReceita, salvarReceita } from "../lib/api";

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

function linha(id: string, ingrediente: string, nome: string, categoria: string, quantidade: number, extra: object = {}) {
  return {
    id,
    ingrediente_id: ingrediente,
    nome,
    categoria,
    componente: false,
    unidade_base: "g",
    texto: null,
    a_decidir: false,
    quantidade,
    unidade: "g",
    ordem: 1,
    observacao: null,
    percentual_padeiro: null,
    custo: null,
    origem: "manual",
    faixa_min: null,
    faixa_max: null,
    funcao: "massa",
    ...extra,
  };
}

const PERDA = (pct: number | null) => ({ percentual: pct, origem: pct == null ? null : "padrao", rotulo: "padrão da casa", motivo: null });

/** O Levain como o Oscar lançou em 12/11 (420 g; inóculo 100 g; 5 % de processo; mel sem custo). */
function levain(): ReceitaFicha {
  return {
    id: "r1",
    produto_id: "p1",
    produto: "Levain (fermento natural líquido)",
    cultura_viva: true,
    ingrediente_id: "ing-levain",
    situacao: "rascunho",
    versao: 1,
    rendimento_quantidade: null,
    rendimento_unidade: null,
    rendimento: null,
    peso_unidade_g: 400,
    perda_percentual: 0,
    formato: null,
    unidades_desejadas: 4,
    modo_fazer: ["Misture todos os ingredientes."],
    selos: ["rascunho"],
    publicada: null,
    linhas: [
      linha("l1", "ing-levain", "Levain (fermento natural líquido)", "Preparos da casa", 100, { componente: true, funcao: "inoculo" }),
      linha("l2", "ing-int", "Farinha de trigo integral", "Farinhas", 50, { custo: 0.35 }),
      linha("l3", "ing-cent", "Farinha de centeio", "Farinhas", 50, { custo: 1.1 }),
      linha("l4", "ing-t0", "Farinha de trigo tipo 0", "Farinhas", 100, { custo: 3.79 }),
      linha("l5", "ing-agua", "Água", "Líquidos", 100),
      linha("l6", "ing-mel", "Mel", "Açúcares e mel", 20),
    ],
    total_massa_g: 420,
    custo_total: 5.24,
    custo_parcial: true,
    linhas_sem_custo: 2,
    custo_por_unidade: null,
    verificacoes: { pendencias: [], avisos: [] },
    perdas: {
      formato: null,
      peso_final_g: null,
      unidades_desejadas: null,
      processo: PERDA(5),
      coccao: PERDA(null),
      peso_cru_g: null,
      unidades: null,
      massa_necessaria_g: null,
    },
    modo_rendimento: "massa",
    rendimento_massa: { massa_g: 420, processo_pct: 5, rende_g: 399, reserva_g: 100, disponivel_g: 299, custo_por_kg: 17.52 },
    hidratacao: { farinha_g: 262.5, agua_g: 131.25, percentual: 50 },
  } as unknown as ReceitaFicha;
}

function renderizar() {
  return render(
    <GestaoContext.Provider
      value={{ sessao: SESSAO, search: "", navegar: vi.fn(), atualizarFluxo: () => {}, pode: () => true, definirTitulo: () => {} }}
    >
      <EditorReceita produtoId="p1" />
    </GestaoContext.Provider>,
  );
}

async function abrirAba(usuario: ReturnType<typeof userEvent.setup>, nome: string) {
  const abas = await screen.findByRole("group", { name: "Partes da receita" });
  await usuario.click(within(abas).getByRole("button", { name: nome }));
}

beforeEach(() => {
  vi.mocked(detalheReceita).mockResolvedValue(levain());
  vi.mocked(salvarReceita).mockImplementation(async () => levain());
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

afterEach(() => {
  vi.clearAllMocks();
});

describe("rendimento em peso dos preparos da casa (GESTAO-018)", () => {
  it("a aba Rendimento do Levain mostra rende, reserva, disponível e custo por kg, sem campos de pão", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await abrirAba(usuario, "Rendimento");
    expect(screen.queryByText("Formato")).not.toBeInTheDocument();
    expect(screen.queryByText("Peso final por unidade (g)")).not.toBeInTheDocument();
    expect(screen.queryByText("Unidades desejadas")).not.toBeInTheDocument();
    expect(screen.queryByText("Perda de cocção")).not.toBeInTheDocument();
    expect(screen.getByText("Perda de processo")).toBeInTheDocument();
    const cartao = (titulo: string) => screen.getByRole("heading", { name: titulo }).closest("article") as HTMLElement;
    expect(cartao("Rende")).toHaveTextContent("399 g");
    expect(cartao("Rende")).toHaveTextContent("de 420 g de massa");
    expect(cartao("Reserva do inóculo")).toHaveTextContent("100 g");
    expect(cartao("Disponível para usar")).toHaveTextContent("299 g");
    expect(cartao("Custo por kg")).toHaveTextContent(/R\$\s?17,52 parcial/);
  });

  it("o Revisar mostra o rendimento em gramas, a hidratação e não pede fermento", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await abrirAba(usuario, "Revisar");
    const fato = (titulo: string) => screen.getByText(titulo, { selector: "dt" }).parentElement as HTMLElement;
    expect(fato("Rendimento")).toHaveTextContent("399 g");
    expect(fato("Hidratação")).toHaveTextContent("50 %");
    expect(fato("Hidratação")).toHaveTextContent("131 g de água para 263 g de farinha");
    expect(fato("Custo por kg")).toHaveTextContent(/R\$\s?17,52 parcial/);
    expect(screen.queryByText("Falta o fermento.")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Publicar mesmo assim, sem fermento")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publicar versão 1" })).toBeEnabled();
  });

  it("ao gravar, não manda peso por peça, formato, unidades nem cocção", async () => {
    const usuario = userEvent.setup();
    renderizar();
    const campo = await screen.findByRole("textbox", { name: "Quantidade, linha 6" });
    await usuario.clear(campo);
    await usuario.type(campo, "25");
    await waitFor(() => expect(salvarReceita).toHaveBeenCalledTimes(1), { timeout: 3000 });
    const corpo = vi.mocked(salvarReceita).mock.calls[0][1] as Record<string, unknown>;
    expect(corpo.peso_unidade_g).toBeNull();
    expect(corpo.formato).toBeNull();
    expect(corpo.unidades_desejadas).toBeNull();
    expect(corpo).not.toHaveProperty("coccao");
  }, 8000);

  it("receita de pão (modo unidades) continua com a tela de peças", async () => {
    const usuario = userEvent.setup();
    vi.mocked(detalheReceita).mockResolvedValue({ ...levain(), cultura_viva: false, modo_rendimento: "unidades", rendimento_massa: null });
    renderizar();
    await abrirAba(usuario, "Rendimento");
    expect(screen.getByText("Formato")).toBeInTheDocument();
    expect(screen.getByText("Perda de cocção")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Reserva do inóculo" })).not.toBeInTheDocument();
  });
});
