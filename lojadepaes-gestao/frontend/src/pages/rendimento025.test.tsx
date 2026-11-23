import { act, render, screen, waitFor, within } from "@testing-library/react";
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
  };
});

import { detalheReceita, salvarReceita } from "../lib/api";

const SESSAO: SessaoInfo = {
  usuario: "ana", nome: "Ana", admin_plataforma: false, papel: "dono", permissoes: ["ver_estoque", "lancar"], csrf: "c",
  fuso: "America/Sao_Paulo", organizacao: null, organizacoes: [], precisa_escolher_organizacao: false,
};

const PERDA = (pct: number | null, origem: string | null, rotulo: string) => ({ percentual: pct, origem, rotulo, motivo: null });

/** O Pão Rústico Comercial do Oscar (23/11): Forma, 600 g, cocção sem referência. */
function pao(): ReceitaFicha {
  return {
    id: "r1", produto_id: "p1", produto: "Pão Rústico Comercial", cultura_viva: false, ingrediente_id: null, situacao: "rascunho", versao: 1,
    rendimento_quantidade: null, rendimento_unidade: null, rendimento: null, peso_unidade_g: 600, perda_percentual: 0, formato: "forma",
    unidades_desejadas: 1, modo_fazer: [], selos: [], publicada: null,
    linhas: [
      { id: "l1", ingrediente_id: "f", nome: "Farinha", categoria: "Farinhas", componente: false, unidade_base: "g", texto: null, a_decidir: false,
        quantidade: 400, unidade: "g", ordem: 1, observacao: null, percentual_padeiro: 100, custo: 2, origem: "manual", faixa_min: null, faixa_max: null, funcao: "massa" },
    ],
    total_massa_g: 400, custo_total: 2, custo_parcial: false, linhas_sem_custo: 0, custo_por_unidade: null,
    verificacoes: { pendencias: [], avisos: [] },
    perdas: { formato: "forma", peso_final_g: 600, unidades_desejadas: 1, processo: PERDA(3, "referencia", "referência"), coccao: PERDA(null, null, "sem referência"), peso_cru_g: null, unidades: null, massa_necessaria_g: null },
    modo_rendimento: "unidades", rendimento_massa: null, hidratacao: null,
  } as unknown as ReceitaFicha;
}

function renderizar() {
  return render(
    <GestaoContext.Provider value={{ sessao: SESSAO, search: "", navegar: vi.fn(), atualizarFluxo: () => {}, pode: () => true, definirTitulo: () => {} }}>
      <EditorReceita produtoId="p1" />
    </GestaoContext.Provider>,
  );
}

const esperar = (ms: number) => act(() => new Promise((r) => setTimeout(r, ms)));

beforeEach(() => {
  vi.mocked(detalheReceita).mockResolvedValue(pao());
  vi.mocked(salvarReceita).mockImplementation(async () => pao());
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: String(query).includes("1024"), media: query, onchange: null, addEventListener: () => undefined, removeEventListener: () => undefined,
    addListener: () => undefined, removeListener: () => undefined, dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
});
afterEach(() => vi.clearAllMocks());

async function abrir(usuario: ReturnType<typeof userEvent.setup>, aba: string) {
  const abas = await screen.findByRole("group", { name: "Partes da receita" });
  await usuario.click(within(abas).getByRole("button", { name: aba }));
}

describe("aba Rendimento não prende a pessoa (GESTAO-025)", () => {
  it("digitar a cocção sem motivo e ir para Revisar: a tela não volta sozinha para Rendimento", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await abrir(usuario, "Rendimento");
    await usuario.type(screen.getByRole("textbox", { name: "Perda de cocção" }), "14");
    await abrir(usuario, "Revisar");
    await esperar(2200);
    expect(within(screen.getByRole("group", { name: "Partes da receita" })).getByRole("button", { name: "Revisar" })).toHaveAttribute("aria-pressed", "true");
    // não tenta gravar sem o motivo (o servidor recusaria)
    expect(salvarReceita).not.toHaveBeenCalled();
  }, 10000);

  it("com o motivo, grava a cocção manual uma vez", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await abrir(usuario, "Rendimento");
    await usuario.type(screen.getByRole("textbox", { name: "Perda de cocção" }), "14");
    await usuario.type(screen.getByRole("textbox", { name: "Motivo do ajuste, Perda de cocção" }), "forma, Busbys");
    await waitFor(() => expect(salvarReceita).toHaveBeenCalled(), { timeout: 3000 });
    await esperar(300);
    const corpo = vi.mocked(salvarReceita).mock.calls.at(-1)?.[1] as { coccao?: { percentual: number; motivo: string } };
    expect(corpo.coccao).toMatchObject({ percentual: 14, motivo: "forma, Busbys" });
    expect(screen.getByRole("textbox", { name: "Perda de cocção" })).toHaveValue("14");
    expect(screen.getByRole("textbox", { name: "Motivo do ajuste, Perda de cocção" })).toHaveValue("forma, Busbys");
  }, 10000);

  it("a mensagem de falta de motivo aparece junto do campo, sem sequestrar a tela", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await abrir(usuario, "Rendimento");
    await usuario.type(screen.getByRole("textbox", { name: "Perda de cocção" }), "14");
    await esperar(2000);
    expect(screen.getByText("Diga o motivo do ajuste para gravar.")).toBeInTheDocument();
  }, 10000);

  it("a pessoa diz quantos pães a receita faz; o peso cru e o final vêm do sistema", async () => {
    const usuario = userEvent.setup();
    const calculada = {
      ...pao(),
      rendimento_quantidade: 1,
      rendimento_unidade: "un",
      total_massa_g: 720,
      perdas: { ...pao().perdas!, coccao: { percentual: 14, origem: "padrao", rotulo: "padrão da casa", motivo: null }, peso_cru_g: 698, peso_final_g: 600, unidades: 1 },
    } as unknown as ReceitaFicha;
    vi.mocked(salvarReceita).mockImplementation(async () => calculada);
    renderizar();
    await abrir(usuario, "Rendimento");
    expect(screen.queryByText("Peso final por unidade (g)")).not.toBeInTheDocument();
    const campo = screen.getByRole("textbox", { name: "A receita faz quantos pães" });
    await usuario.type(campo, "1");
    await waitFor(() => expect(salvarReceita).toHaveBeenCalled(), { timeout: 3000 });
    const corpo = vi.mocked(salvarReceita).mock.calls.at(-1)?.[1] as Record<string, unknown>;
    expect(corpo).toMatchObject({ rendimento_quantidade: 1, rendimento_unidade: "un", peso_unidade_g: null });
    await waitFor(() => expect(screen.getByText("Peças de 698 g")).toBeInTheDocument());
    const cartao = (titulo: string) => screen.getByRole("heading", { name: titulo }).closest("article") as HTMLElement;
    expect(cartao("Peso final")).toHaveTextContent("~600 g");
    expect(cartao("Massa da receita")).toHaveTextContent("720 g");
    await abrir(usuario, "Revisar");
    expect(screen.getByText("Rendimento", { selector: "dt" }).parentElement).toHaveTextContent("1 pão de ~600 g");
  }, 10000);

  it("só aceita número inteiro de pães", async () => {
    const usuario = userEvent.setup();
    renderizar();
    await abrir(usuario, "Rendimento");
    const campo = screen.getByRole("textbox", { name: "A receita faz quantos pães" });
    await usuario.type(campo, "8,5x");
    expect(campo).toHaveValue("85");
  });
});
