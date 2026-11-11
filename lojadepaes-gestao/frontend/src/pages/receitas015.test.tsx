import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GestaoContext } from "../contexto";
import { ApiError, type ReceitaFicha, type SessaoInfo } from "../lib/api";
import { podeSair } from "../lib/guardaSaida";
import { Comanda } from "./Comanda";
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
    carregarComanda: vi.fn(),
    imprimirComanda: vi.fn(),
  };
});

import { carregarComanda, detalheReceita, salvarReceita } from "../lib/api";

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

function ficha(quantidade = 100): ReceitaFicha {
  return {
    id: "r1",
    produto_id: "p1",
    produto: "Levain",
    cultura_viva: true,
    ingrediente_id: "ing-levain",
    situacao: "rascunho",
    versao: 1,
    rendimento_quantidade: 1,
    rendimento_unidade: "un",
    rendimento: "1 un",
    peso_unidade_g: null,
    perda_percentual: 0,
    modo_fazer: [],
    selos: ["rascunho"],
    publicada: null,
    linhas: [
      {
        id: "l1",
        ingrediente_id: "ing-farinha",
        nome: "Farinha de trigo",
        categoria: "Farinhas",
        componente: false,
        unidade_base: "g",
        texto: null,
        a_decidir: false,
        quantidade,
        unidade: "g",
        ordem: 1,
        observacao: null,
        percentual_padeiro: 100,
        custo: 1,
        origem: "manual",
        faixa_min: null,
        faixa_max: null,
        funcao: "massa",
      },
    ],
    total_massa_g: quantidade,
    custo_total: 1,
    custo_parcial: false,
    linhas_sem_custo: 0,
    custo_por_unidade: 1,
  };
}

function renderizar() {
  return render(
    <GestaoContext.Provider
      value={{
        sessao: SESSAO,
        search: "",
        navegar: vi.fn(),
        atualizarFluxo: () => {},
        pode: () => true,
        definirTitulo: () => {},
      }}
    >
      <EditorReceita produtoId="p1" />
    </GestaoContext.Provider>,
  );
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

afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe("autossalvamento da receita", () => {
  it("grava a linha depois da pausa e o recarregar mostra o valor", async () => {
    const usuario = userEvent.setup();
    let atual = ficha();
    vi.mocked(detalheReceita).mockImplementation(async () => atual);
    vi.mocked(salvarReceita).mockImplementation(async (_id, corpo) => {
      atual = {
        ...atual,
        linhas: atual.linhas.map((linha, i) => ({ ...linha, quantidade: corpo.linhas[i]?.quantidade ?? linha.quantidade })),
      };
      return atual;
    });
    const tela = renderizar();
    const campo = await screen.findByRole("textbox", { name: "Quantidade, linha 1" });
    await usuario.clear(campo);
    await usuario.type(campo, "180");
    await waitFor(() => expect(salvarReceita).toHaveBeenCalled(), { timeout: 3000 });
    const enviado = vi.mocked(salvarReceita).mock.calls.at(-1)?.[1];
    expect(enviado?.linhas[0]?.quantidade).toBe(180);
    tela.unmount();
    renderizar();
    expect(await screen.findByRole("textbox", { name: "Quantidade, linha 1" })).toHaveValue("180");
  }, 8000);

  it("mostra o 422 na linha e o indicador de não salva", async () => {
    const usuario = userEvent.setup();
    vi.mocked(detalheReceita).mockResolvedValue(ficha());
    vi.mocked(salvarReceita).mockRejectedValue(new ApiError(422, "Levain usa Levain.", "ciclo_receita", { linha: 1 }));
    renderizar();
    const campo = await screen.findByRole("textbox", { name: "Quantidade, linha 1" });
    await usuario.clear(campo);
    await usuario.type(campo, "90");
    campo.blur();
    expect(await screen.findByRole("alert")).toHaveTextContent("Levain usa Levain.");
    expect(await screen.findByRole("status")).toHaveTextContent("não salva");
  });

  it("pede confirmação ao sair com mudança pendente", async () => {
    const usuario = userEvent.setup();
    vi.mocked(detalheReceita).mockResolvedValue(ficha());
    vi.mocked(salvarReceita).mockImplementation(() => new Promise(() => undefined));
    renderizar();
    const campo = await screen.findByRole("textbox", { name: "Quantidade, linha 1" });
    await usuario.type(campo, "2");
    await waitFor(() => expect(screen.getByRole("button", { name: "Salvar rascunho" })).toBeEnabled());
    const confirmar = vi.spyOn(window, "confirm").mockReturnValue(false);
    expect(podeSair()).toBe(false);
    expect(confirmar).toHaveBeenCalledWith("Há mudanças não salvas. Sair mesmo assim?");
  });

  it("abre a observação na tabela e grava o texto", async () => {
    const usuario = userEvent.setup();
    vi.mocked(detalheReceita).mockResolvedValue(ficha());
    vi.mocked(salvarReceita).mockImplementation(async () => ficha());
    renderizar();
    await screen.findByRole("table", { name: "Ingredientes da receita" });
    await usuario.click(await screen.findByRole("button", { name: "Mais ações da linha 1" }));
    await usuario.click(screen.getByRole("menuitem", { name: "Observação" }));
    const obs = screen.getByRole("textbox", { name: "Observação" });
    await usuario.type(obs, "peneirar");
    await waitFor(
      () => {
        const enviado = vi.mocked(salvarReceita).mock.calls.at(-1)?.[1];
        expect(enviado?.linhas[0]?.observacao).toBe("peneirar");
      },
      { timeout: 3000 },
    );
  });
});

describe("comanda", () => {
  it("mostra a observação e o inóculo", async () => {
    vi.mocked(carregarComanda).mockResolvedValue({
      data: "2026-11-11",
      fornada: { id: "f", nome: "Manhã", horario: "05:00", ordem: 1, ativa: true },
      numero: 1,
      via: 0,
      via_rotulo: null,
      impressa_em: null,
      impressa_por: null,
      produtos: [
        {
          ordem_id: "o",
          produto: "Levain",
          unidades: 1,
          pecas: null,
          massa: null,
          sem_receita: false,
          aviso: null,
          modo_fazer: [],
          observacao: null,
          linhas: [
            {
              nome: "Farinha de trigo",
              funcao: "massa",
              funcao_rotulo: "Massa",
              quantidade_g: "100",
              texto: "100 g",
              componente: false,
              filhos: [],
              observacao: "peneirar",
            },
            {
              nome: "Inóculo: 50 g de Levain do preparo anterior",
              funcao: "inoculo",
              funcao_rotulo: "Inóculo",
              quantidade_g: "50",
              texto: "50 g",
              componente: false,
              filhos: [],
              observacao: null,
            },
          ],
        },
      ],
      pesagem: [],
    });
    render(
      <GestaoContext.Provider
        value={{
          sessao: SESSAO,
          search: "?data=2026-11-11&fornada=f",
          navegar: vi.fn(),
          atualizarFluxo: () => {},
          pode: () => true,
        }}
      >
        <Comanda />
      </GestaoContext.Provider>,
    );
    expect(await screen.findByText("peneirar")).toBeInTheDocument();
    expect(screen.getByText("Inóculo: 50 g de Levain do preparo anterior")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Inóculo" })).toBeInTheDocument();
  });
});
