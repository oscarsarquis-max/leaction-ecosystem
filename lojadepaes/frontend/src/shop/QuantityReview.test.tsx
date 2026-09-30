import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CartProvider } from "./CartContext";
import { CheckoutPage } from "./CheckoutPage";
import { ProductPage } from "./ProductPage";
import { SelectionDrawer } from "./SelectionDrawer";
import { SELECTION_KEY } from "./selection";
import type { PublicProduct } from "./types";

const pepperoni: PublicProduct = {
  name: "Rolled Bread de Pepperoni com Muçarela e Manteiga de Alho",
  slug: "rolled-bread",
  short_description: "Pepperoni e muçarela.",
  long_description: "Pão recheado.",
  image_url: "/api/v1/catalog/media/demo",
  image_alt: "Pão de pepperoni",
  is_available: true,
  from_price: { cents: 7000, currency: "BRL" },
  price_is_from: false,
  ingredients: [{ name: "Pepperoni" }],
  allergen_note: "Informações sobre alergênicos ainda não foram revisadas para este produto.",
  variants: [
    {
      id: "pepperoni-500",
      display_name: "500 g",
      presentation_type: "weight",
      net_weight_grams: 500,
      units_per_pack: null,
      pack_label: null,
      price: { cents: 7000, currency: "BRL" },
    },
  ],
};

vi.mock("./calendarApi", () => ({
  previewCalendar: vi.fn(async () => ({
    occupancy_enabled: true,
    reservation_policy: "admin_accept",
    timezone: "America/Sao_Paulo",
    selected_date: "2026-09-30",
    selected_status: "available",
    full_message: null,
    alternatives: [],
    notice: null,
    review_message: null,
    days: [
      {
        date: "2026-09-30",
        status: "available",
        accessible_label: "quarta-feira, 30 de setembro",
        at_capacity: false,
        eligible: true,
      },
    ],
  })),
}));

describe("quantidade na revisão", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/storefront/quote")) {
          const payload = JSON.parse(String(init?.body)) as { items: Array<{ quantity: number }> };
          const quantity = payload.items[0]?.quantity ?? 1;
          return {
            ok: true,
            json: async () => ({
              requested_date: "2026-09-30",
              currency: "BRL",
              subtotal_cents: 7000 * quantity,
              total_cents: 7000 * quantity,
              date_label: "quarta-feira, 30 de setembro",
              occupies_capacity: false,
              notice: null,
              items: [],
            }),
          };
        }
        return { ok: true, json: async () => pepperoni };
      }),
    );
  });

  it("um clique em carrinho vazio deixa 1 pão e R$ 70,00 na revisão", async () => {
    const user = userEvent.setup();
    const page = render(
      <CartProvider>
        <ProductPage slug="rolled-bread" />
        <SelectionDrawer />
      </CartProvider>,
    );
    expect(await screen.findByRole("heading", { name: pepperoni.name })).toBeInTheDocument();
    expect(screen.queryByText(/500 g por pão/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Adicionar à seleção" }));
    expect(await screen.findByText("Adicionado 1 pão.")).toBeInTheDocument();
    const drawer = screen.getByRole("dialog");
    expect(within(drawer).getByLabelText("Quantidade")).toHaveValue(1);
    expect(within(drawer).getByText("R$ 70,00")).toBeInTheDocument();
    page.unmount();

    render(
      <CartProvider>
        <CheckoutPage />
        <SelectionDrawer />
      </CartProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Revisar e pedir" })).toBeInTheDocument();
    expect(within(screen.getByRole("main")).getByLabelText("Quantidade")).toHaveValue(1);
    expect(screen.queryByText(/500 g por pão/)).not.toBeInTheDocument();
    expect(screen.getAllByText("R$ 70,00").length).toBeGreaterThan(0);
    expect(screen.queryByText("R$ 140,00")).not.toBeInTheDocument();
    const stored = JSON.parse(localStorage.getItem(SELECTION_KEY) ?? "[]") as Array<{ quantity: number }>;
    expect(stored).toMatchObject([{ quantity: 1 }]);
  });

  it("na revisão substitui a quantidade, pede nova cotação e não envia o pedido", async () => {
    const user = userEvent.setup();
    sessionStorage.setItem("lojadepaes_preferred_date", "2026-09-30");
    localStorage.setItem(
      SELECTION_KEY,
      JSON.stringify([
        {
          key: "line-1",
          slug: "rolled-bread",
          variantId: "pepperoni-500",
          quantity: 1,
          adaptation: { text: "sem gergelim", reason: "preference" },
          custom: null,
        },
      ]),
    );
    render(
      <CartProvider>
        <CheckoutPage />
      </CartProvider>,
    );
    expect(await screen.findByRole("heading", { name: "Revisar e pedir" })).toBeInTheDocument();
    expect(await screen.findByText(/Total R\$ 70,00/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Nome de quem pede"), "Ana Isolada");
    await user.type(screen.getByLabelText("E-mail para acompanhar o pedido"), "ana-isolada@example.test");
    await user.click(screen.getByRole("button", { name: "Aumentar quantidade" }));
    expect(await screen.findByText(/Total R\$ 140,00/)).toBeInTheDocument();
    expect(screen.getByLabelText("Quantidade")).toHaveValue(2);
    expect(screen.getByLabelText("Nome de quem pede")).toHaveValue("Ana Isolada");
    expect(screen.getByText(/sem gergelim/)).toBeInTheDocument();
    const stored = JSON.parse(localStorage.getItem(SELECTION_KEY) ?? "[]") as Array<{ quantity: number }>;
    expect(stored).toMatchObject([{ quantity: 2 }]);
    expect(screen.getByRole("button", { name: "Enviar pedido" })).toBeEnabled();
  });

  it("nova inclusão soma e avisa; editar a quantidade define 1 de novo", async () => {
    const user = userEvent.setup();
    render(
      <CartProvider>
        <ProductPage slug="rolled-bread" />
        <SelectionDrawer ordersEnabled />
      </CartProvider>,
    );
    await screen.findByRole("heading", { name: pepperoni.name });
    await user.click(screen.getByRole("button", { name: "Adicionar à seleção" }));
    await user.click(screen.getByRole("button", { name: "Adicionar à seleção" }));
    expect(await screen.findByText("Adicionado 1 pão. Você tem 2 deste pão no carrinho.")).toBeInTheDocument();
    const quantity = within(screen.getByRole("dialog")).getByLabelText("Quantidade");
    expect(quantity).toHaveValue(2);
    fireEvent.change(quantity, { target: { value: "1" } });
    await waitFor(() => expect(quantity).toHaveValue(1));
    expect(within(screen.getByRole("dialog")).getByText("R$ 70,00")).toBeInTheDocument();
  });
});
