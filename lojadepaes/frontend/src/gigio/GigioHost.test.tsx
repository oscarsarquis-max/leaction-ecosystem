import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { GigioHost } from "./GigioHost";

vi.mock("../../images/logos/avatar_gigio.png", () => ({ default: "gigio.png" }));

const requestJson = vi.fn();
vi.mock("../services/http", () => ({
  requestJson: (...args: unknown[]) => requestJson(...args),
}));

describe("GigioHost", () => {
  beforeEach(() => {
    sessionStorage.clear();
    requestJson.mockReset();
  });

  it("does not render when disabled", async () => {
    requestJson.mockResolvedValue({
      enabled: false,
      ready: false,
      live: false,
      welcome: null,
      starters: [],
      culinary: [],
    });
    render(<GigioHost path="/" />);
    await vi.waitFor(() => expect(requestJson).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Conversar com Gigio" })).not.toBeInTheDocument();
  });

  it("opens, sends, keeps conversation and closes with escape", async () => {
    const user = userEvent.setup();
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return {
          enabled: true,
          ready: true,
          live: false,
          welcome: "Oi, eu sou o Gigio, assistente virtual de A Loja.",
          starters: ["Como pedir e receber?"],
          culinary: ["O que preparo com este pão?"],
        };
      }
      return {
        reply: "Pedidos pelo calendário são para os próximos dias.",
        links: [{ href: "/#criacao", label: "Criador de Pães" }],
        suggestions: [],
        unavailable: false,
      };
    });
    render(<GigioHost path="/" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    expect(screen.getByRole("heading", { name: "Gigio" })).toBeInTheDocument();
    expect(screen.getByText(/Ideias para sua mesa/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Como pedir e receber?" }));
    expect(await screen.findByText(/próximos dias/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Criador de Pães" })).toHaveAttribute("href", "/#criacao");
    expect(screen.queryByRole("link", { name: "Ver acompanhamentos sugeridos" })).not.toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("heading", { name: "Gigio" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Conversar com Gigio" }));
    expect(screen.getByText(/próximos dias/)).toBeInTheDocument();
  });

  it("keeps the last question and allows a manual retry after failure", async () => {
    const user = userEvent.setup();
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return {
          enabled: true,
          ready: true,
          live: true,
          welcome: "Oi",
          starters: [],
          culinary: [],
        };
      }
      return {
        reply: "Não consegui concluir a resposta agora. Tente novamente.",
        links: [],
        suggestions: [],
        unavailable: true,
      };
    });
    render(<GigioHost path="/" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "Quero um pão rústico");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByRole("button", { name: "Tentar novamente" })).toBeEnabled();
    expect(screen.getByText("Quero um pão rústico")).toBeInTheDocument();
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: true, welcome: "Oi", starters: [], culinary: [] };
      }
      return { reply: "Toste e sirva com azeite.", links: [], suggestions: [], unavailable: false };
    });
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(await screen.findByText("Toste e sirva com azeite.")).toBeInTheDocument();
  });

  it("prende o CTA contextual à resposta e preserva o link anterior", async () => {
    const user = userEvent.setup();
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: true, welcome: "Oi", starters: [], culinary: [] };
      }
      return {
        reply: "Um vinho tinto e um queijo equilibram a crosta.",
        links: [],
        cta: { href: "/acompanhar?cats=vinhos,queijos&tipo=tinto", label: "Ver acompanhamentos sugeridos", kind: "vitrine" },
        suggestions: [],
        unavailable: false,
      };
    });
    render(<GigioHost path="/" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "Como servir com vinho e queijo?");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    const first = await screen.findByRole("link", { name: "Ver acompanhamentos sugeridos" });
    expect(first).toHaveAttribute("href", "/acompanhar?cats=vinhos,queijos&tipo=tinto");
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: true, welcome: "Oi", starters: [], culinary: [] };
      }
      return {
        reply: "Então fico só no queijo.",
        links: [],
        cta: { href: "/acompanhar?cats=queijos", label: "Ver acompanhamentos sugeridos", kind: "vitrine" },
        suggestions: [],
        unavailable: false,
      };
    });
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "Prefiro queijo, sem vinho");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    const ctas = await screen.findAllByRole("link", { name: "Ver acompanhamentos sugeridos" });
    expect(ctas).toHaveLength(2);
    expect(ctas[0]).toHaveAttribute("href", "/acompanhar?cats=vinhos,queijos&tipo=tinto");
    expect(ctas[1]).toHaveAttribute("href", "/acompanhar?cats=queijos");
  });

  it("mostra fontes em Sobre esta sugestão, separadas do CTA comercial", async () => {
    const user = userEvent.setup();
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: true, welcome: "Oi", starters: [], culinary: [] };
      }
      return {
        reply: "Um tinto do Dão combina com o leitão. Sugestão do Gigio.",
        links: [],
        cta: { href: "/acompanhar?cats=vinhos&mesa=leitao", label: "Ver acompanhamentos sugeridos", kind: "vitrine" },
        sources: [
          {
            href: "https://www.evino.com.br/blog/vinhos-do-dao/",
            label: "Vinhos do Dão",
            kind: "source",
            title: "Tinto do Dão com leitão assado",
            synthesis: "A redação descreve o Dão com leitão. Estilo, não garrafa.",
            kind_note: "Fonte comercial — informa atributos; não é avaliação independente.",
          },
        ],
        suggestions: [],
        unavailable: false,
      };
    });
    render(<GigioHost path="/" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "Qual vinho para o leitão?");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("Sobre esta sugestão")).toBeInTheDocument();
    await user.click(screen.getByText("Sobre esta sugestão"));
    expect(screen.getByRole("link", { name: "Fonte: Vinhos do Dão" })).toHaveAttribute(
      "href",
      "https://www.evino.com.br/blog/vinhos-do-dao/",
    );
    expect(screen.getByText(/não é avaliação independente/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver acompanhamentos sugeridos" })).toHaveAttribute(
      "href",
      "/acompanhar?cats=vinhos&mesa=leitao",
    );
  });

  it("mostra avaliação de guia com edição e safra, sem misturar no CTA", async () => {
    const user = userEvent.setup();
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: true, welcome: "Oi", starters: [], culinary: [] };
      }
      return {
        reply: "O Descorchados atribui 95 pontos a este rótulo e safra. Não prova harmonização.",
        links: [],
        cta: { href: "/acompanhar?cats=vinhos", label: "Ver acompanhamentos sugeridos", kind: "vitrine" },
        sources: [
          {
            href: "https://www.guiadescorchados.cl/archivos/originales/9d93c9af2f50f9023e344c1a0184df84.pdf",
            label: "Informe Brasil 2026 — Descorchados",
            kind: "source",
            title: "Descorchados 2026: Sabina Entre Serras Sauvignon Blanc 2025",
            score_line: "Descorchados · edição Informe Brasil 2026 · 95/100 · safra 2025",
            synthesis: "Nota do guia para este rótulo e safra.",
            kind_note: "Avaliação de rótulo no guia, com edição e safra. Não prova harmonização com o prato.",
          },
        ],
        suggestions: [],
        unavailable: false,
      };
    });
    render(<GigioHost path="/" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "O Sacramentos Sabina tem nota?");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    await user.click(await screen.findByText("Sobre esta sugestão"));
    expect(screen.getByText(/95\/100/)).toBeInTheDocument();
    expect(screen.getByText(/safra 2025/)).toBeInTheDocument();
    expect(screen.getByText(/Avaliação de rótulo no guia/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver acompanhamentos sugeridos" })).toHaveAttribute(
      "href",
      "/acompanhar?cats=vinhos",
    );
  });

  it("mostra fonte, receita e CTA na mesma resposta e conserva ao reabrir", async () => {
    const user = userEvent.setup();
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: true, welcome: "Oi", starters: [], culinary: [] };
      }
      return {
        reply: "A receita publicada é a de sardinhas com homus. Se quiser bebida, a Wine Folly trata sardinha como peixe intenso.",
        links: [
          {
            href: "/receitas/sardinhas-e-homus-de-grao-de-bico-fresco-tartine-bread",
            label: "Sardinhas e Homus de Grão-de-Bico Fresco (Tartine Bread)",
            kind: "recipe",
          },
        ],
        cta: { href: "/acompanhar?cats=azeites&mesa=sardinha", label: "Ver acompanhamentos sugeridos", kind: "vitrine" },
        sources: [
          {
            href: "https://winefolly.com/wine-pairing/wine-with-fish-pairing-guide/",
            label: "Pairing Wine with Fish",
            kind: "source",
            title: "Sardinhas e peixes de sabor intenso",
          },
        ],
        suggestions: [],
        unavailable: false,
      };
    });
    const { unmount } = render(<GigioHost path="/" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "O que combina com a receita de sardinhas com homus?");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByRole("link", { name: "Sardinhas e Homus de Grão-de-Bico Fresco (Tartine Bread)" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver acompanhamentos sugeridos" })).toHaveAttribute(
      "href",
      "/acompanhar?cats=azeites&mesa=sardinha",
    );
    await user.click(screen.getByText("Sobre esta sugestão"));
    expect(screen.getByText("Sardinhas e peixes de sabor intenso")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fechar conversa" }));
    unmount();
    render(<GigioHost path="/" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    expect(screen.getByRole("link", { name: "Ver acompanhamentos sugeridos" })).toHaveAttribute(
      "href",
      "/acompanhar?cats=azeites&mesa=sardinha",
    );
    expect(screen.getByRole("link", { name: "Sardinhas e Homus de Grão-de-Bico Fresco (Tartine Bread)" })).toBeInTheDocument();
  });

  it("keeps Montar esse pão on the message that proposed it", async () => {
    const user = userEvent.setup();
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: false, welcome: "Oi", starters: [], culinary: [] };
      }
      return {
        reply: "Para o sanduíche, farinha branca e fermentação natural curta em pão de forma.",
        links: [],
        builder_cta: { href: "/?proposta=abc.token#criacao", label: "Montar esse pão", kind: "builder" },
        suggestions: [],
        unavailable: false,
      };
    });
    render(<GigioHost path="/" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "Quero um sanduíche com pão de forma");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    const mount = await screen.findByRole("link", { name: "Montar esse pão" });
    expect(mount).toHaveAttribute("href", "/?proposta=abc.token#criacao");
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: false, welcome: "Oi", starters: [], culinary: [] };
      }
      return {
        reply: "Outra ideia, agora com integral.",
        links: [],
        builder_cta: { href: "/?proposta=def.token#criacao", label: "Montar esse pão", kind: "builder" },
        suggestions: [],
        unavailable: false,
      };
    });
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "E se for integral?");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    const buttons = await screen.findAllByRole("link", { name: "Montar esse pão" });
    expect(buttons).toHaveLength(2);
    expect(buttons[0]).toHaveAttribute("href", "/?proposta=abc.token#criacao");
    expect(buttons[1]).toHaveAttribute("href", "/?proposta=def.token#criacao");
  });

  it("does not copy the vitrine button onto an out-of-scope reply", async () => {
    const user = userEvent.setup();
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: false, welcome: "Oi", starters: [], culinary: [] };
      }
      return {
        reply: "Para o hambúrguer, cerveja e batatas.",
        links: [],
        cta: { href: "/acompanhar?cats=cervejas,batatas&mesa=hamburguer", label: "Ver acompanhamentos sugeridos", kind: "vitrine" },
        suggestions: [],
        unavailable: false,
      };
    });
    render(<GigioHost path="/" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "Hambúrguer com batatas");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByRole("link", { name: "Ver acompanhamentos sugeridos" })).toBeInTheDocument();
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: false, welcome: "Oi", starters: [], culinary: [] };
      }
      return {
        reply: "Não sou especialista em carro. Se quiser, retomamos o hambúrguer.",
        links: [],
        cta: null,
        suggestions: [],
        unavailable: false,
      };
    });
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "Onde compro um Fusca?");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    const buttons = screen.getAllByRole("link", { name: "Ver acompanhamentos sugeridos" });
    expect(buttons).toHaveLength(1);
    expect(screen.getByText(/Não sou especialista em carro/)).toBeInTheDocument();
  });

  it("pede Usar 1 crédito no aprofundamento e não trata falha do Hub como esgotamento", async () => {
    const user = userEvent.setup();
    const { setLibraryPageContext } = await import("./session");
    setLibraryPageContext({
      article_id: "o-comeco",
      article_version: 1,
      intent: "deepen",
      calculator_mode: "",
    });
    requestJson.mockImplementation(async (path: string) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: false, welcome: "Oi", starters: ["Como pedir e receber?"], culinary: [] };
      }
      if (path === "/api/v1/biblioteca/acesso") {
        return {
          identified: true,
          authorized: true,
          credits: 20,
          balance_source: "hub",
          exhausted: false,
          credit_cost: 1,
        };
      }
      return {
        reply: "Adapte a hidratação em 5 pontos e observe o ponto de véu.",
        links: [],
        suggestions: [],
        unavailable: false,
        access: { authorized: true, credits: 19, charged: true },
      };
    });
    render(<GigioHost path="/biblioteca/o-comeco" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    expect(screen.queryByRole("button", { name: "Como pedir e receber?" })).not.toBeInTheDocument();
    expect(await screen.findByText(/Saldo: 20/)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/Consulta de aprofundamento/), "Como adapto esta fórmula?");
    await user.click(screen.getByRole("button", { name: "Usar 1 crédito" }));
    expect(await screen.findByText(/hidratação/)).toBeInTheDocument();
    const chatCall = requestJson.mock.calls.find((item) => item[0] === "/api/v1/gigio/chat");
    expect(chatCall?.[1]).toMatchObject({ method: "POST" });
    const body = JSON.parse(String(chatCall?.[1]?.body || "{}"));
    expect(body.spend_credit).toBe(true);
    expect(body.operation_id).toBeTruthy();
    setLibraryPageContext(null);
  });

  it("responde livre, oferece refino sem débito e só autoriza 1 crédito no clique", async () => {
    const user = userEvent.setup();
    const chats: Array<Record<string, unknown>> = [];
    requestJson.mockImplementation(async (path: string, init?: { body?: string }) => {
      if (path === "/api/v1/gigio/status") {
        return { enabled: true, ready: true, live: true, welcome: "Oi", starters: [], culinary: [] };
      }
      const body = JSON.parse(String(init?.body || "{}")) as Record<string, unknown>;
      chats.push(body);
      if (chats.length === 1) {
        return {
          reply: "**Tinto** de tanino baixo.\n\n- Assumo assado simples.",
          links: [],
          cta: { href: "/acompanhar?cats=vinhos&tipo=tinto", label: "Ver acompanhamentos sugeridos", kind: "vitrine" },
          sources: [
            {
              href: "https://winefolly.com/wine-pairing/wine-with-fish-pairing-guide/",
              label: "Pairing Wine with Fish",
              kind: "source",
              title: "Peixe grelhado segundo o tipo",
              synthesis: "O preparo muda a escolha.",
              kind_note: "Publicação especializada. Não certifica um SKU à venda.",
            },
          ],
          suggestions: [],
          unavailable: false,
        };
      }
      if (chats.length === 2) {
        return {
          reply: "A resposta anterior já fecha esta consulta livre. Cada envio no aprofundamento usa 1 crédito de IA. Nada foi debitado agora.",
          links: [],
          cta: null,
          sources: [],
          suggestions: [],
          notice: "Aprofundar com o Gigio · Usar 1 crédito de IA",
          unavailable: false,
          access: { deepen_offer: true, charged: false, needs_confirm: true, cost_label: "Usar 1 crédito de IA" },
        };
      }
      if (chats.length === 3) {
        return {
          reply: "Com hortelã, o tinto fica mais leve. Saldo avulso: 9.",
          links: [],
          cta: { href: "/acompanhar?cats=vinhos&tipo=tinto", label: "Ver acompanhamentos sugeridos", kind: "vitrine" },
          sources: [],
          suggestions: [],
          unavailable: false,
          access: { charged: true, credits: 9, credit_cost: 1 },
        };
      }
      return {
        reply: "Os créditos de IA acabaram. A conversa livre continua.",
        links: [],
        suggestions: [],
        unavailable: false,
        access: { exhausted: true, charged: false, credits: 0 },
      };
    });
    render(<GigioHost path="/" />);
    await user.click(await screen.findByRole("button", { name: "Conversar com Gigio" }));
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "Que vinho combina com carneiro assado?");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("Tinto")).toBeInTheDocument();
    expect(screen.getByText("Tinto").tagName).toBe("STRONG");
    expect(screen.getByText("Assumo assado simples.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver acompanhamentos sugeridos" })).toHaveAttribute(
      "href",
      "/acompanhar?cats=vinhos&tipo=tinto",
    );
    await user.click(screen.getByText("Sobre esta sugestão"));
    expect(screen.getByText(/O preparo muda a escolha/)).toBeInTheDocument();
    expect(chats[0].spend_credit).toBeUndefined();

    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "E se o molho for de hortelã?");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText(/Nada foi debitado agora/)).toBeInTheDocument();
    expect(chats[1].spend_credit).toBeUndefined();
    expect(screen.getByText(/Aprofundar com o Gigio/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Usar 1 crédito de IA" }));
    expect(await screen.findByText(/Saldo avulso: 9/)).toBeInTheDocument();
    expect(chats[2].spend_credit).toBe(true);
    expect((chats[2].page as { consult?: string }).consult).toBe("deepen");
    expect(screen.getByRole("button", { name: "Voltar à consulta livre" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Voltar à consulta livre" }));
    expect(screen.queryByRole("button", { name: "Voltar à consulta livre" })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Mensagem para o Gigio"), "Qual o Pix do meu pedido?");
    await user.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText(/conversa livre continua/)).toBeInTheDocument();
    expect(chats[3].spend_credit).toBeUndefined();
    expect(screen.getByText(/tanino baixo/)).toBeInTheDocument();
  });
});
