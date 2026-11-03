import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { GestaoContext } from "../contexto";
import type { AnaliseLinha, Catalogo, SessaoInfo } from "../lib/api";
import { EntradaSemNota } from "./EntradaSemNota";
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

function renderizar(ui: React.ReactElement, opcoes: { search?: string; navegar?: (p: string) => void } = {}) {
  const navegar = opcoes.navegar ?? vi.fn();
  render(
    <GestaoContext.Provider
      value={{
        sessao: SESSAO,
        search: opcoes.search ?? "",
        navegar,
        atualizarFluxo: () => {},
        pode: (a) => SESSAO.permissoes.includes(a),
      }}
    >
      {ui}
    </GestaoContext.Provider>,
  );
  return navegar;
}

function ok(corpo: unknown, status = 200) {
  return { ok: status < 300, status, json: async () => corpo };
}

beforeEach(() => {
  vi.stubGlobal("matchMedia", (q: string) => ({ matches: false, media: q, addEventListener: () => {}, removeEventListener: () => {} }));
});
afterEach(() => vi.unstubAllGlobals());

const CATALOGO: Catalogo = {
  ingredientes: [{ id: "ing-1", nome: "Farinha de trigo", unidade_base: "g" }],
  itens: [
    {
      id: "item-1",
      nome: "Farinha de trigo 25 kg",
      marca: "Dona Benta",
      unidade_controle: "massa",
      conteudo_embalagem: null,
      ingrediente_id: "ing-1",
      ingrediente: "Farinha de trigo",
      unidade_base: "g",
    },
  ],
  locais: [{ id: "loc-1", nome: "Despensa", padrao: true }],
};

function analise(sobre: Partial<AnaliseLinha>): AnaliseLinha {
  return {
    posicao: 1,
    item_existente: null,
    item_igual: null,
    item_parecidos: [],
    ingrediente_existente: null,
    ingrediente_igual: null,
    ingrediente_parecidos: [],
    unidade_controle: "massa",
    conteudo_embalagem: null,
    unidade_base: "g",
    unidades_validas: ["g", "kg"],
    custo_por: "kg",
    pendencias: [],
    a_decidir: false,
    incompleta: false,
    quantidade_base: 5000,
    valor_total: 22.5,
    ...sobre,
  };
}

describe("Entradas", () => {
  it("Nova entrada abre 'Como chegou?': com nota em breve, sem nota ativa", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ok({ filtro: "todas", entradas: [] })));
    const navegar = renderizar(<Entradas />);
    expect(await screen.findByText("Nenhuma entrada ainda.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Nova entrada" }));
    const painel = await screen.findByRole("dialog", { name: "Como chegou?" });
    for (const rotulo of ["Importar o XML", "Ler o QR Code", "Digitar a nota"]) {
      expect(within(painel).getByRole("button", { name: new RegExp(rotulo) })).toBeDisabled();
    }
    await userEvent.click(within(painel).getByRole("button", { name: "Entrada sem nota" }));
    expect(navegar).toHaveBeenCalledWith("/entradas/sem-nota");
  });

  it("lista a entrada com situação e abre o detalhe com itens e validade pendente", async () => {
    const resumo = {
      id: "e1",
      data: "2026-11-02",
      tipo: "sem_nota",
      motivo: "compra_sem_nota",
      motivo_detalhe: null,
      fornecedor: "Atacadão",
      itens: 2,
      valor: 112.5,
      valor_parcial: true,
      situacao: "pendente",
    };
    const detalhe = {
      ...resumo,
      observacao: null,
      local: "Despensa",
      lancada_por: "Ana",
      linhas: [
        {
          posicao: 1, item: "Farinha de trigo 25 kg", marca: "Dona Benta", ingrediente_id: "i1", ingrediente: "Farinha de trigo",
          quantidade: 25, unidade: "kg", quantidade_base: 25000, unidade_base: "g", lote_id: "l1", lote: "E20261102-01",
          validade: null, sem_validade: false, validade_pendente: true, custo: 4.5, custo_por: "kg", valor_total: 112.5,
        },
      ],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => (url.includes("/entradas/e1") ? ok(detalhe) : ok({ filtro: "todas", entradas: [resumo] }))),
    );
    renderizar(<Entradas />);
    const linha = await screen.findByRole("button", { name: /Compra sem nota · Atacadão/ });
    expect(linha).toHaveTextContent("02/11/2026");
    expect(linha).toHaveTextContent("2 itens");
    expect(linha).toHaveTextContent("Pendente");
    expect(linha).toHaveTextContent("(parcial)");
    await userEvent.click(linha);
    const painel = await screen.findByRole("dialog", { name: "Entrada de 02/11/2026" });
    expect(await within(painel).findByText("25 kg")).toBeInTheDocument();
    expect(within(painel).getByText("falta a validade")).toBeInTheDocument();
    expect(within(painel).getByRole("button", { name: "Informar validade" })).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});

describe("Entrada sem nota", () => {
  it("bloqueia a gravação até decidir o parecido e grava com a decisão", async () => {
    const corpos: { url: string; corpo: Record<string, unknown> }[] = [];
    const fetchMock = vi.fn(async (url: string, init?: { method?: string; body?: string }) => {
      if (url.endsWith("/catalogo")) return ok(CATALOGO);
      const corpo = init?.body ? (JSON.parse(init.body) as Record<string, unknown>) : {};
      corpos.push({ url, corpo });
      if (url.endsWith("/entradas/verificar")) {
        const linhas = corpo.linhas as { decisao_ingrediente?: string; item_nome?: string }[];
        return ok({
          linhas: linhas.map((l, i) =>
            analise({
              posicao: i + 1,
              ingrediente_parecidos: [{ id: "ing-1", nome: "Farinha de trigo", unidade_base: "g" }],
              a_decidir: l.decisao_ingrediente !== "novo",
              pendencias:
                l.decisao_ingrediente !== "novo"
                  ? [{ codigo: "ingrediente_parecido", mensagem: "Parecido com um ingrediente que já existe.", bloqueia: true }]
                  : [{ codigo: "validade_nao_informada", mensagem: "Falta a validade. A entrada fica pendente até você informar.", bloqueia: false }],
            }),
          ),
        });
      }
      if (url.endsWith("/entradas")) return ok({ id: "nova-1" }, 201);
      return ok({});
    });
    vi.stubGlobal("fetch", fetchMock);
    const navegar = renderizar(<EntradaSemNota />);

    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Farinha trigo tipo 1");
    await userEvent.type(screen.getByLabelText("Ingrediente, linha 1"), "Farinha trigo");
    await userEvent.type(screen.getByLabelText("Quantidade, linha 1"), "5");
    await userEvent.selectOptions(screen.getByLabelText("Unidade, linha 1"), "kg");
    await userEvent.type(screen.getByLabelText(/^Custo .*linha 1$/), "4,50");
    await userEvent.click(screen.getByRole("button", { name: "Compra sem nota" }));

    const grupo = await screen.findByRole("group", { name: "Ingrediente parecido, linha 1" }, { timeout: 3000 });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(); // nenhum erro solto na tela
    expect(grupo).toHaveTextContent("parecido com");
    expect(grupo).toHaveTextContent("Farinha de trigo");
    const gravar = screen.getByRole("button", { name: "Gravar entrada" });
    expect(gravar).toBeDisabled();
    const resumo = screen.getByRole("region", { name: "Resumo da entrada" });
    expect(resumo).toHaveTextContent("1 item");
    expect(resumo).toHaveTextContent("1 a decidir");
    expect(resumo).toHaveTextContent("Decida os itens parecidos.");

    await userEvent.click(within(grupo).getByRole("button", { name: "Criar novo" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Gravar entrada" })).toBeEnabled(), { timeout: 3000 });
    expect(screen.getByText(/Falta a validade/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Resumo da entrada" })).toHaveTextContent("0 a decidir");
    expect(screen.getByRole("region", { name: "Resumo da entrada" })).toHaveTextContent("R$ 22,50");

    await userEvent.click(screen.getByRole("button", { name: "Gravar entrada" }));
    await waitFor(() => expect(navegar).toHaveBeenCalledWith("/entradas?abrir=nova-1"));
    const envio = corpos.filter((c) => c.url.endsWith("/entradas")).at(-1)!.corpo;
    expect(envio).toMatchObject({ tipo: "sem_nota", motivo: "compra_sem_nota", local_id: "loc-1" });
    expect(String(envio.chave).length).toBeGreaterThanOrEqual(8);
    const linha = (envio.linhas as Record<string, unknown>[])[0];
    expect(linha).toMatchObject({
      item_nome: "Farinha trigo tipo 1",
      ingrediente_nome: "Farinha trigo",
      decisao_ingrediente: "novo",
      quantidade: 5,
      unidade: "kg",
      custo: 4.5,
    });
  });

  it("item que já existe vem com ingrediente e unidade travados", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: { body?: string }) => {
        if (url.endsWith("/catalogo")) return ok(CATALOGO);
        if (url.endsWith("/entradas/verificar")) {
          const n = (JSON.parse(init!.body!) as { linhas: unknown[] }).linhas.length;
          return ok({ linhas: Array.from({ length: n }, (_, i) => analise({ posicao: i + 1 })) });
        }
        return ok({});
      }),
    );
    renderizar(<EntradaSemNota />);
    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Farinha de trigo 25 kg — Dona Benta");
    await userEvent.tab(); // o nome é reconhecido ao sair do campo
    const ingrediente = screen.getByLabelText("Ingrediente, linha 1");
    expect(ingrediente).toHaveValue("Farinha de trigo");
    expect(ingrediente).toHaveAttribute("readonly");
    expect(screen.getByLabelText("Marca, linha 1")).toHaveAttribute("readonly");
    const unidade = screen.getByLabelText("Unidade, linha 1");
    expect(within(unidade).queryByRole("option", { name: "L" })).not.toBeInTheDocument();
    expect(within(unidade).getByRole("option", { name: "kg" })).toBeInTheDocument();
    // sobra uma linha vazia no fim, como numa planilha
    expect(screen.getByLabelText("Item como comprado, linha 2")).toHaveValue("");
  });

  it("quem digita o nome de um ingrediente que já existe não é interrompido", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => (url.endsWith("/catalogo") ? ok(CATALOGO) : ok({ linhas: [] }))));
    renderizar(<EntradaSemNota />);
    const campo = await screen.findByLabelText("Ingrediente, linha 1");
    await userEvent.type(campo, "Farinha de trigo integral");
    expect(campo).toHaveValue("Farinha de trigo integral");
    expect(campo).not.toHaveAttribute("readonly");
  });

  it("o rótulo do custo acompanha a unidade", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => (url.endsWith("/catalogo") ? ok(CATALOGO) : ok({ linhas: [] }))));
    renderizar(<EntradaSemNota />);
    await screen.findByLabelText("Item como comprado, linha 1");
    const unidade = screen.getByLabelText("Unidade, linha 1");
    await userEvent.selectOptions(unidade, "emb");
    expect(screen.getByLabelText(/Custo R\$ por embalagem, linha 1/)).toBeInTheDocument();
    await userEvent.selectOptions(unidade, "l");
    expect(screen.getByLabelText(/Custo R\$ por L, linha 1/)).toBeInTheDocument();
    await userEvent.selectOptions(unidade, "g");
    expect(screen.getByLabelText(/Custo R\$ por kg, linha 1/)).toBeInTheDocument();
  });
});

describe("Ingredientes", () => {
  const lista = {
    ingredientes: [
      { id: "i1", nome: "Farinha de trigo", unidade_base: "g", ativo: true, saldo: 25000, itens: 1, lotes: 1, vence_primeiro: "2026-11-05", vence_em_7_dias: true },
      { id: "i2", nome: "Sal", unidade_base: "g", ativo: true, saldo: 0, itens: 0, lotes: 0, vence_primeiro: null, vence_em_7_dias: false },
    ],
    pares_parecidos: [{ a: { id: "i1", nome: "Farinha de trigo" }, b: { id: "i3", nome: "Farinha trigo" }, unidade_base: "g" }],
  };
  const detalhe = {
    ...lista.ingredientes[0],
    custo_medio_base: 0.0045,
    lotes_com_custo: 1,
    lotes_com_saldo: 1,
    itens_detalhe: [{ id: "it1", nome: "Farinha de trigo 25 kg", marca: "Dona Benta", unidade_controle: "massa", conteudo_embalagem: null, saldo: 25000 }],
    lotes_detalhe: [{ id: "l1", codigo: "E20261101-01", item: "Farinha de trigo 25 kg", marca: "Dona Benta", local: "Despensa", validade: "2026-11-05", sem_validade: false, saldo: 25000, custo_unidade_base: 0.0045 }],
    movimentos: [{ id: "m1", tipo: "entrada", quando: "2026-11-01T10:00:00Z", quantidade_base: 25000, motivo: "compra_sem_nota", lote: "E20261101-01", item: "Farinha de trigo 25 kg", de: null, para: null }],
    juntado_em_id: null,
  };

  function servirIngredientes() {
    const chamadas: { url: string; metodo: string; corpo: unknown }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: { method?: string; body?: string }) => {
        chamadas.push({ url, metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(init.body) : null });
        if (url.includes("/ajustes")) return ok({ ...detalhe, saldo: 20000 }, 201);
        if (url.includes("/ingredientes/i1")) return ok(detalhe);
        return ok(lista);
      }),
    );
    return chamadas;
  }

  it("lista saldo e estado, avisa dos pares parecidos e abre o painel com lotes e histórico", async () => {
    servirIngredientes();
    renderizar(<Ingredientes />);
    const linha = await screen.findByRole("button", { name: /Farinha de trigo/ });
    expect(linha).toHaveTextContent("25 kg");
    expect(linha).toHaveTextContent("Vence em 7 dias");
    expect(screen.getByRole("button", { name: /Sal/ })).toHaveTextContent("Sem saldo");
    expect(screen.getByRole("status")).toHaveTextContent("1 par parece o mesmo ingrediente");
    expect(screen.getByRole("button", { name: "Juntar" })).toBeInTheDocument();

    await userEvent.click(linha);
    const painel = await screen.findByRole("dialog", { name: "Farinha de trigo" });
    expect(await within(painel).findByText("Lotes, o que vence primeiro no topo")).toBeInTheDocument();
    expect(within(painel).getByText("E20261101-01")).toBeInTheDocument();
    expect(within(painel).getByText("Histórico")).toBeInTheDocument();
    expect(within(painel).getByRole("button", { name: "Ajustar saldo" })).toBeInTheDocument();
    expect(within(painel).getByRole("button", { name: "Editar" })).toBeInTheDocument();
    expect(within(painel).getByRole("button", { name: "Juntar com…" })).toBeInTheDocument();
    expect(within(painel).getByText(/R\$\s*4,50 por kg/)).toBeInTheDocument();
  });

  it("ajustar saldo exige motivo e manda o saldo contado na unidade base", async () => {
    const chamadas = servirIngredientes();
    renderizar(<Ingredientes />);
    await userEvent.click(await screen.findByRole("button", { name: /Farinha de trigo/ }));
    const painel = await screen.findByRole("dialog", { name: "Farinha de trigo" });
    await userEvent.click(await within(painel).findByRole("button", { name: "Ajustar saldo" }));
    const gravar = within(painel).getByRole("button", { name: "Gravar ajuste" });
    await userEvent.type(within(painel).getByLabelText("Saldo contado"), "20");
    expect(gravar).toBeDisabled(); // falta o motivo
    await userEvent.type(within(painel).getByLabelText("Motivo (obrigatório)"), "Contagem do mês");
    expect(within(painel).getByText(/Diferença: −5 kg/)).toBeInTheDocument();
    expect(gravar).toBeEnabled();
    await userEvent.click(gravar);
    await waitFor(() => expect(chamadas.some((c) => c.url.includes("/ajustes"))).toBe(true));
    const envio = chamadas.find((c) => c.url.includes("/ajustes"))!;
    expect(envio.corpo).toEqual({ lote_id: "l1", saldo_contado_base: 20000, motivo: "Contagem do mês" });
  });

  it("Juntar nos pares parecidos oferece escolher quem fica e 'São diferentes'", async () => {
    servirIngredientes();
    renderizar(<Ingredientes />);
    await userEvent.click(await screen.findByRole("button", { name: "Juntar" }));
    const painel = await screen.findByRole("dialog", { name: "Parecem o mesmo ingrediente" });
    expect(within(painel).getByRole("radio", { name: "Farinha de trigo" })).toBeChecked();
    expect(within(painel).getByRole("radio", { name: "Farinha trigo" })).not.toBeChecked();
    expect(within(painel).getByRole("button", { name: "Juntar" })).toBeInTheDocument();
    expect(within(painel).getByRole("button", { name: "São diferentes" })).toBeInTheDocument();
  });
});
