import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

function renderizarComDesmontar(ui: React.ReactElement) {
  const navegar = vi.fn();
  const r = render(
    <GestaoContext.Provider
      value={{ sessao: SESSAO, search: "", navegar, atualizarFluxo: () => {}, pode: (a) => SESSAO.permissoes.includes(a) }}
    >
      {ui}
    </GestaoContext.Provider>,
  );
  return { unmount: r.unmount };
}

function ok(corpo: unknown, status = 200) {
  return { ok: status < 300, status, json: async () => corpo };
}

beforeEach(() => {
  window.localStorage.clear(); // o modo do custo fica lembrado: cada teste começa do padrão (valor pago)
  vi.stubGlobal("matchMedia", (q: string) => ({ matches: false, media: q, addEventListener: () => {}, removeEventListener: () => {} }));
});
afterEach(() => vi.unstubAllGlobals());

const CATALOGO: Catalogo = {
  ingredientes: [{ id: "ing-1", nome: "Farinha de trigo", unidade_base: "g", categoria: "Farinhas", apelidos: ["farinha 00"] }],
  itens: [
    {
      id: "item-1",
      nome: "Farinha de trigo 25 kg",
      marca: "Dona Benta",
      unidade_controle: "massa",
      conteudo_embalagem: null,
      ingrediente_id: "ing-1",
      ingrediente: "Farinha de trigo",
      ingrediente_categoria: "Farinhas",
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
    expect(screen.getByRole("columnheader", { name: "Entrada" })).toBeInTheDocument();
    expect(linha).toHaveTextContent("02/11/2026");
    expect(linha).toHaveTextContent("Pendente");
    expect(linha).not.toHaveTextContent("Completa");
    expect(linha).toHaveTextContent("(parcial)");
    expect(linha.querySelector(".col-itens")).toHaveTextContent("2");
    await userEvent.click(linha);
    const regiao = await screen.findByRole("region", { name: "Itens desta entrada" });
    expect(await within(regiao).findByText("25 kg")).toBeInTheDocument();
    expect(within(regiao).getByText("falta a validade")).toBeInTheDocument();
    await userEvent.click(within(regiao).getByRole("button", { name: "Ações de Farinha de trigo 25 kg" }));
    expect(within(regiao).getByRole("menuitem", { name: "Informar validade" })).toBeInTheDocument();
    await userEvent.click(within(regiao).getByRole("button", { name: "Ver detalhes" }));
    const painel = await screen.findByRole("dialog", { name: "Entrada de 02/11/2026" });
    expect(within(painel).getByText("falta a validade")).toBeInTheDocument();
    await userEvent.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });
});

describe("Entrada sem nota", () => {
  const FARINHA_BUSCA = {
    id: "ing-1",
    nome: "Farinha de trigo",
    categoria: "Farinhas",
    unidade_base: "g",
    apelidos: ["farinha 00"],
    saldo: 25000,
    itens: 1,
  };
  const SUGESTAO_FARINHA = {
    origem: "ingrediente",
    nivel: 2,
    motivo: "O nome do item traz “Farinha de trigo”",
    travado: false,
    destaque: true,
    ingrediente: FARINHA_BUSCA,
    catalogo: null,
  };
  /** Dois candidatos próximos: o servidor não tem certeza e nada vem em destaque. */
  const SUGESTAO_SEM_CERTEZA = [
    { ...SUGESTAO_FARINHA, nivel: 4, destaque: false, motivo: "Parecido com o nome do item" },
    {
      ...SUGESTAO_FARINHA,
      nivel: 4,
      destaque: false,
      motivo: "Parecido com o nome do item",
      ingrediente: { ...FARINHA_BUSCA, id: "ing-2", nome: "Farinha integral" },
    },
  ];
  const FERMENTO_CATALOGO = {
    id: "cat-1",
    nome: "Fermento biológico seco",
    categoria: "Fermentos",
    unidade_base: "g",
    apelidos: ["lievito"],
  };

  /** O servidor de mentira: sugere pelo item, busca e exige ingrediente escolhido (como o de verdade). */
  function servirComBusca(
    corpos: { url: string; metodo: string; corpo: Record<string, unknown> }[] = [],
    sugestoes: unknown[] = [SUGESTAO_FARINHA],
    doCatalogo: unknown[] = [],
  ) {
    const fetchMock = vi.fn(async (url: string, init?: { method?: string; body?: string }) => {
      if (url.endsWith("/catalogo")) return ok(CATALOGO);
      if (url.includes("/ingredientes/sugestao")) {
        // o diálogo "Cadastrar novo" pede só o catálogo
        return ok({ item: "x", sugestoes: url.includes("so_catalogo=true") ? doCatalogo : sugestoes });
      }
      if (url.includes("/ingredientes/busca")) return ok({ q: "", da_padaria: [FARINHA_BUSCA], do_catalogo: [FERMENTO_CATALOGO] });
      const corpo = init?.body ? (JSON.parse(init.body) as Record<string, unknown>) : {};
      corpos.push({ url, metodo: init?.method ?? "GET", corpo });
      if (url.endsWith("/ingredientes") && init?.method === "POST") {
        return ok(
          { ...FARINHA_BUSCA, id: "ing-9", nome: corpo.nome, categoria: corpo.categoria, unidade_base: corpo.unidade_base, apelidos: corpo.apelidos },
          201,
        );
      }
      if (url.endsWith("/entradas/verificar")) {
        const linhas = corpo.linhas as { ingrediente_id?: string | null }[];
        return ok({
          linhas: linhas.map((l, i) =>
            l.ingrediente_id
              ? analise({
                  posicao: i + 1,
                  pendencias: [{ codigo: "validade_nao_informada", mensagem: "Falta a validade. A entrada fica pendente até você informar.", bloqueia: false }],
                })
              : analise({
                  posicao: i + 1,
                  a_decidir: true,
                  pendencias: [{ codigo: "sem_ingrediente", mensagem: "Escolha o ingrediente.", bloqueia: true }],
                }),
          ),
        });
      }
      if (url.endsWith("/entradas")) return ok({ id: "nova-1" }, 201);
      return ok({});
    });
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  it("a sugestão fica pendente: a linha conta 'a decidir' até a pessoa confirmar; só então grava com o ingrediente", async () => {
    const corpos: { url: string; metodo: string; corpo: Record<string, unknown> }[] = [];
    servirComBusca(corpos);
    const navegar = renderizar(<EntradaSemNota />);

    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Farinha trigo tipo 1");
    await userEvent.type(screen.getByLabelText("Quantidade, linha 1"), "5");
    await userEvent.selectOptions(screen.getByLabelText("Unidade, linha 1"), "kg");
    await userEvent.type(screen.getByLabelText("Valor pago (R$), linha 1"), "22,50");
    await userEvent.click(screen.getByRole("button", { name: "Compra sem nota" }));

    // a 1ª sugestão já aparece no campo, em destaque, mas pendente: ainda não é o ingrediente da linha
    const usar = await screen.findByRole("button", { name: /Confirmar a sugestão Farinha de trigo/ }, { timeout: 3000 });
    expect(screen.queryByRole("group", { name: "Ingrediente, linha 1" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Ingrediente, linha 1")).toHaveAttribute("placeholder", "Farinha de trigo");
    expect(screen.getByText(/Sugestão pendente: Farinha de trigo/)).toBeInTheDocument();

    const resumo = screen.getByRole("region", { name: "Resumo da entrada" });
    await waitFor(() => expect(resumo).toHaveTextContent("1 a decidir"), { timeout: 3000 });
    expect(resumo).toHaveTextContent("Para gravar: decida 1 linha");
    expect(screen.getByRole("button", { name: "Gravar entrada" })).toBeDisabled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await userEvent.click(usar);
    const chip = await screen.findByRole("group", { name: "Ingrediente, linha 1" });
    expect(chip).toHaveTextContent("Farinha de trigo");
    expect(chip).toHaveTextContent("Farinhas");
    await waitFor(() => expect(screen.getByRole("button", { name: "Gravar entrada" })).toBeEnabled(), { timeout: 3000 });
    expect(resumo).toHaveTextContent("0 a decidir");

    await userEvent.click(screen.getByRole("button", { name: "Gravar entrada" }));
    await waitFor(() => expect(navegar).toHaveBeenCalledWith("/entradas?abrir=nova-1"));
    const envio = corpos.filter((c) => c.url.endsWith("/entradas") && c.metodo === "POST").at(-1)!.corpo;
    expect(envio).toMatchObject({ tipo: "sem_nota", motivo: "compra_sem_nota", local_id: "loc-1" });
    const linha = (envio.linhas as Record<string, unknown>[])[0];
    expect(linha).toMatchObject({ item_nome: "Farinha trigo tipo 1", ingrediente_id: "ing-1", quantidade: 5, unidade: "kg", valor_pago: 22.5, custo: null });
    expect(linha).not.toHaveProperty("ingrediente_nome"); // a entrada nunca manda nome para criar ingrediente
  });

  it("Enter no campo confirma a sugestão pendente; o × volta a deixar a linha 'a decidir'", async () => {
    servirComBusca();
    renderizar(<EntradaSemNota />);
    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Farinha trigo tipo 1");
    await screen.findByRole("button", { name: /Confirmar a sugestão/ }, { timeout: 3000 });
    await userEvent.tab(); // do item para o ingrediente
    expect(screen.getByLabelText("Ingrediente, linha 1")).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    const chip = await screen.findByRole("group", { name: "Ingrediente, linha 1" });
    expect(chip).toHaveTextContent("Farinha de trigo");

    await userEvent.click(within(chip).getByRole("button", { name: "Trocar o ingrediente Farinha de trigo" }));
    expect(screen.queryByRole("group", { name: "Ingrediente, linha 1" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Ingrediente, linha 1")).toHaveFocus();
    const resumo = screen.getByRole("region", { name: "Resumo da entrada" });
    await waitFor(() => expect(resumo).toHaveTextContent("1 a decidir"), { timeout: 3000 });
  });

  it("item que já existe vem com o ingrediente travado (sem ×), a marca e a unidade", async () => {
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
    const chip = screen.getByRole("group", { name: "Ingrediente, linha 1" });
    expect(chip).toHaveTextContent("Farinha de trigo");
    expect(chip).toHaveTextContent("vem do item");
    expect(within(chip).queryByRole("button")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Marca, linha 1")).toHaveAttribute("readonly");
    const unidade = screen.getByLabelText("Unidade, linha 1");
    expect(within(unidade).queryByRole("option", { name: "L" })).not.toBeInTheDocument();
    expect(within(unidade).getByRole("option", { name: "kg" })).toBeInTheDocument();
    // sobra uma linha vazia no fim, como numa planilha
    expect(screen.getByLabelText("Item como comprado, linha 2")).toHaveValue("");
  });

  it("a busca mostra a padaria e o catálogo; escolher do catálogo abre o diálogo com os existentes ANTES dos campos", async () => {
    const corpos: { url: string; metodo: string; corpo: Record<string, unknown> }[] = [];
    servirComBusca(corpos);
    renderizar(<EntradaSemNota />);
    await userEvent.click(await screen.findByLabelText("Ingrediente, linha 1"));

    const lista = await screen.findByRole("listbox", { name: /Ingredientes/ });
    expect(await within(lista).findByText("Na sua padaria")).toBeInTheDocument();
    expect(within(lista).getByText("Farinhas")).toBeInTheDocument(); // agrupado por categoria
    expect(within(lista).getByRole("option", { name: /^Farinha de trigo/ })).toHaveTextContent("25 kg");
    expect(within(lista).getByText("Do catálogo")).toBeInTheDocument();
    expect(within(lista).getByRole("option", { name: /Fermento biológico seco/ })).toHaveTextContent("do catálogo");
    const opcoes = within(lista).getAllByRole("option");
    expect(opcoes.at(-1)).toHaveTextContent("Não encontrei, cadastrar novo");

    await userEvent.click(within(lista).getByRole("option", { name: /Fermento biológico seco/ }));
    const dialogo = await screen.findByRole("dialog", { name: "Cadastrar novo ingrediente" });
    // 1) os que já existem; 2) só depois os campos; 3) o botão de confirmar
    const titulo = within(dialogo).getByRole("heading", { name: "Estes já existem e parecem com o que você digitou" });
    const nome = within(dialogo).getByLabelText("Nome genérico");
    expect(titulo.compareDocumentPosition(nome) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(await within(dialogo).findByRole("button", { name: "Usar Farinha de trigo" }, { timeout: 3000 })).toBeInTheDocument();
    expect(nome).toHaveValue("Fermento biológico seco");
    expect(within(dialogo).getByLabelText("Categoria")).toHaveValue("Fermentos");
    expect(within(dialogo).getByLabelText("Unidade base")).toHaveValue("g");
    expect(corpos.some((c) => c.metodo === "POST" && c.url.endsWith("/ingredientes"))).toBe(false); // nada criado ainda

    await userEvent.click(within(dialogo).getByRole("button", { name: "Confirmo que não existe, cadastrar" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Cadastrar novo ingrediente" })).not.toBeInTheDocument());
    const criacao = corpos.find((c) => c.metodo === "POST" && c.url.endsWith("/ingredientes"))!;
    expect(criacao.corpo).toMatchObject({
      nome: "Fermento biológico seco",
      categoria: "Fermentos",
      unidade_base: "g",
      apelidos: ["lievito"],
      confirmado_inexistente: true,
    });
    const chip = await screen.findByRole("group", { name: "Ingrediente, linha 1" });
    expect(chip).toHaveTextContent("Fermento biológico seco");
  });

  it("'Não encontrei, cadastrar novo' leva o que foi digitado para o diálogo; 'Usar' escolhe o que já existe", async () => {
    servirComBusca();
    renderizar(<EntradaSemNota />);
    const campo = await screen.findByLabelText("Ingrediente, linha 1");
    await userEvent.type(campo, "Farinha de rosca");
    const lista = await screen.findByRole("listbox", { name: /Ingredientes/ });
    await userEvent.click(await within(lista).findByRole("option", { name: "Não encontrei, cadastrar novo" }));
    const dialogo = await screen.findByRole("dialog", { name: "Cadastrar novo ingrediente" });
    expect(within(dialogo).getByLabelText("Nome genérico")).toHaveValue("Farinha de rosca");
    // sem candidato no catálogo: a categoria NÃO vem como "Outros" por padrão; a pessoa escolhe
    expect(within(dialogo).getByLabelText("Categoria")).toHaveValue("");
    expect(within(dialogo).getByRole("button", { name: "Confirmo que não existe, cadastrar" })).toBeDisabled();
    await userEvent.click(await within(dialogo).findByRole("button", { name: "Usar Farinha de trigo" }, { timeout: 3000 }));
    const chip = await screen.findByRole("group", { name: "Ingrediente, linha 1" });
    expect(chip).toHaveTextContent("Farinha de trigo");
    expect(screen.queryByRole("dialog", { name: "Cadastrar novo ingrediente" })).not.toBeInTheDocument();
  });

  it("sem certeza (dois candidatos próximos) nada vem em destaque: 'Escolha o ingrediente' e o Enter não escolhe", async () => {
    servirComBusca([], SUGESTAO_SEM_CERTEZA);
    renderizar(<EntradaSemNota />);
    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Farinha 5 kg");
    const ver = await screen.findByRole("button", { name: /Ver as 2 sugestões/ }, { timeout: 3000 });
    const campo = screen.getByLabelText("Ingrediente, linha 1");
    expect(campo).toHaveAttribute("placeholder", "Escolha o ingrediente");
    expect(screen.queryByRole("button", { name: /Confirmar a sugestão/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/Sugestão pendente/)).not.toBeInTheDocument();
    const resumo = screen.getByRole("region", { name: "Resumo da entrada" });
    await waitFor(() => expect(resumo).toHaveTextContent("1 a decidir"), { timeout: 3000 });

    // Enter no campo (lista aberta pelo botão) não escolhe ninguém
    await userEvent.click(ver);
    const lista = await screen.findByRole("listbox", { name: /Ingredientes/ });
    expect(within(lista).queryAllByRole("option", { selected: true })).toHaveLength(0);
    await userEvent.keyboard("{Enter}");
    expect(screen.queryByRole("group", { name: "Ingrediente, linha 1" })).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // as sugestões continuam abertas, uma a uma, para a pessoa escolher
    expect(within(lista).getAllByRole("option", { name: /Farinha/ }).length).toBeGreaterThanOrEqual(2);
    await userEvent.keyboard("{ArrowDown}{Enter}");
    expect(await screen.findByRole("group", { name: "Ingrediente, linha 1" })).toHaveTextContent("Farinha de trigo");
  });

  it("'Cadastrar novo' lista o candidato do catálogo e vem com o nome e a categoria dele", async () => {
    const candidato = {
      origem: "catalogo",
      nivel: 2,
      motivo: "O nome do item traz “Fermento biológico seco” (do catálogo)",
      travado: false,
      destaque: true,
      ingrediente: null,
      catalogo: FERMENTO_CATALOGO,
    };
    const corpos: { url: string; metodo: string; corpo: Record<string, unknown> }[] = [];
    servirComBusca(corpos, [], [candidato]);
    renderizar(<EntradaSemNota />);
    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Fermento biológico seco 500 g");
    const campo = screen.getByLabelText("Ingrediente, linha 1");
    await userEvent.type(campo, "fermento");
    const lista = await screen.findByRole("listbox", { name: /Ingredientes/ });
    await userEvent.click(await within(lista).findByRole("option", { name: "Não encontrei, cadastrar novo" }));
    const dialogo = await screen.findByRole("dialog", { name: "Cadastrar novo ingrediente" });

    // nome e categoria do melhor candidato do catálogo: nunca "fermento" em minúsculas e "Outros"
    await waitFor(() => expect(within(dialogo).getByLabelText("Nome genérico")).toHaveValue("Fermento biológico seco"), { timeout: 3000 });
    expect(within(dialogo).getByLabelText("Categoria")).toHaveValue("Fermentos");
    expect(within(dialogo).getByLabelText("Unidade base")).toHaveValue("g");
    // e a lista "Estes já existem" inclui o do catálogo, com "Usar"
    const usar = await within(dialogo).findByRole("button", { name: "Usar Fermento biológico seco, do catálogo" }, { timeout: 3000 });
    expect(usar.closest("li")).toHaveTextContent("Fermento biológico seco");
    expect(usar.closest("li")).toHaveTextContent("do catálogo");
    expect(corpos.some((c) => c.metodo === "POST" && c.url.endsWith("/ingredientes"))).toBe(false);
  });

  it("o rótulo do custo acompanha a unidade (no modo preço por unidade)", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => (url.endsWith("/catalogo") ? ok(CATALOGO) : ok({ linhas: [] }))));
    renderizar(<EntradaSemNota />);
    await screen.findByLabelText("Item como comprado, linha 1");
    await userEvent.selectOptions(screen.getByLabelText("Como informar o custo"), "preco_unidade");
    const unidade = screen.getByLabelText("Unidade, linha 1");
    await userEvent.selectOptions(unidade, "emb");
    expect(screen.getByLabelText(/Custo R\$ por embalagem, linha 1/)).toBeInTheDocument();
    await userEvent.selectOptions(unidade, "l");
    expect(screen.getByLabelText(/Custo R\$ por L, linha 1/)).toBeInTheDocument();
    await userEvent.selectOptions(unidade, "g");
    expect(screen.getByLabelText(/Custo R\$ por kg, linha 1/)).toBeInTheDocument();
  });
});

describe("Entrada sem nota em tabela (1024 px ou mais)", () => {
  type LinhaEnviada = {
    item_nome?: string;
    quantidade?: number | null;
    validade?: string | null;
    sem_validade?: boolean;
    ingrediente_id?: string | null;
  };

  function larguraDeComputador(largura: "tabela" | "celular") {
    vi.stubGlobal("matchMedia", (q: string) => ({
      matches: largura === "tabela" ? q.includes("min-width: 1024px") : q.includes("max-width: 959px"),
      media: q,
      addEventListener: () => {},
      removeEventListener: () => {},
    }));
  }

  /** Uma análise que reage ao que foi digitado, como a do servidor. */
  function servir(exigirIngrediente = false) {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: { body?: string }) => {
        if (url.endsWith("/catalogo")) return ok(CATALOGO);
        if (url.endsWith("/entradas/verificar")) {
          const linhas = (JSON.parse(init!.body!) as { linhas: LinhaEnviada[] }).linhas;
          return ok({
            linhas: linhas.map((l, i) => {
              const pendencias: AnaliseLinha["pendencias"] = [];
              const decidir = exigirIngrediente && !l.ingrediente_id;
              if (decidir) pendencias.push({ codigo: "sem_ingrediente", mensagem: "Escolha o ingrediente.", bloqueia: true });
              if (!l.quantidade) pendencias.push({ codigo: "quantidade_invalida", mensagem: "Informe uma quantidade maior que zero.", bloqueia: true });
              if (!l.validade && !l.sem_validade) {
                pendencias.push({ codigo: "validade_nao_informada", mensagem: "Falta a validade. A entrada fica pendente até você informar.", bloqueia: false });
              }
              return analise({
                posicao: i + 1,
                pendencias,
                a_decidir: decidir,
                incompleta: !l.quantidade,
              });
            }),
          });
        }
        return ok({});
      }),
    );
  }

  const textoDe = (el: HTMLElement) => {
    // o cabeçalho do custo é o seletor "Valor pago ▾ | Preço por unidade": vale o que está escolhido
    const seletor = within(el).queryByRole("combobox") as HTMLSelectElement | null;
    return seletor ? `${seletor.selectedOptions[0].textContent} ▾` : (el.textContent ?? "").replace(/\s+/g, " ").trim();
  };

  it("cada item é uma linha da tabela, com as colunas na ordem da planilha e o cabeçalho fixo", async () => {
    larguraDeComputador("tabela");
    servir();
    renderizar(<EntradaSemNota />);
    const tabela = await screen.findByRole("table", { name: "Itens da entrada" });
    expect(within(tabela).getAllByRole("columnheader").map(textoDe)).toEqual([
      "Item",
      "Ingrediente",
      "Marca",
      "Qtd.",
      "Unidade",
      "Conteúdo",
      "Lote",
      "Validade / sem",
      "Valor pago ▾",
      "Ações",
    ]);
    // três linhas vazias de partida: uma linha de tabela cada, sem cartões
    expect(within(tabela).getAllByRole("row")).toHaveLength(1 + 3);
    expect(document.querySelector(".grade-cab")).toBeNull();
    expect(screen.getByRole("button", { name: "Colar da planilha" })).toBeInTheDocument();
    expect(screen.getByText(/Dica: cole de uma planilha/)).toBeInTheDocument();
  });

  it("Tab segue a ordem das colunas e Enter na última coluna vai para a linha de baixo", async () => {
    larguraDeComputador("tabela");
    servir();
    renderizar(<EntradaSemNota />);
    const item = await screen.findByLabelText("Item como comprado, linha 1");
    await userEvent.type(item, "Farinha");
    const ordem = [
      "Ingrediente, linha 1",
      "Marca, linha 1",
      "Quantidade, linha 1",
      "Unidade, linha 1",
      "Lote, linha 1",
      "Validade, linha 1",
      "Sem validade, linha 1",
      "Valor pago (R$), linha 1",
      "Mais ações da linha 1",
    ];
    await userEvent.selectOptions(screen.getByLabelText("Unidade, linha 1"), "kg");
    item.focus();
    const visitados: string[] = [];
    for (let i = 0; i < ordem.length; i += 1) {
      await userEvent.tab();
      visitados.push(document.activeElement?.getAttribute("aria-label") ?? "");
    }
    expect(visitados).toEqual(ordem);

    const custo = screen.getByLabelText("Valor pago (R$), linha 1");
    await userEvent.type(custo, "4,5{Enter}");
    expect(screen.getByLabelText("Item como comprado, linha 2")).toHaveFocus();
  });

  it("a pendência fica numa sublinha da própria linha, só quando existe (o ingrediente a decidir mora no campo)", async () => {
    larguraDeComputador("tabela");
    servir(true);
    renderizar(<EntradaSemNota />);
    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Farinha trigo tipo 1");
    await userEvent.type(screen.getByLabelText("Quantidade, linha 1"), "5");

    const aviso = await screen.findByText(/Falta a validade/, undefined, { timeout: 3000 });
    const sublinha = aviso.closest("tr")!;
    expect(sublinha).toHaveClass("linha-avisos");
    expect(sublinha.previousElementSibling).toHaveClass("linha-dados");
    // "Escolha o ingrediente" não vira texto solto: a linha só conta "a decidir"
    expect(within(sublinha).queryByText(/Escolha o ingrediente/)).toBeNull();
    expect(document.querySelectorAll(".linha-avisos")).toHaveLength(1);
  });

  it("o rodapé conta a validade em aberto, cada contador leva à primeira linha e a frase diz o que falta", async () => {
    larguraDeComputador("tabela");
    servir();
    renderizar(<EntradaSemNota />);
    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Açúcar");
    await userEvent.type(screen.getByLabelText("Quantidade, linha 1"), "2");
    await userEvent.selectOptions(screen.getByLabelText("Unidade, linha 1"), "kg");
    fireEvent.change(screen.getByLabelText("Validade, linha 1"), { target: { value: "2026-12-01" } });
    await userEvent.type(screen.getByLabelText("Item como comprado, linha 2"), "Sal");
    await userEvent.click(screen.getByRole("button", { name: "Compra sem nota" }));

    const rodape = screen.getByRole("region", { name: "Resumo da entrada" });
    await waitFor(() => expect(rodape).toHaveTextContent("1 incompleto"), { timeout: 3000 });
    expect(rodape).toHaveTextContent("1 sem validade");
    expect(rodape).toHaveTextContent("Para gravar: complete 1 linha incompleta.");

    await userEvent.click(within(rodape).getByRole("button", { name: "1 sem validade" }));
    expect(screen.getByLabelText("Validade, linha 2")).toHaveFocus();
    await userEvent.click(within(rodape).getByRole("button", { name: "1 incompleto" }));
    expect(screen.getByLabelText("Quantidade, linha 2")).toHaveFocus();

    await userEvent.type(screen.getByLabelText("Quantidade, linha 2"), "1");
    await userEvent.selectOptions(screen.getByLabelText("Unidade, linha 2"), "kg");
    await waitFor(() => expect(rodape).toHaveTextContent("0 incompletos"), { timeout: 3000 });
    expect(rodape).toHaveTextContent("1 sem validade");
    expect(rodape).toHaveTextContent("Pode gravar. A entrada fica pendente: 1 item sem validade.");
    expect(screen.getByRole("button", { name: "Gravar entrada" })).toBeEnabled();
    // sem nenhum, o contador deixa de ser botão
    await userEvent.click(screen.getByLabelText("Sem validade, linha 2"));
    await waitFor(() => expect(within(rodape).queryByRole("button", { name: /sem validade/ })).toBeNull(), { timeout: 3000 });
    expect(rodape).toHaveTextContent("0 sem validade");
  });

  it("o contador 'a decidir' leva à coluna Ingrediente", async () => {
    larguraDeComputador("tabela");
    servir(true);
    renderizar(<EntradaSemNota />);
    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 2"), "Farinha trigo tipo 1");
    await userEvent.type(screen.getByLabelText("Quantidade, linha 2"), "5");
    const rodape = screen.getByRole("region", { name: "Resumo da entrada" });
    const contador = await within(rodape).findByRole("button", { name: "1 a decidir" }, { timeout: 3000 });
    await userEvent.click(contador);
    expect(screen.getByLabelText("Ingrediente, linha 2")).toHaveFocus();
  });

  it("'Colar da planilha' abre um painel e as linhas coladas entram na tabela", async () => {
    larguraDeComputador("tabela");
    servir();
    renderizar(<EntradaSemNota />);
    await userEvent.click(await screen.findByRole("button", { name: "Colar da planilha" }));
    const painel = await screen.findByRole("dialog", { name: "Colar da planilha" });
    const adicionar = within(painel).getByRole("button", { name: "Adicionar a linha" });
    expect(adicionar).toBeDisabled();
    fireEvent.change(within(painel).getByLabelText("Linhas copiadas"), {
      target: {
        value:
          "Açúcar 5 kg\tAçúcar\tUnião\t2\tkg\t\tL1\t2026-12-01\t4,50\nSal grosso\tSal\t\t1\tkg\t\t\tsem validade\t3" +
          "\nFarinha Nita 25 kg\tFarinha 00\t\t1\tkg\t\t\tsem validade\t3",
      },
    });
    expect(within(painel).getByText(/Colar nunca cria ingrediente/)).toBeInTheDocument();
    await userEvent.click(within(painel).getByRole("button", { name: "Adicionar 3 linhas" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(screen.getByLabelText("Item como comprado, linha 1")).toHaveValue("Açúcar 5 kg");
    expect(screen.getByLabelText("Validade, linha 1")).toHaveValue("2026-12-01");
    expect(screen.getByLabelText("Item como comprado, linha 2")).toHaveValue("Sal grosso");
    expect(screen.getByLabelText("Sem validade, linha 2")).toBeChecked();
    // o ingrediente da planilha só liga quando bate exatamente com o nome ou com um apelido ("Farinha 00")
    expect(screen.getByLabelText("Ingrediente, linha 1")).toHaveValue("Açúcar"); // não existe: fica "a decidir"
    expect(screen.getByLabelText("Ingrediente, linha 2")).toHaveValue("Sal");
    expect(screen.getByRole("group", { name: "Ingrediente, linha 3" })).toHaveTextContent("Farinha de trigo");
    expect(screen.getByLabelText("Item como comprado, linha 4")).toHaveValue(""); // sobra uma linha vazia
  });

  it("o menu ⋯ duplica ou remove a linha", async () => {
    larguraDeComputador("tabela");
    servir();
    renderizar(<EntradaSemNota />);
    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Açúcar");
    await userEvent.type(screen.getByLabelText("Lote, linha 1"), "L1");
    await userEvent.type(screen.getByLabelText("Item como comprado, linha 2"), "Sal");

    await userEvent.click(screen.getByRole("button", { name: "Mais ações da linha 1" }));
    const menu = screen.getByRole("menu", { name: "Ações da linha 1" });
    await userEvent.click(within(menu).getByRole("menuitem", { name: "Duplicar a linha 1" }));
    expect(screen.getByLabelText("Item como comprado, linha 2")).toHaveValue("Açúcar");
    expect(screen.getByLabelText("Lote, linha 2")).toHaveValue(""); // o lote não se repete
    expect(screen.getByLabelText("Item como comprado, linha 3")).toHaveValue("Sal");
    expect(screen.getByLabelText("Item como comprado, linha 2")).toHaveFocus();

    await userEvent.click(screen.getByRole("button", { name: "Mais ações da linha 3" }));
    await userEvent.click(screen.getByRole("menuitem", { name: "Remover a linha 3" }));
    expect(screen.queryByDisplayValue("Sal")).not.toBeInTheDocument();
  });

  it("o celular continua como está: lista compacta, sem tabela", async () => {
    larguraDeComputador("celular");
    servir();
    renderizar(<EntradaSemNota />);
    expect(await screen.findByRole("list", { name: "Itens da entrada" })).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(document.querySelectorAll(".compacta-resumo").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByRole("button", { name: "Colar da planilha" })).toBeInTheDocument();
  });
});

describe("Entrada sem nota: valor pago (GESTAO-006)", () => {
  type Corpo = { linhas: Record<string, unknown>[] };

  /** Um servidor que faz a conta do custo como o de verdade: valor pago ÷ quantidade, ou preço por unidade ÷ conteúdo. */
  function servirCusto(verificacoes: Corpo[]) {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: { body?: string }) => {
        if (url.endsWith("/catalogo")) return ok(CATALOGO);
        if (url.includes("/ingredientes/sugestao")) return ok({ item: "x", sugestoes: [] });
        if (!url.endsWith("/entradas/verificar")) return ok({});
        const corpo = JSON.parse(init!.body!) as Corpo;
        verificacoes.push(corpo);
        return ok({
          linhas: corpo.linhas.map((l, i) => {
            const emb = l.unidade === "emb";
            const conteudo = Number(l.conteudo_embalagem ?? 0);
            const quantidade = Number(l.quantidade ?? 0);
            const baseTotal = emb ? quantidade * conteudo : l.unidade === "kg" ? quantidade * 1000 : quantidade;
            const pago = l.valor_pago as number | null | undefined;
            const preco = l.custo as number | null | undefined;
            let porBase: number | null = null;
            let modo: "valor_pago" | "preco_unidade" | null = null;
            if (pago != null && baseTotal > 0) {
              modo = "valor_pago";
              porBase = pago / baseTotal;
            } else if (preco != null) {
              modo = "preco_unidade";
              porBase = emb ? preco / conteudo : preco / 1000;
            }
            return analise({
              posicao: i + 1,
              unidade_controle: emb ? "embalagem" : "massa",
              modo_custo: modo,
              custo_unidade_base: porBase,
              custo_embalagem: emb && porBase !== null ? porBase * conteudo : null,
              valor_total: porBase !== null ? porBase * baseTotal : null,
            });
          }),
        });
      }),
    );
  }

  it("o custo é o valor pago por padrão e a linha mostra 'R$ por kg' embaixo: 0,5 kg por R$ 22,99 = R$ 45,98/kg", async () => {
    const verificacoes: Corpo[] = [];
    servirCusto(verificacoes);
    renderizar(<EntradaSemNota />);
    expect(await screen.findByLabelText("Como informar o custo")).toHaveValue("valor_pago");
    await userEvent.type(screen.getByLabelText("Item como comprado, linha 1"), "Farinha de trigo sarraceno");
    await userEvent.type(screen.getByLabelText("Quantidade, linha 1"), "0,5");
    await userEvent.selectOptions(screen.getByLabelText("Unidade, linha 1"), "kg");
    await userEvent.type(screen.getByLabelText("Valor pago (R$), linha 1"), "22,99");
    expect(await screen.findByText(/^= R\$\s*45,98\/kg$/, undefined, { timeout: 3000 })).toBeInTheDocument();
    const enviada = verificacoes.at(-1)!.linhas[0];
    expect(enviada).toMatchObject({ valor_pago: 22.99, custo: null, quantidade: 0.5, unidade: "kg" });
  });

  it("na embalagem: 1 embalagem de 500 g por R$ 22,99 = R$ 22,99/emb · R$ 45,98/kg (o rótulo diz 'embalagem')", async () => {
    servirCusto([]);
    renderizar(<EntradaSemNota />);
    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Farinha sarraceno 500 g");
    await userEvent.type(screen.getByLabelText("Quantidade, linha 1"), "1");
    const unidade = screen.getByLabelText("Unidade, linha 1");
    expect(within(unidade).getByRole("option", { name: "embalagem" })).toBeInTheDocument();
    await userEvent.selectOptions(unidade, "emb");
    await userEvent.type(screen.getByLabelText("Conteúdo da embalagem, linha 1"), "500");
    await userEvent.type(screen.getByLabelText("Valor pago (R$), linha 1"), "22,99");
    expect(await screen.findByText(/^= R\$\s*22,99\/emb · R\$\s*45,98\/kg$/, undefined, { timeout: 3000 })).toBeInTheDocument();
  });

  it("'Preço por unidade' continua funcionando, manda custo (não valor pago) e a escolha fica lembrada", async () => {
    const verificacoes: Corpo[] = [];
    servirCusto(verificacoes);
    const { unmount } = renderizarComDesmontar(<EntradaSemNota />);
    await userEvent.selectOptions(await screen.findByLabelText("Como informar o custo"), "preco_unidade");
    await userEvent.type(screen.getByLabelText("Item como comprado, linha 1"), "Farinha de trigo sarraceno");
    await userEvent.type(screen.getByLabelText("Quantidade, linha 1"), "0,5");
    await userEvent.selectOptions(screen.getByLabelText("Unidade, linha 1"), "kg");
    await userEvent.type(screen.getByLabelText("Custo R$ por kg, linha 1"), "45,98");
    expect(await screen.findByText(/^= R\$\s*45,98\/kg$/, undefined, { timeout: 3000 })).toBeInTheDocument();
    const enviada = verificacoes.at(-1)!.linhas[0];
    expect(enviada).toMatchObject({ custo: 45.98, valor_pago: null });

    unmount(); // volta à tela: a última escolha vale
    renderizar(<EntradaSemNota />);
    expect(await screen.findByLabelText("Como informar o custo")).toHaveValue("preco_unidade");
  });

  it("colar da planilha respeita o modo escolhido (a coluna de custo vale como valor pago ou como preço por unidade)", async () => {
    const verificacoes: Corpo[] = [];
    servirCusto(verificacoes);
    renderizar(<EntradaSemNota />);
    const colar = async () => {
      await userEvent.click(await screen.findByRole("button", { name: "Colar da planilha" }));
      const painel = await screen.findByRole("dialog", { name: "Colar da planilha" });
      fireEvent.change(within(painel).getByLabelText("Linhas copiadas"), {
        target: { value: "Farinha sarraceno\t\t\t0,5\tkg\t\t\tsem validade\t22,99" },
      });
      await userEvent.click(within(painel).getByRole("button", { name: "Adicionar a linha" }));
      await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    };
    await colar();
    await waitFor(() => expect(verificacoes.at(-1)?.linhas[0]).toMatchObject({ valor_pago: 22.99, custo: null }), { timeout: 3000 });
    expect(screen.getByLabelText("Valor pago (R$), linha 1")).toHaveValue("22,99");

    // trocar o modo reinterpreta o mesmo número como preço por unidade
    await userEvent.selectOptions(screen.getByLabelText("Como informar o custo"), "preco_unidade");
    await waitFor(() => expect(verificacoes.at(-1)?.linhas[0]).toMatchObject({ custo: 22.99, valor_pago: null }), { timeout: 3000 });
  });

  it("'Não sei' deixa o custo desconhecido: nada de valor pago nem custo, e o total não soma", async () => {
    const verificacoes: Corpo[] = [];
    servirCusto(verificacoes);
    renderizar(<EntradaSemNota />);
    await userEvent.type(await screen.findByLabelText("Item como comprado, linha 1"), "Farinha");
    await userEvent.type(screen.getByLabelText("Quantidade, linha 1"), "1");
    await userEvent.selectOptions(screen.getByLabelText("Unidade, linha 1"), "kg");
    await waitFor(() => expect(verificacoes.length).toBeGreaterThan(0), { timeout: 3000 });
    expect(verificacoes.at(-1)!.linhas[0]).toMatchObject({ valor_pago: null, custo: null });
    expect(screen.queryByText(/^= R\$/)).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Resumo da entrada" })).toHaveTextContent("sem custo não soma");
  });
});

describe("Ingredientes", () => {
  const lista = {
    ingredientes: [
      { id: "i1", nome: "Farinha de trigo", categoria: "Farinhas", apelidos: ["farinha 00"], unidade_base: "g", ativo: true, saldo: 25000, itens: 1, lotes: 1, vence_primeiro: "2026-11-05", vence_em_7_dias: true },
      { id: "i2", nome: "Sal", categoria: "Sal e temperos", apelidos: [], unidade_base: "g", ativo: true, saldo: 0, itens: 0, lotes: 0, vence_primeiro: null, vence_em_7_dias: false },
      { id: "i4", nome: "Açúcar", categoria: "Açúcares", apelidos: [], unidade_base: "g", ativo: true, saldo: 1000, itens: 1, lotes: 1, vence_primeiro: "2027-06-01", vence_em_7_dias: false },
    ],
    pares_parecidos: [{ a: { id: "i1", nome: "Farinha de trigo" }, b: { id: "i3", nome: "Farinha trigo" }, unidade_base: "g" }],
    categorias: [
      { nome: "Farinhas", total: 1 },
      { nome: "Sal e temperos", total: 1 },
    ],
  };
  const detalhe = {
    ...lista.ingredientes[0],
    custo_medio_base: 0.0045,
    lotes_com_custo: 1,
    lotes_com_saldo: 1,
    itens_detalhe: [{ id: "it1", nome: "Farinha de trigo 25 kg", marca: "Dona Benta", unidade_controle: "massa", conteudo_embalagem: null, saldo: 25000 }],
    lotes_detalhe: [{ id: "l1", codigo: "E20261101-01", item: "Farinha de trigo 25 kg", marca: "Dona Benta", local: "Despensa", validade: "2026-11-05", sem_validade: false, saldo: 25000, custo_unidade_base: 0.0045, custo_corrigido: true, custo_antes: 0.003, custo_depois: 0.0045 }],
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
        if (init?.method === "PATCH") return ok({ ...detalhe, categoria: "Gorduras" });
        if (url.includes("/ingredientes/busca")) return ok({ q: "", da_padaria: [], do_catalogo: [] });
        if (url.includes("/ingredientes/i1")) return ok(detalhe);
        return ok(lista);
      }),
    );
    return chamadas;
  }

  it("lista saldo e estado, avisa dos pares parecidos e abre o painel com lotes e histórico", async () => {
    servirIngredientes();
    renderizar(<Ingredientes />);
    const linha = await screen.findByRole("button", { name: /^Farinha de trigo/ });
    const farinha = linha.closest("tr")!;
    expect(farinha).toHaveTextContent("25 kg");
    expect(farinha).toHaveTextContent("Vence em 7 dias");
    expect(farinha).toHaveTextContent("Parecidos");
    const sal = screen.getByRole("button", { name: /^Sal/ }).closest("tr")!;
    expect(sal).toHaveTextContent("Sem saldo");
    // ingrediente sem nenhum item: "nenhum item", não "0 itens · 0 lotes"
    expect(sal).toHaveTextContent("nenhum item");
    expect(sal).not.toHaveTextContent("0 itens");
    expect(linha).toHaveTextContent("1 item · 1 lote");
    const acucar = screen.getByRole("button", { name: /^Açúcar/ }).closest("tr")!;
    expect(acucar).toHaveTextContent("—");
    expect(acucar).not.toHaveTextContent("Em dia");
    expect(screen.queryByText("Em dia")).not.toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Ingrediente" })).toBeInTheDocument();
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

  it("a linha expandida é uma tabela e o lote corrigido leva o selo pequeno", async () => {
    servirIngredientes();
    renderizar(<Ingredientes />);
    await screen.findByRole("button", { name: /^Farinha de trigo/ });
    await userEvent.click(screen.getByRole("button", { name: "Mostrar lotes de Farinha de trigo" }));
    const regiao = await screen.findByRole("region", { name: "Lotes de Farinha de trigo" });
    expect(within(regiao).getByRole("columnheader", { name: "Item / Lote" })).toBeInTheDocument();
    expect(within(regiao).getByRole("columnheader", { name: "Quantidade" })).toBeInTheDocument();
    expect(within(regiao).getByText("E20261101-01")).toBeInTheDocument();
    expect(within(regiao).getByText("custo corrigido")).toBeInTheDocument();
    await userEvent.click(within(regiao).getByRole("button", { name: "Ações de E20261101-01" }));
    expect(within(regiao).getByRole("menuitem", { name: "Corrigir custo" })).toBeInTheDocument();
    expect(within(regiao).getByRole("menuitem", { name: "Trocar ingrediente" })).toBeInTheDocument();
  });

  it("ajustar saldo exige motivo e manda o saldo contado na unidade base", async () => {
    const chamadas = servirIngredientes();
    renderizar(<Ingredientes />);
    await userEvent.click(await screen.findByRole("button", { name: /^Farinha de trigo/ }));
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

  it("a categoria aparece embaixo do nome e filtra a lista", async () => {
    servirIngredientes();
    const navegar = renderizar(<Ingredientes />);
    const farinha = await screen.findByRole("button", { name: /^Farinha de trigo/ });
    expect(farinha).toHaveTextContent("Farinhas");
    expect(screen.getByRole("button", { name: /^Sal/ })).toHaveTextContent("Sal e temperos");
    const filtro = screen.getByLabelText("Categoria");
    expect(within(filtro).getByRole("option", { name: "Farinhas (1)" })).toBeInTheDocument();
    await userEvent.selectOptions(filtro, "Farinhas");
    expect(navegar).toHaveBeenCalledWith("/ingredientes?categoria=Farinhas", true);
  });

  it("Novo ingrediente começa pela busca; Editar muda nome, categoria e apelidos", async () => {
    const chamadas = servirIngredientes();
    renderizar(<Ingredientes />);
    await userEvent.click(await screen.findByRole("button", { name: "Novo ingrediente" }));
    const busca = await screen.findByRole("combobox", { name: "Buscar ingrediente" });
    expect(busca).toHaveFocus();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument(); // nada de formulário antes da busca
    await userEvent.click(screen.getByRole("button", { name: "Fechar" }));
    expect(screen.queryByRole("combobox", { name: "Buscar ingrediente" })).not.toBeInTheDocument();

    await userEvent.click(await screen.findByRole("button", { name: /^Farinha de trigo/ }));
    const painel = await screen.findByRole("dialog", { name: "Farinha de trigo" });
    expect(await within(painel).findByText("Categoria")).toBeInTheDocument();
    await userEvent.click(within(painel).getByRole("button", { name: "Editar" }));
    await userEvent.selectOptions(within(painel).getByLabelText("Categoria"), "Gorduras");
    const apelidos = within(painel).getByLabelText("Apelidos");
    await userEvent.clear(apelidos);
    await userEvent.type(apelidos, "farinha 00, tipo 00");
    await userEvent.click(within(painel).getByRole("button", { name: "Salvar" }));
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "PATCH")).toBe(true));
    expect(chamadas.find((c) => c.metodo === "PATCH")!.corpo).toEqual({ categoria: "Gorduras", apelidos: ["farinha 00", "tipo 00"] });
  });
});

describe("Corrigir custo e trocar ingrediente (GESTAO-006)", () => {
  const CUSTO_LOTE = {
    id: "l1",
    codigo: "E20261102-01",
    item: "Farinha de trigo sarraceno 500 g",
    marca: "",
    ingrediente_id: "i1",
    ingrediente: "Farinha de trigo",
    unidade_base: "g",
    unidade_controle: "massa",
    conteudo_embalagem: null,
    quantidade_comprada_base: 500,
    custo_unidade_base: 0.04598,
    valor_pago_atual: 22.99,
    historico: [],
  };
  const resumoEntrada = {
    id: "e1", data: "2026-11-02", tipo: "sem_nota", motivo: "compra_sem_nota", motivo_detalhe: null,
    fornecedor: "Atacadão", itens: 1, valor: 22.99, valor_parcial: false, situacao: "completa",
  };
  const detalheEntrada = {
    ...resumoEntrada,
    observacao: null,
    local: "Despensa",
    lancada_por: "Ana",
    linhas: [
      {
        posicao: 1, item: "Farinha de trigo sarraceno 500 g", marca: "", ingrediente_id: "i1", ingrediente: "Farinha de trigo",
        quantidade: 0.5, unidade: "kg", quantidade_base: 500, unidade_base: "g", lote_id: "l1", lote: "E20261102-01",
        validade: "2026-12-01", sem_validade: false, validade_pendente: false,
        custo: null, custo_por: null, valor_pago: 22.99, modo_custo: "valor_pago", custo_unidade_base: 0.04598, valor_total: 22.99,
      },
    ],
  };

  const normaliza = (s: string | null) => (s ?? "").replace(/\s+/g, " ");

  it("no detalhe da entrada: mostra o valor pago e o custo por kg, e 'Corrigir custo' mostra antes e depois sem mexer no saldo", async () => {
    const chamadas: { url: string; metodo: string; corpo: Record<string, unknown> | null }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: { method?: string; body?: string }) => {
        chamadas.push({ url, metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(init.body) : null });
        if (url.includes("/lotes/l1/custo")) return ok(CUSTO_LOTE);
        if (url.includes("/entradas/e1")) return ok(detalheEntrada);
        return ok({ filtro: "todas", entradas: [resumoEntrada] });
      }),
    );
    renderizar(<Entradas />);
    await userEvent.click(await screen.findByRole("button", { name: /Compra sem nota · Atacadão/ }));
    const regiao = await screen.findByRole("region", { name: "Itens desta entrada" });
    expect(normaliza((await within(regiao).findByText(/pagos/)).textContent)).toMatch(/R\$ 22,99 pagos · R\$ 45,98\/kg/);

    await userEvent.click(within(regiao).getByRole("button", { name: /Ações de/ }));
    await userEvent.click(within(regiao).getByRole("menuitem", { name: "Corrigir custo" }));
    const form = await within(regiao).findByRole("form", { name: /Corrigir custo do lote E20261102-01/ });
    expect(normaliza(within(form).getByText(/Neste lote entraram/).textContent)).toContain("pagos R$ 22,99");
    const antes = within(form).getByText("Antes").nextElementSibling!;
    expect(normaliza(antes.textContent)).toBe("R$ 45,98/kg");

    const gravar = within(form).getByRole("button", { name: "Gravar correção" });
    await userEvent.type(within(form).getByLabelText("Valor pago (R$)"), "20");
    expect(normaliza(within(form).getByText("Depois").nextElementSibling!.textContent)).toBe("R$ 40,00/kg");
    expect(gravar).toBeDisabled(); // falta o motivo
    await userEvent.type(within(form).getByLabelText("Motivo (obrigatório)"), "Erro de digitação");
    expect(gravar).toBeEnabled();
    await userEvent.click(gravar);
    await waitFor(() => expect(chamadas.some((c) => c.metodo === "POST")).toBe(true));
    const envio = chamadas.find((c) => c.metodo === "POST")!;
    expect(envio.url).toContain("/lotes/l1/custo");
    expect(envio.corpo).toEqual({ valor_pago: 20, motivo: "Erro de digitação" }); // nunca quantidade
    await waitFor(() => expect(within(regiao).queryByRole("form", { name: /Corrigir custo/ })).not.toBeInTheDocument());
  });

  it("'Corrigir custo' no modo preço por unidade calcula o depois por kg e recusa valor igual ao atual", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.includes("/lotes/l1/custo")) return ok(CUSTO_LOTE);
        if (url.includes("/entradas/e1")) return ok(detalheEntrada);
        return ok({ filtro: "todas", entradas: [resumoEntrada] });
      }),
    );
    renderizar(<Entradas />);
    await userEvent.click(await screen.findByRole("button", { name: /Compra sem nota · Atacadão/ }));
    const regiao = await screen.findByRole("region", { name: "Itens desta entrada" });
    await userEvent.click(await within(regiao).findByRole("button", { name: /Ações de/ }));
    await userEvent.click(within(regiao).getByRole("menuitem", { name: "Corrigir custo" }));
    const form = await within(regiao).findByRole("form", { name: /Corrigir custo do lote/ });
    await userEvent.selectOptions(within(form).getByLabelText("Como informar"), "preco_unidade");
    await userEvent.type(within(form).getByLabelText("Preço (R$ por kg)"), "50");
    expect(normaliza(within(form).getByText("Depois").nextElementSibling!.textContent)).toBe("R$ 50,00/kg");
    await userEvent.clear(within(form).getByLabelText("Preço (R$ por kg)"));
    await userEvent.type(within(form).getByLabelText("Preço (R$ por kg)"), "45,98");
    expect(within(form).getByText(/Igual ao custo atual/)).toBeInTheDocument();
    await userEvent.type(within(form).getByLabelText("Motivo (obrigatório)"), "Conferi a nota");
    expect(within(form).getByRole("button", { name: "Gravar correção" })).toBeDisabled();
  });

  const SARRACENO = { id: "i9", nome: "Farinha de trigo sarraceno", categoria: "Farinhas", unidade_base: "g", apelidos: [], saldo: 0, itens: 0 };
  const listaIng = {
    ingredientes: [
      { id: "i1", nome: "Farinha de trigo", categoria: "Farinhas", apelidos: [], unidade_base: "g", ativo: true, saldo: 500, itens: 1, lotes: 1, vence_primeiro: null, vence_em_7_dias: false },
    ],
    pares_parecidos: [],
    categorias: [{ nome: "Farinhas", total: 1 }],
  };
  const detalheIng = {
    ...listaIng.ingredientes[0],
    custo_medio_base: 0.04598,
    lotes_com_custo: 1,
    lotes_com_saldo: 1,
    itens_detalhe: [{ id: "it1", nome: "Trigo Sarraceno", marca: "", unidade_controle: "massa", conteudo_embalagem: null, saldo: 500 }],
    lotes_detalhe: [
      { id: "l1", item_id: "it1", codigo: "E20261102-01", item: "Trigo Sarraceno", marca: "", local: "Despensa", validade: null, sem_validade: true, saldo: 500, custo_unidade_base: 0.04598 },
    ],
    movimentos: [],
    correcoes_custo: [
      { id: "c1", quando: "2026-11-03T10:00:00Z", quem: "Ana", lote: "E20261102-01", item: "Trigo Sarraceno", modo: "valor_pago", valor_pago: 22.99, custo_antes: 0.04, custo_depois: 0.04598, quantidade_base: 500, motivo: "Erro de digitação" },
    ],
    juntado_em_id: null,
  };
  const detalheSarraceno = { ...detalheIng, ...SARRACENO, nome: "Farinha de trigo sarraceno", correcoes_custo: [], itens_detalhe: detalheIng.itens_detalhe };

  it("o painel do ingrediente mostra o custo de cada lote, 'Corrigir custo' e o histórico das correções", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.includes("/lotes/l1/custo")) return ok(CUSTO_LOTE);
        if (url.includes("/ingredientes/i1")) return ok(detalheIng);
        return ok(listaIng);
      }),
    );
    renderizar(<Ingredientes />);
    await userEvent.click(await screen.findByRole("button", { name: /^Farinha de trigo/ }));
    const painel = await screen.findByRole("dialog", { name: "Farinha de trigo" });
    expect(normaliza((await within(painel).findByText(/^Custo:/)).textContent)).toContain("Custo: R$ 45,98/kg");
    const historico = within(painel).getByRole("heading", { name: "Correções de custo" }).closest("section")!;
    expect(normaliza(historico.textContent)).toContain("R$ 40,00/kg → R$ 45,98/kg");
    expect(historico).toHaveTextContent("Erro de digitação");
    expect(historico).toHaveTextContent("Ana");
    await userEvent.click(within(painel).getByRole("button", { name: "Corrigir custo do lote E20261102-01" }));
    expect(await within(painel).findByRole("form", { name: /Corrigir custo do lote E20261102-01/ })).toBeInTheDocument();
  });

  it("'Trocar ingrediente' liga o item ao ingrediente certo, com motivo, e abre o novo ingrediente", async () => {
    const chamadas: { url: string; metodo: string; corpo: Record<string, unknown> | null }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: { method?: string; body?: string }) => {
        chamadas.push({ url, metodo: init?.method ?? "GET", corpo: init?.body ? JSON.parse(init.body) : null });
        if (url.includes("/itens/it1/trocar-ingrediente")) return ok(detalheSarraceno);
        if (url.includes("/ingredientes/sugestao")) return ok({ item: "Trigo Sarraceno", sugestoes: [] });
        if (url.includes("/ingredientes/busca")) return ok({ q: "", da_padaria: [SARRACENO], do_catalogo: [] });
        if (url.includes("/ingredientes/i9")) return ok(detalheSarraceno);
        if (url.includes("/ingredientes/i1")) return ok(detalheIng);
        return ok(listaIng);
      }),
    );
    renderizar(<Ingredientes />);
    await userEvent.click(await screen.findByRole("button", { name: /^Farinha de trigo/ }));
    const painel = await screen.findByRole("dialog", { name: "Farinha de trigo" });
    await userEvent.click(await within(painel).findByRole("button", { name: "Trocar ingrediente de Trigo Sarraceno" }));
    const form = await within(painel).findByRole("form", { name: "Trocar o ingrediente de Trigo Sarraceno" });
    expect(form).toHaveTextContent("os lotes e o saldo do item vão junto");
    const enviar = within(form).getByRole("button", { name: "Trocar ingrediente" });
    expect(enviar).toBeDisabled();
    await userEvent.click(within(form).getByLabelText("Novo ingrediente do item"));
    const lista = await screen.findByRole("listbox", { name: /Ingredientes/ });
    await userEvent.click(await within(lista).findByRole("option", { name: /Farinha de trigo sarraceno/ }));
    await userEvent.type(within(form).getByLabelText("Motivo (obrigatório)"), "Cadastrado no ingrediente errado");
    expect(enviar).toBeEnabled();
    await userEvent.click(enviar);
    await waitFor(() => expect(chamadas.some((c) => c.url.includes("/itens/it1/trocar-ingrediente"))).toBe(true));
    expect(chamadas.find((c) => c.url.includes("/itens/it1/trocar-ingrediente"))!.corpo).toEqual({
      ingrediente_id: "i9",
      motivo: "Cadastrado no ingrediente errado",
    });
    expect(await screen.findByRole("dialog", { name: "Farinha de trigo sarraceno" })).toBeInTheDocument();
  });

  it("sem a permissão certa não aparecem 'Corrigir custo' nem 'Trocar ingrediente'", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url.includes("/ingredientes/i1")) return ok(detalheIng);
        return ok(listaIng);
      }),
    );
    render(
      <GestaoContext.Provider
        value={{
          sessao: { ...SESSAO, permissoes: ["ver_hoje", "ver_estoque"] },
          search: "",
          navegar: vi.fn(),
          atualizarFluxo: () => {},
          pode: (a) => ["ver_hoje", "ver_estoque"].includes(a),
        }}
      >
        <Ingredientes />
      </GestaoContext.Provider>,
    );
    await userEvent.click(await screen.findByRole("button", { name: /^Farinha de trigo/ }));
    const painel = await screen.findByRole("dialog", { name: "Farinha de trigo" });
    await within(painel).findByText(/^Custo:/);
    expect(within(painel).queryByRole("button", { name: /Corrigir custo/ })).not.toBeInTheDocument();
    expect(within(painel).queryByRole("button", { name: /Trocar ingrediente/ })).not.toBeInTheDocument();
  });
});
