import { act, render, screen, waitFor } from "@testing-library/react";
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

import { buscarIngredientes, detalheReceita, salvarReceita } from "../lib/api";

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

const INGREDIENTES = [
  { id: "ing-farinha", nome: "Farinha de trigo", categoria: "Farinhas", unidade_base: "g", apelidos: [], saldo: 0, itens: 1 },
  { id: "ing-agua", nome: "Água", categoria: "Líquidos", unidade_base: "g", apelidos: [], saldo: 0, itens: 1 },
];

/** Levain da Boulangerie como está em produção: rascunho com 0 linhas. */
function vazia(): ReceitaFicha {
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
    linhas: [],
    total_massa_g: 0,
    custo_total: 0,
    custo_parcial: false,
    linhas_sem_custo: 0,
    custo_por_unidade: null,
  } as unknown as ReceitaFicha;
}

let servidor: ReceitaFicha;
let seq = 0;

/** Simula o backend: substitui as linhas pelas enviadas, com ids NOVOS a cada gravação (como o real). */
function servidorFake() {
  vi.mocked(detalheReceita).mockImplementation(async () => servidor);
  vi.mocked(salvarReceita).mockImplementation(async (_id, corpo) => {
    servidor = {
      ...servidor,
      linhas: corpo.linhas.map((l, i) => {
        const ing = INGREDIENTES.find((x) => x.id === l.ingrediente_id);
        return {
          id: `srv-${++seq}`,
          ingrediente_id: l.ingrediente_id,
          nome: ing?.nome ?? l.texto ?? "",
          categoria: ing?.categoria ?? null,
          componente: false,
          unidade_base: "g",
          texto: l.texto,
          a_decidir: !l.ingrediente_id,
          quantidade: l.quantidade,
          unidade: l.unidade,
          ordem: i + 1,
          observacao: l.observacao,
          percentual_padeiro: 100,
          custo: 2.5,
          origem: l.origem,
          faixa_min: null,
          faixa_max: null,
          funcao: l.funcao,
        };
      }),
    } as ReceitaFicha;
    return servidor;
  });
  vi.mocked(buscarIngredientes).mockImplementation(async (q: string) => ({
    q,
    da_padaria: INGREDIENTES.filter((i) => i.nome.toLowerCase().includes(q.toLowerCase())),
    do_catalogo: [],
    juntados: [],
  }) as never);
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

async function escolher(usuario: ReturnType<typeof userEvent.setup>, linha: number, busca: string, nome: string) {
  const campo = await screen.findByRole("combobox", { name: `Ingrediente, linha ${linha}` });
  await usuario.click(campo);
  await usuario.type(campo, busca);
  await usuario.click(await screen.findByRole("option", { name: new RegExp(nome) }));
}

const esperar = (ms: number) => act(() => new Promise((r) => setTimeout(r, ms)));

beforeEach(() => {
  seq = 0;
  servidor = vazia();
  servidorFake();
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

describe("entrada da receita com gravação automática (GESTAO-017)", () => {
  it("o ingrediente escolhido não some depois da pausa da gravação", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await escolher(usuario, 1, "Fari", "Farinha de trigo");
    await esperar(2500);
    expect(screen.getByRole("group", { name: "Ingrediente, linha 1" })).toHaveTextContent("Farinha de trigo");
    // nada enviável mudou: não grava
    expect(salvarReceita).not.toHaveBeenCalled();
  }, 10000);

  it("digitar a quantidade grava, a linha fica e o campo não perde o foco", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await escolher(usuario, 1, "Fari", "Farinha de trigo");
    const campo = screen.getByRole("textbox", { name: "Quantidade, linha 1" });
    await usuario.click(campo);
    await usuario.type(campo, "1000");
    await waitFor(() => expect(salvarReceita).toHaveBeenCalledTimes(1), { timeout: 3000 });
    await esperar(300);
    expect(vi.mocked(salvarReceita).mock.calls[0][1].linhas[0]).toMatchObject({ ingrediente_id: "ing-farinha", quantidade: 1000 });
    expect(screen.getByRole("group", { name: "Ingrediente, linha 1" })).toHaveTextContent("Farinha de trigo");
    const depois = screen.getByRole("textbox", { name: "Quantidade, linha 1" });
    expect(depois).toBe(campo);
    expect(depois).toHaveFocus();
    expect(depois).toHaveValue("1000");
  }, 10000);

  it("a linha nova (Adicionar linha) e a escolhida nela continuam depois de gravar", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await escolher(usuario, 1, "Fari", "Farinha de trigo");
    await usuario.type(screen.getByRole("textbox", { name: "Quantidade, linha 1" }), "1000");
    await waitFor(() => expect(salvarReceita).toHaveBeenCalledTimes(1), { timeout: 3000 });
    await usuario.click(screen.getByRole("button", { name: "Adicionar linha" }));
    await esperar(2500);
    await escolher(usuario, 2, "Ág", "Água");
    await esperar(2500);
    expect(screen.getByRole("group", { name: "Ingrediente, linha 1" })).toHaveTextContent("Farinha de trigo");
    expect(screen.getByRole("group", { name: "Ingrediente, linha 2" })).toHaveTextContent("Água");
    await usuario.type(screen.getByRole("textbox", { name: "Quantidade, linha 2" }), "1000");
    await waitFor(() => expect(salvarReceita).toHaveBeenCalledTimes(2), { timeout: 3000 });
    await esperar(300);
    expect(vi.mocked(salvarReceita).mock.calls[1][1].linhas).toHaveLength(2);
    expect(screen.getByRole("group", { name: "Ingrediente, linha 2" })).toHaveTextContent("Água");
    expect(screen.getByRole("textbox", { name: "Quantidade, linha 2" })).toHaveValue("1000");
  }, 15000);

  it("o que foi digitado durante a gravação não é sobrescrito pela resposta", async () => {
    const usuario = userEvent.setup();
    let soltar: () => void = () => {};
    const original = vi.mocked(salvarReceita).getMockImplementation()!;
    vi.mocked(salvarReceita).mockImplementation(
      (id, corpo) => new Promise((ok) => { soltar = () => ok(original(id, corpo)); }),
    );
    renderizar();
    await escolher(usuario, 1, "Fari", "Farinha de trigo");
    const campo = screen.getByRole("textbox", { name: "Quantidade, linha 1" });
    await usuario.type(campo, "100");
    await waitFor(() => expect(salvarReceita).toHaveBeenCalledTimes(1), { timeout: 3000 });
    await usuario.type(campo, "0"); // 1000, com a gravação de 100 ainda no ar
    await act(async () => soltar());
    await esperar(50);
    expect(campo).toHaveValue("1000");
    await waitFor(() => expect(salvarReceita).toHaveBeenCalledTimes(2), { timeout: 3000 });
    await act(async () => soltar());
    await esperar(50);
    expect(vi.mocked(salvarReceita).mock.calls[1][1].linhas[0].quantidade).toBe(1000);
    expect(campo).toHaveValue("1000");
  }, 15000);
});
