import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CartProvider } from "./CartContext";
import { ProductPage } from "./ProductPage";
import { ProductShelf } from "./ProductShelf";
import { SelectionDrawer } from "./SelectionDrawer";
import type { PublicProduct } from "./types";

const product: PublicProduct = {
  name: "Pão da casa",
  slug: "pao-da-casa",
  short_description: "Crosta firme e miolo aberto.",
  long_description: "Assado em pedra.",
  image_url: "/api/v1/catalog/media/demo",
  image_alt: "Pão sobre pano",
  is_available: true,
  from_price: { cents: 2490, currency: "BRL" },
  price_is_from: true,
  ingredients: [{ name: "Farinha de trigo" }, { name: "Água" }],
  allergen_note: "Informações sobre alergênicos ainda não foram revisadas para este produto.",
  variants: [
    {
      id: "v500",
      display_name: "500 g",
      presentation_type: "weight",
      net_weight_grams: 500,
      units_per_pack: null,
      pack_label: null,
      price: { cents: 2490, currency: "BRL" },
    },
    {
      id: "v800",
      display_name: "800 g",
      presentation_type: "weight",
      net_weight_grams: 800,
      units_per_pack: null,
      pack_label: null,
      price: { cents: 3200, currency: "BRL" },
    },
  ],
};

const emptyCalendar = {
  occupancy_enabled: false,
  reservation_policy: "unset",
  timezone: "America/Sao_Paulo",
  selected_date: null,
  selected_status: null,
  full_message: null,
  alternatives: [],
  notice: null,
  days: [],
};

function shopFetch(
  catalog: { items: PublicProduct[]; page: number; page_size: number; total: number } | Error,
  weekRecipe: unknown = null,
  archive: { items: unknown[]; page: number; page_size: number; total: number; q: string } = {
    items: [],
    page: 1,
    page_size: 5,
    total: 0,
    q: "",
  },
) {
  return vi.fn(async (input: RequestInfo) => {
    const url = String(input);
    if (url.includes("/operations")) {
      return {
        ok: true,
        json: async () => ({
          preview_protection: false,
          orders_enabled: true,
          payments_enabled: true,
          date_requests_enabled: true,
          house_fidelity_active: false,
          business_date: "2026-09-29",
          message: null,
        }),
      };
    }
    if (url.includes("/promotions/house-fidelity")) {
      return {
        ok: true,
        json: async () => ({
          campaign_active: false,
          preview: false,
          restart_at: "2026-10-01T00:00:00-03:00",
          restart_label: "1º de outubro, às 00h (horário de Brasília)",
          stamps: "neutral",
          participant: null,
          pending_criteria: ["pedido_valido", "apresentacao", "frete"],
        }),
      };
    }
    if (url.includes("/schedule/suggestions")) {
      return {
        ok: true,
        json: async () => ({
          context_date: null,
          context_source: "none",
          context_label: null,
          mode: "empty",
          title: "Sugestões para sua fornada",
          message: "Não há fornada disponível neste calendário. Você pode pedir outra data.",
          items: [],
        }),
      };
    }
    if (url.includes("/schedule/")) {
      return { ok: true, json: async () => emptyCalendar };
    }
    if (catalog instanceof Error) {
      throw catalog;
    }
    if (url.includes("/catalog/week-recipes")) {
      return { ok: true, json: async () => archive };
    }
    if (url.includes("/catalog/week-recipe")) {
      return { ok: true, json: async () => ({ recipe: weekRecipe }) };
    }
    if (url.includes("/catalog/showcase") || url.includes("/catalog/products")) {
      return { ok: true, json: async () => catalog };
    }
    return { ok: false, status: 404, json: async () => ({ detail: "não encontrado" }) };
  });
}

describe("vitrine de produtos", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  it("lista pães publicados e usa a partir de só com preços distintos", async () => {
    vi.stubGlobal(
      "fetch",
      shopFetch({ items: [product], page: 1, page_size: 24, total: 1 }),
    );
    render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Nossos pães" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Seu quarto pedido traz um pão de presente/ })).toBeInTheDocument();
    const band = document.querySelector(".shelf-band");
    expect(band?.querySelector(".bake-calendar")).not.toBeNull();
    expect(band?.querySelector(".house-fidelity")).not.toBeNull();
    expect(band?.querySelector(".fornada-panel")).toBeNull();
    expect(band?.querySelector(".week-recipe")).toBeNull();
    expect(screen.getByRole("heading", { name: "Pão da casa" })).toBeInTheDocument();
    expect(screen.getByText("Crosta firme e miolo aberto.")).toBeInTheDocument();
    expect(screen.getByText("A partir de R$ 24,90")).toBeInTheDocument();
    expect(screen.getByText("500 g · 800 g")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Escolher meu pão" })).toHaveAttribute("href", "/paes/pao-da-casa");
    expect(screen.getByText(/Farinha de trigo, Água/)).toBeInTheDocument();
    expect(screen.queryByText("Pão sobre pano")).not.toBeInTheDocument();
    const urls = vi.mocked(fetch).mock.calls.map((call) => String(call[0]));
    expect(urls.some((url) => url.includes("/catalog/showcase"))).toBe(true);
    expect(urls.some((url) => url.includes("/catalog/products"))).toBe(false);
    vi.unstubAllGlobals();
  });

  it("mostra a legenda visível abaixo da foto e esconde o espaço quando vazia", async () => {
    vi.stubGlobal(
      "fetch",
      shopFetch({
        items: [{ ...product, image_caption: "Fatia com raspas de limão." }],
        page: 1,
        page_size: 10,
        total: 1,
      }),
    );
    const { unmount } = render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByText("Fatia com raspas de limão.")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Pão sobre pano" })).toBeInTheDocument();
    unmount();
    vi.stubGlobal(
      "fetch",
      shopFetch({ items: [{ ...product, image_caption: "" }], page: 1, page_size: 10, total: 1 }),
    );
    render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Pão da casa" })).toBeInTheDocument();
    expect(screen.queryByText("Fatia com raspas de limão.")).not.toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Pão sobre pano" })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("expande a lista longa de ingredientes no cartão", async () => {
    const user = userEvent.setup();
    const longList = [
      { name: "Farinha de trigo" },
      { name: "Água" },
      { name: "Levain" },
      { name: "Sal" },
      { name: "Azeite" },
      { name: "Mel" },
    ];
    vi.stubGlobal(
      "fetch",
      shopFetch({
        items: [{ ...product, ingredients: longList }],
        page: 1,
        page_size: 10,
        total: 1,
      }),
    );
    render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByText(/Farinha de trigo, Água, Levain…/)).toBeInTheDocument();
    const disclosure = screen.getByText("Ver ingredientes").closest("details");
    expect(disclosure).not.toBeNull();
    expect(disclosure).not.toHaveAttribute("open");
    await user.click(screen.getByText("Ver ingredientes"));
    expect(disclosure).toHaveAttribute("open");
    expect(screen.getByText(/Farinha de trigo, Água, Levain, Sal, Azeite, Mel\./)).toBeVisible();
    expect(screen.queryByText(/Farinha de trigo, Água, Levain…/)).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("não duplica a lista quando o resumo já traz a composição literal", async () => {
    vi.stubGlobal(
      "fetch",
      shopFetch({
        items: [
          {
            ...product,
            short_description: "Farinha de trigo, Água.",
            ingredients: [{ name: "Farinha de trigo" }, { name: "Água" }],
          },
        ],
        page: 1,
        page_size: 10,
        total: 1,
      }),
    );
    render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByText("Farinha de trigo, Água.")).toBeInTheDocument();
    expect(screen.queryByText("Ingredientes")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("mostra só os pães da vitrine na ordem recebida, sem cartões vazios", async () => {
    const items = Array.from({ length: 3 }, (_, index) => ({
      ...product,
      name: `Pão ${index + 1}`,
      slug: `pao-${index + 1}`,
    }));
    vi.stubGlobal("fetch", shopFetch({ items, page: 1, page_size: 10, total: 3 }));
    render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Pão 1" })).toBeInTheDocument();
    expect(document.querySelectorAll(".shelf-card")).toHaveLength(3);
    expect(screen.getByRole("article", { name: /Seu quarto pedido traz um pão de presente/ })).toBeInTheDocument();
    expect(screen.queryByText("Fotografia ainda não disponível")).not.toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("distingue catálogo vazio de falha e permite tentar de novo", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", shopFetch({ items: [], page: 1, page_size: 24, total: 0 }));
    const { unmount } = render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByText("Ainda não há pães na vitrine.")).toBeInTheDocument();
    unmount();
    vi.stubGlobal("fetch", shopFetch(new TypeError("Failed to fetch")));
    render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByText(/Não foi possível carregar os pães agora/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
    vi.unstubAllGlobals();
  });

  it("atualiza subtotal ao trocar a variação e adiciona à seleção", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => product,
      }),
    );
    render(
      <CartProvider>
        <ProductPage slug="pao-da-casa" />
        <SelectionDrawer />
      </CartProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Pão da casa" })).toBeInTheDocument();
    expect(screen.getByText("Crosta firme e miolo aberto.")).toBeInTheDocument();
    expect(screen.getByText("Assado em pedra.")).toBeInTheDocument();
    expect(screen.getByText(/Farinha de trigo, Água/)).toBeInTheDocument();
    expect(screen.getByText("Subtotal R$ 24,90")).toBeInTheDocument();
    await user.click(screen.getByLabelText(/800 g/));
    expect(screen.getByText("Subtotal R$ 32,00")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Adicionar à seleção" }));
    expect(screen.getByRole("heading", { name: "Sua seleção" })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("oferece adaptação opcional sem misturar linhas da mesma variação", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => product,
      }),
    );
    render(
      <CartProvider>
        <ProductPage slug="pao-da-casa" />
        <SelectionDrawer />
      </CartProvider>,
    );
    expect(await screen.findByText("Pedir uma adaptação")).toBeInTheDocument();
    const disclosure = document.querySelector(".adaptation-disclosure");
    expect(disclosure).not.toBeNull();
    expect(disclosure).not.toHaveAttribute("open");
    await user.click(disclosure!.querySelector("summary") as HTMLElement);
    expect(screen.getByText("O que você gostaria de mudar?")).toBeInTheDocument();
    await user.type(
      screen.getByLabelText(/Ingrediente a retirar/),
      "retirar gergelim",
    );
    await user.click(screen.getByLabelText("Intolerância ou restrição alimentar"));
    expect(screen.getByText(/não garante ausência de alergênicos/i)).toBeInTheDocument();
    expect(screen.queryByText(/sem glúten/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Adicionar à seleção" }));
    expect(screen.getByText(/Adaptação solicitada/)).toBeInTheDocument();
    expect(screen.getAllByText(/retirar gergelim/).length).toBeGreaterThan(0);
    vi.unstubAllGlobals();
  });

  it("mostra a receita da semana abaixo da promoção, sem CTA comercial", async () => {
    vi.stubGlobal(
      "fetch",
      shopFetch(
        { items: [product], page: 1, page_size: 10, total: 1 },
        {
          title: "Torrada da casa",
          slug: "torrada-da-casa",
          summary: "Fatias com azeite e tomate.",
          image_url: "/api/v1/catalog/media/demo",
          image_alt: "Torrada",
          image_caption: "",
          image_focus: "50% 40%",
          prep_time: null,
          yield_text: null,
          ingredients: ["Pão"],
          steps: ["Tostar"],
          breads: [],
          href: "/receitas/torrada-da-casa",
        },
      ),
    );
    render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Torrada da casa" })).toBeInTheDocument();
    expect(screen.getByText("Receita em destaque")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver receita" })).toHaveAttribute("href", "/receitas/torrada-da-casa");
    expect(screen.getByRole("heading", { name: "Mais ideias para sua mesa" })).toBeInTheDocument();
    expect(screen.getByLabelText("Buscar receitas")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Receita ou ingrediente…")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Buscar" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver o acervo de receitas" })).toHaveAttribute("href", "/receitas");
    const photo = document.querySelector(".week-recipe-media img") as HTMLImageElement;
    expect(photo).toBeTruthy();
    expect(photo.getAttribute("style")).toBeNull();
    const recipe = document.querySelector(".week-recipe");
    expect(recipe?.querySelector(".bake-calendar-request")).toBeNull();
    expect(recipe).not.toHaveTextContent("Escolher meu pão");
    expect(recipe).not.toHaveTextContent("Prévia");
    expect(document.querySelector(".bake-calendar .bake-calendar-request")).not.toBeNull();
    const side = document.querySelector(".shelf-side");
    expect(side?.querySelector(".house-fidelity")?.nextElementSibling?.classList.contains("week-recipe")).toBe(true);
    vi.unstubAllGlobals();
  });

  it("mantém a busca sem foto vazia quando só há acervo publicado", async () => {
    vi.stubGlobal(
      "fetch",
      shopFetch(
        { items: [product], page: 1, page_size: 10, total: 1 },
        null,
        {
          items: [{ title: "Torrada da casa", slug: "torrada-da-casa", summary: "Fatias.", href: "/receitas/torrada-da-casa", image_url: null }],
          page: 1,
          page_size: 5,
          total: 1,
          q: "",
        },
      ),
    );
    render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Mais ideias para sua mesa" })).toBeInTheDocument();
    expect(screen.queryByText("Receita em destaque")).not.toBeInTheDocument();
    expect(document.querySelector(".week-recipe-media")).toBeNull();
    expect(screen.getByRole("button", { name: "Buscar" })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("omite o bloco da receita quando não há destaque", async () => {
    vi.stubGlobal("fetch", shopFetch({ items: [product], page: 1, page_size: 10, total: 1 }));
    render(
      <CartProvider>
        <ProductShelf />
      </CartProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Nossos pães" })).toBeInTheDocument();
    expect(screen.queryByText("Receita em destaque")).not.toBeInTheDocument();
    expect(document.querySelector(".week-recipe")).toBeNull();
    expect(document.querySelector(".fornada-panel")).toBeNull();
    vi.unstubAllGlobals();
  });
});
