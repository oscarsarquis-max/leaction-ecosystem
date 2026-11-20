import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { CustosVisao, Hoje as HojeDados } from "../lib/api";
import { GestaoContext } from "../contexto";
import type { SessaoInfo } from "../lib/api";
import { dataLonga, quando } from "../lib/format";
import { Hoje } from "./Hoje";

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

function renderizar(navegar: (para: string) => void = () => {}, sessao: SessaoInfo = SESSAO) {
  return render(
    <GestaoContext.Provider
      value={{ sessao, search: "", navegar, atualizarFluxo: () => {}, pode: (a) => SESSAO.permissoes.includes(a) }}
    >
      <Hoje />
    </GestaoContext.Provider>,
  );
}

function base(sobrescrever: Partial<HojeDados> = {}): HojeDados {
  return {
    hoje: "2026-11-02",
    ate: "2026-11-15",
    dias: 14,
    fonte_loja: true,
    producao_hoje: [],
    fluxo: { etapas: [], proximo_passo: null, entradas_total: 1, entradas_pendentes: 0 },
    vence_em_7_dias: [],
    sem_saldo: [],
    compatibilidade: { ok: true, versao_loja: "e7b3c9a41d06", versao_conhecida: true, mensagem: null },
    fornadas: [],
    total_paes_fisicos: 0,
    ...sobrescrever,
  };
}

function servir(dados: HojeDados, custos: CustosVisao | null = null) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(async (url: string) => {
      if (String(url).includes("/custos")) {
        return custos ? { ok: true, status: 200, json: async () => custos } : { ok: false, status: 500, json: async () => ({}) };
      }
      return { ok: true, status: 200, json: async () => dados };
    }),
  );
}

afterEach(() => vi.unstubAllGlobals());

describe("formatação de datas", () => {
  it("não volta um dia por causa do fuso", () => {
    expect(dataLonga("2026-11-03")).toBe("terça-feira, 3 de novembro");
    expect(quando("2026-11-02", "2026-11-02")).toBe("Hoje");
    expect(quando("2026-11-02", "2026-11-03")).toBe("Amanhã");
    expect(quando("2026-11-02", "2026-11-06")).toBe("Em 4 dias");
  });
});

describe("tela Hoje", () => {
  it("mostra a demanda por fornada, com totais", async () => {
    servir(
      base({
        total_paes_fisicos: 12,
        fornadas: [
          {
            data: "2026-11-03",
            paes_fisicos: 5,
            quantidade: 3,
            unidades_pendentes: 0,
            itens: [
              {
                origem: "catalogo",
                produto_ou_massa: "Pão de Fermentação Natural",
                variante_ou_forma: "Unidade",
                receita_base: "TRAD",
                quantidade: 3,
                paes_fisicos: 5,
                linhas_unidades_pendentes: 0,
              },
            ],
          },
          {
            data: "2026-11-06",
            paes_fisicos: 7,
            quantidade: 7,
            unidades_pendentes: 0,
            itens: [
              {
                origem: "criador",
                produto_ou_massa: "Massa Integral",
                variante_ou_forma: "Bola",
                receita_base: null,
                quantidade: 7,
                paes_fisicos: 7,
                linhas_unidades_pendentes: 0,
              },
            ],
          },
        ],
      }),
    );
    renderizar();
    expect(await screen.findByRole("heading", { name: "terça-feira, 3 de novembro" })).toBeInTheDocument();
    expect(screen.getByText("Amanhã")).toBeInTheDocument();
    expect(screen.getByText("Em 4 dias")).toBeInTheDocument();
    const loja = screen.getByRole("region", { name: "Próximas fornadas da Loja" });
    expect(within(loja).getByText(/12 pães em 2 fornadas/)).toBeInTheDocument();
    expect(screen.getByText("Pão de Fermentação Natural")).toBeInTheDocument();
    expect(screen.getByText("Criador de pães")).toBeInTheDocument();
  });

  it("avisa quando há linhas sem quantidade de pães, em vez de mostrar zero em silêncio", async () => {
    servir(
      base({
        total_paes_fisicos: 2,
        fornadas: [
          {
            data: "2026-11-03",
            paes_fisicos: 2,
            quantidade: 5,
            unidades_pendentes: 1,
            itens: [
              {
                origem: "catalogo",
                produto_ou_massa: "Kit surpresa",
                variante_ou_forma: "Kit",
                receita_base: "TRAD",
                quantidade: 3,
                paes_fisicos: 3,
                linhas_unidades_pendentes: 1,
              },
            ],
          },
        ],
      }),
    );
    renderizar();
    expect(await screen.findByText("Unidades a confirmar")).toBeInTheDocument();
    expect(screen.getByText(/a confirmar/, { selector: ".hoje-pendente" })).toBeInTheDocument();
  });

  it("explica quando não há demanda", async () => {
    servir(base());
    renderizar();
    expect(await screen.findByText("Nenhuma demanda confirmada nos próximos 14 dias.")).toBeInTheDocument();
  });

  it("não inventa número quando a Loja não pôde ser lida", async () => {
    servir(
      base({
        compatibilidade: { ok: false, versao_loja: null, versao_conhecida: null, mensagem: "Não consegui ler os dados da Loja agora." },
      }),
    );
    renderizar();
    expect(await screen.findByRole("alert")).toHaveTextContent("Não consegui ler os dados da Loja agora.");
    expect(screen.queryByText("Pães confirmados")).not.toBeInTheDocument();
  });

  it("mostra erro com botão de tentar de novo quando a API falha", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({}) }));
    renderizar();
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível carregar o dia agora.");
    expect(screen.getByRole("button", { name: "Tentar de novo" })).toBeInTheDocument();
  });

  it("lista as pendências que vêm do servidor e leva para cada uma (GESTAO-020)", async () => {
    servir(
      base({
        pendencias: [
          { codigo: "produtos_sem_receita", texto: "9 produtos sem receita publicada", acao: "Ver produtos", href: "/produtos?filtro=pendentes", estado: "falta" },
          { codigo: "sem_entrada", texto: "Mel ainda sem entrada", acao: "Ver ingredientes", href: "/ingredientes", estado: "atencao" },
        ],
      }),
    );
    const navegar = vi.fn();
    renderizar(navegar);
    const bloco = (await screen.findByRole("heading", { name: "Pendências" })).closest("section")!;
    expect(within(bloco).getByText("9 produtos sem receita publicada")).toBeInTheDocument();
    expect(within(bloco).getByText("Mel ainda sem entrada")).toBeInTheDocument();
    expect(screen.queryByText("Monte a primeira receita")).not.toBeInTheDocument();
    await userEvent.click(within(bloco).getByRole("button", { name: "Ver produtos" }));
    expect(navegar).toHaveBeenCalledWith("/produtos?filtro=pendentes");
  });

  it("sem pendências, diz que o cadastro está em dia", async () => {
    servir(base({ pendencias: [] }));
    renderizar();
    expect(await screen.findByText("Nada pendente no cadastro.")).toBeInTheDocument();
  });

  it("mostra o vínculo de cada pão com o Gestão e o que vai faltar de ingrediente (GESTAO-020)", async () => {
    servir(
      base({
        total_paes_fisicos: 9,
        fornadas: [
          {
            data: "2026-11-03",
            paes_fisicos: 9,
            quantidade: 9,
            unidades_pendentes: 0,
            itens: [
              { origem: "catalogo", produto_ou_massa: "Focaccia", variante_ou_forma: "Inteira", receita_base: null, quantidade: 4, paes_fisicos: 4, linhas_unidades_pendentes: 0, vinculo: { produto_id: "p1", produto: "Focaccia Alta", receita: "publicada" } },
              { origem: "catalogo", produto_ou_massa: "Pão Sovado", variante_ou_forma: "8 un", receita_base: null, quantidade: 3, paes_fisicos: 3, linhas_unidades_pendentes: 0, vinculo: { produto_id: "p2", produto: "Pão Sovado", receita: "rascunho" } },
              { origem: "criador", produto_ou_massa: "Massa Integral", variante_ou_forma: "Bola", receita_base: null, quantidade: 2, paes_fisicos: 2, linhas_unidades_pendentes: 0, vinculo: null },
            ],
          },
        ],
        necessidade: {
          itens: [
            { ingrediente_id: "i1", ingrediente: "Farinha tipo 0", unidade_base: "g", precisa: 2400, tem: 5000, falta: 0 },
            { ingrediente_id: "i2", ingrediente: "Azeite", unidade_base: "ml", precisa: 300, tem: 120, falta: 180 },
          ],
          fora_da_conta: 5,
        },
      }),
    );
    renderizar();
    const linha = async (nome: string) => (await screen.findByText(nome, { selector: "th" })).closest("tr")!;
    expect(within(await linha("Focaccia")).getByText("Receita publicada")).toBeInTheDocument();
    expect(within(await linha("Pão Sovado")).getByText("Receita em rascunho")).toBeInTheDocument();
    expect(within(await linha("Massa Integral")).getByText("Sem vínculo")).toBeInTheDocument();
    const bloco = screen.getByRole("heading", { name: "Ingredientes para essas fornadas" }).closest("section")!;
    expect(within(bloco).getByText("1 ingrediente vai faltar.")).toBeInTheDocument();
    const linhas = within(bloco).getAllByRole("row");
    expect(linhas[1]).toHaveTextContent("Azeite");
    expect(within(linhas[1]).getByText("Falta 180 ml")).toBeInTheDocument();
    expect(within(bloco).getByText("5 pães ficaram fora da conta: sem vínculo ou sem receita publicada.")).toBeInTheDocument();
  });

  it("o aviso de versão da Loja aparece só para quem administra a plataforma", async () => {
    const dados = base({ compatibilidade: { ok: true, versao_loja: "x", versao_conhecida: false, mensagem: "A Loja mudou de versão." } });
    servir(dados);
    const primeira = renderizar();
    expect(await screen.findByText("Nenhuma demanda confirmada nos próximos 14 dias.")).toBeInTheDocument();
    expect(screen.queryByText("A Loja mudou de versão.")).not.toBeInTheDocument();
    primeira.unmount();
    servir(dados);
    renderizar(() => {}, { ...SESSAO, admin_plataforma: true });
    expect(await screen.findByText("A Loja mudou de versão.")).toBeInTheDocument();
  });

  it("mostra Vence em 7 dias e Acabou; o legado sem_saldo não aparece (água, nunca entrou)", async () => {
    servir(
      base({
        vence_em_7_dias: [
          {
            lote_id: "l1",
            ingrediente_id: "i1",
            ingrediente: "Fermento",
            item: "Fermento seco",
            codigo: "E20261101-01",
            validade: "2026-11-05",
            dias: 3,
            saldo: 1500,
            unidade_base: "g",
          },
        ],
        sem_saldo: [{ id: "i3", nome: "Água" }],
        acabaram: [{ id: "i2", nome: "Sal" }],
      }),
    );
    renderizar();
    const vence = await screen.findByRole("group", { name: "Vence em 7 dias" });
    expect(within(vence).getByText("Fermento")).toBeInTheDocument();
    expect(within(vence).getByText("1,5 kg")).toBeInTheDocument();
    const acabou = screen.getByRole("group", { name: "Acabou" });
    expect(within(acabou).getByText("Sal")).toBeInTheDocument();
    expect(screen.queryByText("Água")).not.toBeInTheDocument();
    expect(screen.queryByText("acabou")).not.toBeInTheDocument();
  });

  it("organização que não é a fonte da Loja não vê a demanda", async () => {
    servir(base({ fonte_loja: false }));
    renderizar();
    expect(await screen.findByText("Nada pendente no cadastro.")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Próximas fornadas da Loja" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Período da Loja")).not.toBeInTheDocument();
  });

  it("o painel mostra os números do dia e cada um leva à sua área (GESTAO-020)", async () => {
    servir(
      base({
        total_paes_fisicos: 26,
        producao_hoje: [{ fornada_id: "f1", fornada: "Manhã", horario: "05:00", unidades: 12, ordens: 2, pedido_mudou: false }],
        indicadores: { receitas_publicadas: 1, produtos_produzidos: 10, entradas_mes_qtd: 6, entradas_mes_valor: 412.37 },
        necessidade: { itens: [{ ingrediente_id: "i1", ingrediente: "Farinha", unidade_base: "g", precisa: 6800, tem: 5000, falta: 1800 }], fora_da_conta: 0 },
      }),
    );
    const navegar = vi.fn();
    renderizar(navegar);
    const numeros = await screen.findByRole("region", { name: "Números do dia" });
    expect(within(numeros).getByRole("button", { name: /Produção de hoje\s*12/ })).toBeInTheDocument();
    expect(within(numeros).getByRole("button", { name: /Confirmados na Loja\s*26/ })).toBeInTheDocument();
    expect(within(numeros).getByRole("button", { name: /Ingredientes em falta\s*1/ })).toBeInTheDocument();
    expect(within(numeros).getByRole("button", { name: /Entradas no mês\s*R\$\s?412,37/ })).toBeInTheDocument();
    await userEvent.click(within(numeros).getByRole("button", { name: /Receitas publicadas\s*1 de 10/ }));
    expect(navegar).toHaveBeenCalledWith("/receitas");
  });

  it("o gráfico da demanda leva ao dia da produção, e o de resultado ordena do pior para o melhor", async () => {
    const produto = (id: string, nome: string, resultado: number) => ({
      produto_id: id, nome, familia_id: null, familia: null, receita_publicada: true, massa_g: 400, custo_variavel: 5, custo_parcial: false,
      rateio: 2, custo_total: 7, regra_propria: null, regra: null, regra_origem: null, preco_sugerido: null, preco_manual: null, preco_proprio: null,
      loja: [{ variante: "Unidade", unidades: 1, preco: 7 + resultado, preco_por_unidade: 7 + resultado, mc: null, mc_pct: null, markup: null, resultado }],
    });
    servir(
      base({
        total_paes_fisicos: 9,
        fornadas: [{ data: "2026-11-03", paes_fisicos: 9, quantidade: 9, unidades_pendentes: 0, itens: [] }],
      }),
      {
        parametros: { massa_mensal_kg: 600, regra: null, custo_fixo_total: 3000, custo_fixo_por_kg: 5 },
        custos_fixos: [],
        familias: [],
        produtos: [produto("a", "Pão Rústico", 58.6), produto("b", "Pain Noir", -1)],
      },
    );
    const navegar = vi.fn();
    renderizar(navegar);
    await userEvent.click((await screen.findByRole("list", { name: "Pães por dia" })).querySelector("button") as HTMLElement);
    expect(navegar).toHaveBeenCalledWith("/producao/dia?data=2026-11-03");
    const lista = await screen.findByRole("list", { name: "Resultado por pão de cada produto" });
    const linhas = within(lista).getAllByRole("listitem");
    expect(linhas[0]).toHaveTextContent("Pain Noir");
    expect(linhas[0]).toHaveTextContent("− R$ 1,00");
    expect(linhas[1]).toHaveTextContent("Pão Rústico");
    expect(within(await screen.findByRole("region", { name: "Números do dia" })).getByRole("button", { name: /Produtos com prejuízo\s*1/ })).toBeInTheDocument();
  });

  it("as áreas do sistema aparecem com a situação e levam a cada uma", async () => {
    servir(
      base({
        fluxo: {
          etapas: [
            { id: "receitas", nome: "Receitas", pergunta: "Como eu faço?", estado: "falta", frase: "9 sem receita publicada", href: "/receitas" },
          ],
          proximo_passo: null,
          entradas_total: 1,
          entradas_pendentes: 0,
        },
      }),
    );
    const navegar = vi.fn();
    renderizar(navegar);
    const areas = (await screen.findByRole("heading", { name: "Áreas" })).closest("section")!;
    await userEvent.click(within(areas).getByRole("button", { name: /Receitas/ }));
    expect(navegar).toHaveBeenCalledWith("/receitas");
    await userEvent.click(within(areas).getByRole("button", { name: /Custos/ }));
    expect(navegar).toHaveBeenCalledWith("/gestao/custos");
  });

  it("sem os custos (falha ou ainda não calculados), o resto do painel aparece", async () => {
    servir(base(), null);
    renderizar();
    expect(await screen.findByText("Os custos ainda não foram calculados.")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Números do dia" })).toBeInTheDocument();
  });
});
