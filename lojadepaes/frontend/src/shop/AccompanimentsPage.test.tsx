import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccompanimentsPage } from "./AccompanimentsPage";
import type { AccompanimentCard, AccompanimentsCatalog } from "./accompanimentsApi";

const requestJson = vi.fn();
vi.mock("../services/http", () => ({
  requestJson: (...args: unknown[]) => requestJson(...args),
}));

function sampleCard(partial: Partial<AccompanimentCard> & Pick<AccompanimentCard, "id" | "name">): AccompanimentCard {
  return {
    description: "Descrição breve.",
    image_url: null,
    occasion: "Mesa",
    story_title: "Mesa da casa",
    story_lead: "",
    why_pairs: "",
    serving_tip: "",
    price_label: "R$ 10,00",
    price_fresh: true,
    price_as_of: null,
    outbound_href: "https://www.mercadolivre.com.br/p/MLBTEST",
    outbound_label: "Ver no Mercado Livre",
    marketplace: "Mercado Livre",
    story_href: `/acompanhar#${partial.id}`,
    related_product_slugs: [],
    related_breads: [],
    related_recipes: [],
    ...partial,
  };
}

function catalogOf(items: AccompanimentCard[]): AccompanimentsCatalog {
  return {
    enabled: true,
    title: "Para acompanhar seu pão",
    intro: "Uma seleção de complementos.",
    source_status: "hub",
    commission_note: "Links comissionados: A Loja pode receber uma comissão pelas compras.",
    external_notice: "Compra e entrega realizadas separadamente pelo Mercado Livre.",
    delivery_help: { mode: "manual", text: "Confira a previsão no Mercado Livre." },
    attribution_ready: true,
    stories: [],
    items,
  };
}

afterEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("página Para acompanhar seu pão", () => {
  it("não publica chamada comercial quando a curadoria está desligada", async () => {
    requestJson.mockResolvedValue({
      enabled: false,
      title: "Para acompanhar seu pão",
      intro: "Uma seleção de complementos e acessórios para aproveitar seus pães à mesa ou encontrar uma ideia de presente.",
      source_status: "off",
      commission_note: null,
      external_notice: null,
      delivery_help: { mode: "manual", text: "Confira a previsão no Mercado Livre." },
      attribution_ready: false,
      stories: [],
      items: [],
    });
    render(<AccompanimentsPage />);
    expect(await screen.findByRole("heading", { name: "Para acompanhar seu pão" })).toBeInTheDocument();
    expect(screen.getByText(/ainda não está publicada/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ver no Mercado Livre" })).not.toBeInTheDocument();
  });

  it("identifica fixture local e não oferece compra", async () => {
    requestJson.mockResolvedValue({
      enabled: true,
      title: "Para acompanhar seu pão",
      intro: "Uma seleção de complementos.",
      source_status: "local_preview",
      preview: true,
      demo_notice: "Esta página está em prévia local.",
      commission_note: null,
      external_notice: "Prévia local: este item é fixture de demonstração.",
      delivery_help: { mode: "manual", text: "Confira a previsão no destino." },
      attribution_ready: false,
      stories: [
        {
          occasion: "Café da manhã",
          title: "Café com fatias mornas",
          lead: "Toste o pão.",
          items: [
            {
              id: "local-demo-azeite",
              name: "Azeite extra virgem (demonstração local)",
              description: "Fixture desta prévia.",
              image_url: null,
              occasion: "Café da manhã",
              story_title: "Café com fatias mornas",
              story_lead: "Toste o pão.",
              why_pairs: "Equilibra a crosta.",
              serving_tip: "Sirva ainda morno.",
              price_label: null,
              price_fresh: false,
              price_as_of: null,
              outbound_href: null,
              outbound_label: null,
              marketplace: null,
              demo: true,
              commercial_enabled: false,
              external_notice: "Prévia local: este item é fixture de demonstração.",
              story_href: "/acompanhar#local-demo-azeite",
              related_product_slugs: ["pao-fermentacao-natural-de-trigo"],
              related_breads: [
                {
                  slug: "pao-fermentacao-natural-de-trigo",
                  name: "Pão Fermentação Natural de Trigo",
                  href: "/paes/pao-fermentacao-natural-de-trigo",
                },
              ],
              related_recipes: [],
            },
          ],
        },
      ],
      items: [],
    });
    render(<AccompanimentsPage />);
    expect(await screen.findByRole("heading", { name: "Café com fatias mornas" })).toBeInTheDocument();
    expect(screen.getAllByText(/prévia local/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/sem preço comercial/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Ver no Mercado Livre" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByText("Mais sobre este acompanhamento"));
    expect(screen.getByRole("link", { name: "Pão Fermentação Natural de Trigo" })).toHaveAttribute(
      "href",
      "/paes/pao-fermentacao-natural-de-trigo",
    );
  });

  it("mostra história, preço, aviso e o destino oficial", async () => {
    requestJson.mockResolvedValue({
      enabled: true,
      title: "Para acompanhar seu pão",
      intro: "Uma seleção de complementos.",
      source_status: "snapshot",
      commission_note: "Links comissionados: A Loja pode receber uma comissão pelas compras.",
      external_notice: "Compra e entrega realizadas separadamente pelo Mercado Livre.",
      delivery_help: { mode: "manual", text: "Confira a previsão no Mercado Livre e escolha uma fornada." },
      attribution_ready: true,
      stories: [
        {
          occasion: "Café da manhã",
          title: "Café com fatias mornas",
          lead: "Toste o pão e acrescente o azeite na hora.",
          items: [
            {
              id: "item-1",
              name: "Azeite da casa",
              description: "Azeite extra virgem para a mesa.",
              image_url: "https://http2.mlstatic.com/demo.jpg",
              occasion: "Café da manhã",
              story_title: "Café com fatias mornas",
              story_lead: "Toste o pão.",
              why_pairs: "A gordura do azeite equilibra a crosta.",
              serving_tip: "Sirva ainda morno.",
              price_label: "R$ 42,90",
              price_fresh: true,
              price_as_of: "2026-10-06T12:00:00+00:00",
              outbound_href: "https://www.mercadolivre.com.br/p/MLBTEST123?attr=keep",
              outbound_label: "Ver no Mercado Livre",
              marketplace: "Mercado Livre",
              vendor: "mercadolivre",
              external_notice: "Compra e entrega realizadas separadamente pelo Mercado Livre. Confira preço e disponibilidade no destino.",
              story_href: "/acompanhar#item-1",
              related_product_slugs: ["pao-da-casa"],
              related_breads: [{ slug: "pao-da-casa", name: "Pão da casa", href: "/paes/pao-da-casa" }],
              related_recipes: [],
            },
          ],
        },
      ],
      items: [],
    });
    render(<AccompanimentsPage />);
    expect(await screen.findByRole("heading", { name: "Café com fatias mornas" })).toBeInTheDocument();
    expect(screen.getByText("R$ 42,90")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Mais sobre este acompanhamento"));
    expect(screen.getByText(/Combina com/)).toBeInTheDocument();
    const outbound = screen.getByRole("link", { name: "Ver no Mercado Livre" });
    expect(outbound).toHaveAttribute("href", "https://www.mercadolivre.com.br/p/MLBTEST123?attr=keep");
    expect(outbound).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText(/Links comissionados/)).toBeInTheDocument();
    expect(screen.getByText(/Compra e entrega realizadas separadamente/)).toBeInTheDocument();
    expect(screen.getByText("Data informada de entrega")).toBeInTheDocument();
    expect(screen.queryByText("Data prevista que você viu no destino")).not.toBeInTheDocument();
  });

  it("nomeia Amazon quando o destino é Amazon", async () => {
    requestJson.mockResolvedValue({
      enabled: true,
      title: "Para acompanhar seu pão",
      intro: "Uma seleção de complementos.",
      source_status: "hub",
      commission_note: "Links comissionados: A Loja pode receber uma comissão pelas compras.",
      external_notice: "Compra e entrega realizadas separadamente pela Amazon.",
      delivery_help: { mode: "manual", text: "Confira a previsão no destino." },
      attribution_ready: true,
      stories: [
        {
          occasion: "Mesa de fim de tarde",
          title: "Vinho da mesa",
          lead: "",
          items: [
            {
              id: "B00VINHO1",
              name: "Vinho da mesa",
              description: "Vinho tinto para a mesa.",
              image_url: null,
              occasion: "Mesa de fim de tarde",
              story_title: "Vinho da mesa",
              story_lead: "",
              why_pairs: "",
              serving_tip: "",
              price_label: "R$ 59,90",
              price_fresh: true,
              price_as_of: null,
              outbound_href: "https://www.amazon.com.br/dp/B00VINHO1?tag=loja-20",
              outbound_label: "Ver na Amazon",
              marketplace: "Amazon",
              vendor: "amazon",
              external_notice: "Compra e entrega realizadas separadamente pela Amazon. Confira preço e disponibilidade no destino.",
              story_href: "/acompanhar#B00VINHO1",
              related_product_slugs: [],
              related_breads: [],
              related_recipes: [],
            },
          ],
        },
      ],
      items: [],
    });
    render(<AccompanimentsPage />);
    const outbound = await screen.findByRole("link", { name: "Ver na Amazon" });
    expect(outbound).toHaveAttribute("href", "https://www.amazon.com.br/dp/B00VINHO1?tag=loja-20");
    expect(screen.queryByRole("link", { name: "Ver no Mercado Livre" })).not.toBeInTheDocument();
  });

  it("pagina 13 itens sem repetir e volta à primeira página", async () => {
    const items = Array.from({ length: 13 }, (_, index) =>
      sampleCard({ id: `item-${index + 1}`, name: `Item ${index + 1}` }),
    );
    requestJson.mockResolvedValue(catalogOf(items));
    render(<AccompanimentsPage />);
    expect(await screen.findByRole("heading", { name: "Item 1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Item 12" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Item 13" })).not.toBeInTheDocument();
    expect(screen.getByText("Página 1 de 2 · 13 itens")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Próxima" }));
    expect(await screen.findByRole("heading", { name: "Item 13" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Item 1" })).not.toBeInTheDocument();
    expect(screen.getByText("Página 2 de 2 · 13 itens")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Próxima" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Anterior" }));
    expect(await screen.findByRole("heading", { name: "Item 1" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Item 13" })).not.toBeInTheDocument();
  });

  it("mostra o contexto filtrado e o atalho para a seleção geral", async () => {
    window.history.replaceState(null, "", "/acompanhar?cats=vinhos,queijos");
    requestJson.mockResolvedValue({
      ...catalogOf([sampleCard({ id: "vinho-1", name: "Vinho tinto da mesa" })]),
      title: "Acompanhamentos para vinhos e queijos",
      context: {
        active: true,
        empty: false,
        title: "Acompanhamentos para vinhos e queijos",
        filters: [
          { key: "cats", label: "Vinhos" },
          { key: "cats", label: "Queijos" },
        ],
        clear_href: "/acompanhar",
      },
    });
    render(<AccompanimentsPage />);
    expect(await screen.findByRole("heading", { name: "Acompanhamentos para vinhos e queijos" })).toBeInTheDocument();
    expect(screen.getByText("Vinhos")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver todos os acompanhamentos" })).toHaveAttribute("href", "/acompanhar");
  });

  it("não troca silêncio por catálogo genérico quando o contexto vem vazio", async () => {
    requestJson.mockResolvedValue({
      ...catalogOf([]),
      enabled: true,
      title: "Acompanhamentos para vinhos",
      context: {
        active: true,
        empty: true,
        title: "Acompanhamentos para vinhos",
        filters: [{ key: "cats", label: "Vinhos" }],
        clear_href: "/acompanhar",
      },
    });
    render(<AccompanimentsPage />);
    expect(await screen.findByText(/Não há complementos disponíveis para essa sugestão/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver todos os acompanhamentos" })).toHaveAttribute("href", "/acompanhar");
    expect(screen.queryByRole("link", { name: "Ver no Mercado Livre" })).not.toBeInTheDocument();
  });

  it("não repete o nome do produto como cabeçalho da grade e usa no Mercado Livre", async () => {
    requestJson.mockResolvedValue({
      ...catalogOf([
        sampleCard({
          id: "vinho-1",
          name: "Vinho Tinto Português 750ml",
          story_title: "Vinho Tinto Português 750ml",
          occasion: "Mesa de fim de tarde",
          price_label: null,
          price_fresh: false,
        }),
      ]),
      title: "Sugestões para sua mesa",
      context: {
        active: true,
        empty: false,
        title: "Sugestões para sua mesa",
        summary: "leitão e saladas",
        filters: [
          { key: "mesa", label: "leitão" },
          { key: "cats", label: "Vinhos" },
        ],
        clear_href: "/acompanhar",
      },
    });
    render(<AccompanimentsPage />);
    expect(await screen.findByRole("heading", { name: "Sugestões para sua mesa" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Vinho Tinto Português 750ml" })).toHaveLength(1);
    expect(screen.getByText("Consulte o preço no Mercado Livre")).toBeInTheDocument();
    expect(screen.queryByText(/na Mercado Livre/)).not.toBeInTheDocument();
  });

  it("recua página inválida quando o catálogo encolhe", async () => {
    window.history.replaceState(null, "", "/acompanhar?pagina=9");
    requestJson.mockResolvedValue(
      catalogOf(Array.from({ length: 13 }, (_, index) => sampleCard({ id: `late-${index + 1}`, name: `Late ${index + 1}` }))),
    );
    render(<AccompanimentsPage />);
    expect(await screen.findByText("Página 2 de 2 · 13 itens")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Late 13" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Late 1" })).not.toBeInTheDocument();
  });
});
