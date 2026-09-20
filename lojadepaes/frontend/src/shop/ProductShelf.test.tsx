import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
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

describe("vitrine de produtos", () => {
  it("lista pães publicados e usa a partir de só com preços distintos", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ items: [product], page: 1, page_size: 24, total: 1 }),
      }),
    );
    render(<ProductShelf />);
    expect(await screen.findByRole("heading", { name: "Pão da casa" })).toBeInTheDocument();
    expect(screen.getByText("A partir de R$ 24,90")).toBeInTheDocument();
    expect(screen.getByText("500 g · 800 g")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it("distingue catálogo vazio de falha e permite tentar de novo", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ items: [], page: 1, page_size: 24, total: 0 }),
      }),
    );
    const { unmount } = render(<ProductShelf />);
    expect(await screen.findByText("Ainda não há pães publicados na vitrine.")).toBeInTheDocument();
    unmount();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<ProductShelf />);
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
    expect(screen.getByText("Subtotal R$ 24,90")).toBeInTheDocument();
    await user.click(screen.getByLabelText(/800 g/));
    expect(screen.getByText("Subtotal R$ 32,00")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Adicionar à seleção" }));
    expect(screen.getByRole("heading", { name: "Sua seleção" })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
