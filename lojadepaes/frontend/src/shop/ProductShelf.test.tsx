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

function shopFetch(catalog: { items: PublicProduct[]; page: number; page_size: number; total: number } | Error) {
  return vi.fn(async (input: RequestInfo) => {
    const url = String(input);
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
    expect(screen.getByText(/Farinha de trigo, Água, Levain, Sal, Azeite, Mel\./)).toBeInTheDocument();
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
    expect(screen.getAllByRole("article")).toHaveLength(3);
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
});
