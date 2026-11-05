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
      value={{ sessao: SESSAO, search: "", navegar: vi.fn(), atualizarFluxo: () => {}, pode: (a) => SESSAO.permissoes.includes(a) }}
    >
      {ui}
    </GestaoContext.Provider>,
  );
}

function dialogoNaArea(nome: string) {
  const dialogo = screen.getByRole("dialog", { name: nome });
  expect(dialogo.closest(".linha-expandida")).toBeNull();
  expect(dialogo.closest(".fluxo-lista-card")).toBeNull();
  expect(getComputedStyle(dialogo).position).toBe("fixed");
  expect(getComputedStyle(dialogo).top).toBe("0px");
  return dialogo;
}

const DESTINO = {
  id: "i2",
  nome: "Farinha de trigo tipo 00",
  categoria: "Farinhas",
  unidade_base: "g",
  apelidos: [],
  saldo: 0,
  itens: 0,
};

describe("GESTAO-007C trocar ingrediente", () => {
  it("na lista de ingredientes o ⋯ do item abre o diálogo na área visível, grava e os dois saldos mudam", async () => {
    let movido = false;
    const chamadas: { url: string; metodo: string; corpo: Record<string, unknown> | null }[] = [];
    const lista = {
      ingredientes: [
        { id: "i1", nome: "Farinha de trigo tipo 0", categoria: "Farinhas", apelidos: [], unidade_base: "g", ativo: true, saldo: 4000, itens: 2, lotes: 1, vence_primeiro: null, vence_em_7_dias: false },
        { id: "i2", nome: "Farinha de trigo tipo 00", categoria: "Farinhas", apelidos: [], unidade_base: "g", ativo: true, saldo: 0, itens: 0, lotes: 0, vence_primeiro: null, vence_em_7_dias: false },
      ],
      pares_parecidos: [],
      categorias: [],
    };
    const detalhe = {
      ...lista.ingredientes[0],
      custo_medio_base: null,
      lotes_com_custo: 1,
      lotes_com_saldo: 1,
      itens_detalhe: [
        { id: "it1", nome: "Farinha de Trigo Nita 00", marca: "Nita", unidade_controle: "massa", conteudo_embalagem: null, saldo: 4000 },
        { id: "it2", nome: "Farinha comum", marca: "", unidade_controle: "massa", conteudo_embalagem: null, saldo: 0 },
      ],
      lotes_detalhe: [
        { id: "l7", item_id: "it1", codigo: "E20261103-07", item: "Farinha de Trigo Nita 00", marca: "Nita", local: "Despensa", validade: null, sem_validade: true, saldo: 4000, custo_unidade_base: 0.004 },
      ],
      movimentos: [],
      correcoes_custo: [],
      juntado_em_id: null,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: { method?: string; body?: string }) => {
        chamadas.push({ url, metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(init.body) : null });
        if (init?.method === "POST" && url.includes("/itens/it1/trocar-ingrediente")) {
          movido = true;
          return { ok: true, status: 200, json: async () => detalhe };
        }
        if (url.includes("/ingredientes/sugestao")) return { ok: true, status: 200, json: async () => ({ item: "", sugestoes: [] }) };
        if (url.includes("/ingredientes/busca")) return { ok: true, status: 200, json: async () => ({ q: "", da_padaria: [DESTINO], do_catalogo: [] }) };
        if (url.includes("/ingredientes/i1")) return { ok: true, status: 200, json: async () => detalhe };
        const saldoOrigem = movido ? 0 : 4000;
        const saldoDestino = movido ? 4000 : 0;
        return {
          ok: true,
          status: 200,
          json: async () => ({
            ...lista,
            ingredientes: [
              { ...lista.ingredientes[0], saldo: saldoOrigem },
              { ...lista.ingredientes[1], saldo: saldoDestino },
            ],
          }),
        };
      }),
    );
    renderizar(<Ingredientes />);
    await userEvent.click(await screen.findByRole("button", { name: "Mostrar lotes de Farinha de trigo tipo 0" }));
    const regiao = await screen.findByRole("region", { name: "Lotes de Farinha de trigo tipo 0" });
    await userEvent.click(within(regiao).getByRole("button", { name: "Ações do lote E20261103-07" }));
    expect(within(regiao).queryByRole("menuitem", { name: "Trocar ingrediente" })).not.toBeInTheDocument();
    expect(within(regiao).getByRole("menuitem", { name: "Corrigir custo" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await userEvent.click(within(regiao).getByRole("button", { name: "Ações de Farinha de Trigo Nita 00" }));
    await userEvent.click(within(regiao).getByRole("menuitem", { name: "Trocar ingrediente" }));
    const dialogo = dialogoNaArea("Trocar ingrediente");
    expect(dialogo).toHaveTextContent("Mover");
    expect(dialogo).toHaveTextContent("Farinha de Trigo Nita 00");
    expect(dialogo).toHaveTextContent("1 lote");
    expect(dialogo).toHaveTextContent("4 kg");
    expect(dialogo).toHaveTextContent("Farinha de trigo tipo 0");
    const form = within(dialogo).getByRole("form", { name: "Trocar o ingrediente de Farinha de Trigo Nita 00" });
    await userEvent.click(within(form).getByLabelText("Novo ingrediente do item"));
    const listaBox = await screen.findByRole("listbox", { name: /Ingredientes/ });
    await userEvent.click(await within(listaBox).findByRole("option", { name: /Farinha de trigo tipo 00/ }));
    await userEvent.type(within(form).getByLabelText("Motivo (obrigatório)"), "Estava no tipo errado");
    await userEvent.click(within(form).getByRole("button", { name: "Mover" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "POST")).toBe(true));
    expect(chamadas.find((c) => c.metodo === "POST")!.corpo).toEqual({ ingrediente_id: "i2", motivo: "Estava no tipo errado" });
    expect(await screen.findByRole("status")).toHaveTextContent("Movido para Farinha de trigo tipo 00");
    const origem = screen.getByRole("button", { name: /^Farinha de trigo tipo 0 / }).closest("tr")!;
    const destino = screen.getByRole("button", { name: /^Farinha de trigo tipo 00/ }).closest("tr")!;
    expect(origem).toHaveTextContent("0 g");
    expect(destino).toHaveTextContent("4 kg");
  });

  it("na lista de entradas o ⋯ do item abre o diálogo na área visível e grava", async () => {
    const chamadas: { url: string; metodo: string; corpo: Record<string, unknown> | null }[] = [];
    const entrada = {
      id: "e1",
      data: "2026-11-03",
      tipo: "sem_nota",
      motivo: "compra_sem_nota",
      motivo_detalhe: null,
      fornecedor: null,
      itens: 1,
      itens_nomes: ["Farinha de Trigo Nita 00"],
      ingredientes: ["Farinha de trigo tipo 0"],
      lotes: ["E20261103-07"],
      valor: 18,
      valor_parcial: false,
      situacao: "completa",
    };
    const detalhe = {
      ...entrada,
      observacao: null,
      local: "Despensa",
      lancada_por: "Ana",
      linhas: [
        {
          posicao: 1,
          item_id: "it1",
          item: "Farinha de Trigo Nita 00",
          marca: "Nita",
          ingrediente_id: "i1",
          ingrediente: "Farinha de trigo tipo 0",
          quantidade: 4,
          unidade: "kg",
          quantidade_base: 4000,
          unidade_base: "g",
          lote_id: "l7",
          lote: "E20261103-07",
          validade: null,
          sem_validade: true,
          validade_pendente: false,
          custo: null,
          custo_por: null,
          valor_pago: 18,
          modo_custo: "valor_pago",
          custo_unidade_base: 0.004,
          valor_total: 18,
        },
      ],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: { method?: string; body?: string }) => {
        chamadas.push({ url, metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(init.body) : null });
        if (init?.method === "POST" && url.includes("/itens/it1/trocar-ingrediente")) {
          return { ok: true, status: 200, json: async () => ({ id: "i2", nome: "Farinha de trigo tipo 00" }) };
        }
        if (url.includes("/ingredientes/sugestao")) return { ok: true, status: 200, json: async () => ({ item: "", sugestoes: [] }) };
        if (url.includes("/ingredientes/busca")) return { ok: true, status: 200, json: async () => ({ q: "", da_padaria: [DESTINO], do_catalogo: [] }) };
        if (url.includes("/entradas/e1")) return { ok: true, status: 200, json: async () => detalhe };
        return { ok: true, status: 200, json: async () => ({ filtro: "todas", entradas: [entrada] }) };
      }),
    );
    renderizar(<Entradas />);
    await userEvent.click(await screen.findByRole("button", { name: /Farinha de Trigo Nita 00/ }));
    const regiao = await screen.findByRole("region", { name: "Itens desta entrada" });
    await userEvent.click(within(regiao).getByRole("button", { name: "Ações do lote E20261103-07" }));
    expect(within(regiao).queryByRole("menuitem", { name: "Trocar ingrediente" })).not.toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await userEvent.click(within(regiao).getByRole("button", { name: "Ações de Farinha de Trigo Nita 00" }));
    await userEvent.click(within(regiao).getByRole("menuitem", { name: "Trocar ingrediente" }));
    const dialogo = dialogoNaArea("Trocar ingrediente");
    const form = within(dialogo).getByRole("form", { name: "Trocar o ingrediente de Farinha de Trigo Nita 00" });
    await userEvent.click(within(form).getByLabelText("Novo ingrediente do item"));
    const listaBox = await screen.findByRole("listbox", { name: /Ingredientes/ });
    await userEvent.click(await within(listaBox).findByRole("option", { name: /Farinha de trigo tipo 00/ }));
    await userEvent.type(within(form).getByLabelText("Motivo (obrigatório)"), "Estava no tipo errado");
    await userEvent.click(within(form).getByRole("button", { name: "Mover" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "POST")).toBe(true));
    expect(chamadas.find((c) => c.metodo === "POST")!.corpo).toEqual({ ingrediente_id: "i2", motivo: "Estava no tipo errado" });
    expect(await screen.findByRole("status")).toHaveTextContent("Movido para Farinha de trigo tipo 00");
  });

  it("o juntado não aparece na busca: reativar e só então a troca grava", async () => {
    let reativado = false;
    const chamadas: { url: string; metodo: string; corpo: Record<string, unknown> | null }[] = [];
    const juntado = {
      id: "i2",
      nome: "Farinha de trigo tipo 00",
      destino_id: "i1",
      destino_nome: "Farinha de trigo tipo 0",
      juntado_em: "2026-11-03",
    };
    const lista = {
      ingredientes: [
        { id: "i1", nome: "Farinha de trigo tipo 0", categoria: "Farinhas", apelidos: [], unidade_base: "g", ativo: true, saldo: 4000, itens: 1, lotes: 1, vence_primeiro: null, vence_em_7_dias: false },
      ],
      pares_parecidos: [],
      categorias: [],
    };
    const detalhe = {
      ...lista.ingredientes[0],
      custo_medio_base: null,
      lotes_com_custo: 0,
      lotes_com_saldo: 1,
      itens_detalhe: [
        { id: "it1", nome: "Farinha de Trigo Nita 00", marca: "Nita", unidade_controle: "massa", conteudo_embalagem: null, saldo: 4000 },
      ],
      lotes_detalhe: [
        { id: "l7", item_id: "it1", codigo: "E20261103-07", item: "Farinha de Trigo Nita 00", marca: "Nita", local: "Despensa", validade: null, sem_validade: true, saldo: 4000, custo_unidade_base: 0.004 },
      ],
      movimentos: [],
      correcoes_custo: [],
      juntado_em_id: null,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: { method?: string; body?: string }) => {
        chamadas.push({ url, metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(init.body) : null });
        if (init?.method === "POST" && url.includes("/ingredientes/i2/reativar")) {
          reativado = true;
          return { ok: true, status: 200, json: async () => ({ ...DESTINO, ativo: true, juntado_em_id: null, itens_detalhe: [], movimentos: [] }) };
        }
        if (init?.method === "POST" && url.includes("/itens/it1/trocar-ingrediente")) {
          return { ok: true, status: 200, json: async () => ({ id: "i2", nome: "Farinha de trigo tipo 00" }) };
        }
        if (url.includes("/ingredientes/sugestao")) return { ok: true, status: 200, json: async () => ({ item: "", sugestoes: [] }) };
        if (url.includes("/ingredientes/busca")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({
              q: "",
              da_padaria: reativado ? [DESTINO] : [],
              do_catalogo: [],
              juntados: reativado ? [] : [juntado],
            }),
          };
        }
        if (url.includes("/ingredientes/i1")) return { ok: true, status: 200, json: async () => detalhe };
        return { ok: true, status: 200, json: async () => lista };
      }),
    );
    renderizar(<Ingredientes />);
    await userEvent.click(await screen.findByRole("button", { name: "Mostrar lotes de Farinha de trigo tipo 0" }));
    const regiao = await screen.findByRole("region", { name: "Lotes de Farinha de trigo tipo 0" });
    await userEvent.click(within(regiao).getByRole("button", { name: "Ações de Farinha de Trigo Nita 00" }));
    await userEvent.click(within(regiao).getByRole("menuitem", { name: "Trocar ingrediente" }));
    const troca = dialogoNaArea("Trocar ingrediente");
    expect(within(troca).queryByRole("option", { name: /Farinha de trigo tipo 00/ })).not.toBeInTheDocument();
    await userEvent.click(within(troca).getByRole("button", { name: /Farinha de trigo tipo 00 foi juntado a Farinha de trigo tipo 0/ }));
    const reativar = await screen.findByRole("dialog", { name: "Reativar ingrediente" });
    expect(reativar).toHaveTextContent("Farinha de trigo tipo 00");
    expect(reativar).toHaveTextContent("Farinha de trigo tipo 0");
    expect(reativar).toHaveTextContent("03/11");
    await userEvent.type(within(reativar).getByLabelText("Motivo (obrigatório)"), "Vou usar separado");
    await userEvent.click(within(reativar).getByRole("button", { name: "Reativar como ingrediente separado" }));
    await waitFor(() => expect(chamadas.some((c) => c.url.includes("/reativar"))).toBe(true));
    const form = within(troca).getByRole("form", { name: "Trocar o ingrediente de Farinha de Trigo Nita 00" });
    await userEvent.click(within(form).getByLabelText("Novo ingrediente do item"));
    const listaBox = await screen.findByRole("listbox", { name: /Ingredientes/ });
    await userEvent.click(await within(listaBox).findByRole("option", { name: /Farinha de trigo tipo 00/ }));
    await userEvent.type(within(form).getByLabelText("Motivo (obrigatório)"), "Era o tipo 00");
    await userEvent.click(within(form).getByRole("button", { name: "Mover" }));
    await waitFor(() => expect(chamadas.some((c) => c.url.includes("/trocar-ingrediente"))).toBe(true));
    expect(chamadas.find((c) => c.url.includes("/reativar"))!.corpo).toEqual({ motivo: "Vou usar separado" });
    expect(chamadas.find((c) => c.url.includes("/trocar-ingrediente"))!.corpo).toEqual({
      ingrediente_id: "i2",
      motivo: "Era o tipo 00",
    });
  });
});
