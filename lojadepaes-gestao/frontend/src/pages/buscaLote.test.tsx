import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { GestaoContext } from "../contexto";
import type { SessaoInfo } from "../lib/api";
import { Entradas } from "./Entradas";
import { Ingredientes } from "./Ingredientes";

const SESSAO: SessaoInfo = {
  usuario: "ana",
  nome: "Ana",
  admin_plataforma: false,
  papel: "dono",
  permissoes: ["ver_hoje", "ver_estoque", "lancar", "ajustar", "juntar", "gerenciar_usuarios"],
  csrf: "c",
  fuso: "America/Sao_Paulo",
  organizacao: null,
  organizacoes: [],
  precisa_escolher_organizacao: false,
};

function renderizar(ui: React.ReactElement) {
  render(
    <GestaoContext.Provider
      value={{
        sessao: SESSAO,
        search: "",
        navegar: vi.fn(),
        atualizarFluxo: () => {},
        pode: (a) => SESSAO.permissoes.includes(a),
      }}
    >
      {ui}
    </GestaoContext.Provider>,
  );
}

const ENTRADA = {
  id: "e1",
  data: "2026-11-03",
  tipo: "sem_nota",
  motivo: "contagem",
  motivo_detalhe: null,
  fornecedor: null,
  itens: 3,
  itens_nomes: ["Fubá Orgânico", "Trigo Sarraceno", "Sal"],
  ingredientes: ["Fubá Orgânico", "Trigo Sarraceno", "Sal"],
  lotes: ["E20261103-12", "E20261103-13", "E20261103-14"],
  valor: 30,
  valor_parcial: false,
  situacao: "completa",
};

const DETALHE = {
  ...ENTRADA,
  observacao: null,
  local: "Despensa",
  lancada_por: "Ana",
  linhas: [
    {
      posicao: 1,
      item_id: "it1",
      item: "Fubá Orgânico",
      marca: "",
      ingrediente_id: "i1",
      ingrediente: "Fubá Orgânico",
      quantidade: 1,
      unidade: "kg",
      quantidade_base: 1000,
      unidade_base: "g",
      lote_id: "l12",
      lote: "E20261103-12",
      validade: "2027-01-01",
      sem_validade: false,
      validade_pendente: false,
      custo_unidade_base: 0.01,
      valor_total: 10,
      custo_corrigido: false,
    },
  ],
};

const CUSTO = {
  id: "l12",
  codigo: "E20261103-12",
  item: "Fubá Orgânico",
  marca: "",
  ingrediente_id: "i1",
  ingrediente: "Fubá Orgânico",
  unidade_base: "g",
  unidade_controle: "massa",
  conteudo_embalagem: null,
  quantidade_comprada_base: 1000,
  custo_unidade_base: 0.01,
  valor_pago_atual: 10,
  historico: [] as { motivo: string }[],
};

describe("GESTAO-007 achar o lote", () => {
  it("a linha lista os itens e os lotes, e '-12' abre essa linha com o lote em destaque", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => ({
        ok: true,
        status: 200,
        json: async () => (url.includes("/entradas/e1") ? DETALHE : { filtro: "todas", entradas: [ENTRADA] }),
      })),
    );
    renderizar(<Entradas />);
    const linha = await screen.findByRole("button", { name: /Fubá Orgânico, Trigo Sarraceno e mais 1/ });
    expect(linha).toHaveTextContent("E20261103-12 a -14");
    expect(linha).toHaveTextContent("Contagem de estoque · Sem nota");

    await userEvent.type(screen.getByLabelText("Buscar item, ingrediente ou lote"), "-12");
    const regiao = await screen.findByRole("region", { name: "Itens desta entrada" });
    const destaque = within(regiao).getByText("E20261103-12").closest("tr")!;
    expect(destaque).toHaveClass("lote-destaque");
  });

  it("'fuba' acha Fubá Orgânico e abre os lotes", async () => {
    const lista = {
      ingredientes: [
        {
          id: "i1",
          nome: "Fubá Orgânico",
          categoria: "Farinhas",
          apelidos: [],
          unidade_base: "g",
          ativo: true,
          saldo: 1000,
          itens: 1,
          itens_nomes: ["Fubá Orgânico"],
          lotes: 1,
          lotes_codigos: ["E20261103-12"],
          vence_primeiro: null,
          vence_em_7_dias: false,
        },
        {
          id: "i2",
          nome: "Sal",
          categoria: "Sal e temperos",
          apelidos: [],
          unidade_base: "g",
          ativo: true,
          saldo: 0,
          itens: 0,
          lotes: 0,
          lotes_codigos: [],
          vence_primeiro: null,
          vence_em_7_dias: false,
        },
      ],
      pares_parecidos: [],
      categorias: [],
    };
    const detalhe = {
      ...lista.ingredientes[0],
      custo_medio_base: 0.01,
      lotes_com_custo: 1,
      lotes_com_saldo: 1,
      itens_detalhe: [{ id: "it1", nome: "Fubá Orgânico", marca: "", unidade_controle: "massa", conteudo_embalagem: null, saldo: 1000 }],
      lotes_detalhe: [
        {
          id: "l12",
          item_id: "it1",
          codigo: "E20261103-12",
          item: "Fubá Orgânico",
          marca: "",
          local: "Despensa",
          validade: null,
          sem_validade: true,
          saldo: 1000,
          custo_unidade_base: 0.01,
        },
      ],
      movimentos: [],
      correcoes_custo: [],
      juntado_em_id: null,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => ({
        ok: true,
        status: 200,
        json: async () => (url.includes("/ingredientes/i1") ? detalhe : lista),
      })),
    );
    renderizar(<Ingredientes />);
    await screen.findByRole("button", { name: /^Sal/ });
    await userEvent.type(screen.getByLabelText("Buscar item, ingrediente ou lote"), "fuba");
    expect(screen.queryByRole("button", { name: /^Sal/ })).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /^Fubá Orgânico/ })).toBeInTheDocument();
    const regiao = await screen.findByRole("region", { name: "Lotes de Fubá Orgânico" });
    expect(within(regiao).getByText("E20261103-12")).toBeInTheDocument();
  });

  it("'Corrigir custo' na linha expandida grava o valor pago e o motivo, como o histórico do 006", async () => {
    const chamadas: { url: string; metodo: string; corpo: Record<string, unknown> | null }[] = [];
    let corrigido = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: { method?: string; body?: string }) => {
        chamadas.push({ url, metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(init.body) : null });
        if (init?.method === "POST" && url.includes("/lotes/l12/custo")) {
          corrigido = true;
          return {
            ok: true,
            status: 200,
            json: async () => ({
              ...CUSTO,
              custo_unidade_base: 0.02,
              historico: [{ motivo: "Achei a nota" }],
            }),
          };
        }
        if (url.includes("/lotes/l12/custo")) return { ok: true, status: 200, json: async () => CUSTO };
        if (url.includes("/entradas/e1")) {
          return {
            ok: true,
            status: 200,
            json: async () =>
              corrigido
                ? { ...DETALHE, linhas: [{ ...DETALHE.linhas[0], custo_corrigido: true, custo_antes: 0.01, custo_depois: 0.02 }] }
                : DETALHE,
          };
        }
        return { ok: true, status: 200, json: async () => ({ filtro: "todas", entradas: [ENTRADA] }) };
      }),
    );
    renderizar(<Entradas />);
    await userEvent.click(await screen.findByRole("button", { name: /Fubá Orgânico/ }));
    const regiao = await screen.findByRole("region", { name: "Itens desta entrada" });
    await userEvent.click(within(regiao).getByRole("button", { name: "Corrigir custo" }));
    const form = await within(regiao).findByRole("form", { name: /Corrigir custo do lote E20261103-12/ });
    await userEvent.type(within(form).getByLabelText("Valor pago (R$)"), "20");
    await userEvent.type(within(form).getByLabelText("Motivo (obrigatório)"), "Achei a nota");
    await userEvent.click(within(form).getByRole("button", { name: "Gravar correção" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "POST")).toBe(true));
    const envio = chamadas.find((c) => c.metodo === "POST")!;
    expect(envio.url).toContain("/lotes/l12/custo");
    expect(envio.corpo).toEqual({ valor_pago: 20, motivo: "Achei a nota" });
    expect(await within(regiao).findByText("custo corrigido")).toBeInTheDocument();
  });
});
