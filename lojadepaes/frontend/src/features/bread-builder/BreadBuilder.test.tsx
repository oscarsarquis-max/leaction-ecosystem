import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CartProvider } from "../../shop/CartContext";
import { BreadBuilder } from "./BreadBuilder";

vi.mock("./builderApi", () => ({
  fetchBuilderCatalog: vi.fn(async () => ({
    price_cents: 7000,
    weight_grams: 500,
    currency: "BRL",
    fulfillment: "pickup",
    doughs: [
      { id: "d1", name: "Maturada (Long fermentation)", description: "descansa mais tempo", recipe_base_pending: false },
      { id: "d2", name: "Sovada (Kneaded dough)", description: "trabalhada à mão", recipe_base_pending: false },
      { id: "d3", name: "Fermentação natural curta (Classic sourdough)", description: "preparo mais curto", recipe_base_pending: false },
    ],
    flours: [
      { id: "f1", name: "Branca (Strong white)", description: "Farinha branca de trigo.", assistant_role: "flour", compatible_dough_ids: [], compatibility_pending: true },
      { id: "f2", name: "Integral de trigo (Whole wheat)", description: "Farinha de trigo integral.", assistant_role: "flour", compatible_dough_ids: [], compatibility_pending: true },
      { id: "f3", name: "Integral de centeio (Whole rye)", description: "Farinha de centeio integral.", assistant_role: "flour", compatible_dough_ids: [], compatibility_pending: true },
      { id: "f4", name: "Fubá (Corn)", description: "Farinha de milho.", assistant_role: "flour", compatible_dough_ids: [], compatibility_pending: true },
    ],
    ingredients: [
      { id: "i1", name: "Nozes", description: "crocância", assistant_role: "inclusion", compatible_dough_ids: ["d1"] },
      { id: "i2", name: "Castanha de caju", description: "amanteigado", assistant_role: "inclusion", compatible_dough_ids: [] },
      { id: "i3", name: "Granola", description: "cereais", assistant_role: "inclusion", compatible_dough_ids: [] },
      { id: "i4", name: "Tomate seco", description: "acidez", assistant_role: "inclusion", compatible_dough_ids: [] },
      { id: "i5", name: "Berinjela", description: "suave", assistant_role: "inclusion", compatible_dough_ids: [] },
      { id: "i6", name: "Queijo parmesão", description: "aromático", assistant_role: "inclusion", compatible_dough_ids: [] },
    ],
    shapes: [
      {
        id: "s1",
        name: "Pão de forma",
        description: "fatias",
        compatible_dough_ids: ["d1"],
        compatibility_pending: false,
      },
    ],
  })),
}));

describe("BreadBuilder", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("coloca a farinha no primeiro passo e os complementos no segundo", async () => {
    const user = userEvent.setup();
    render(
      <CartProvider>
        <BreadBuilder />
      </CartProvider>,
    );

    expect(await screen.findByRole("heading", { name: "Criador de Pães" })).toBeInTheDocument();
    expect(screen.getByText(/elabore sua receita/i)).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Farinha" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Fermentação e preparo" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /branca/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /integral de trigo/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /centeio/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /fubá/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /maturada/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sovada/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /fermentação natural curta/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^integral$/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/multigrãos/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/farinha branca italiana/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /nozes/i })).not.toBeInTheDocument();

    expect(screen.getByRole("button", { name: /escolher os sabores/i })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /branca/i }));
    expect(screen.getByRole("button", { name: /escolher os sabores/i })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /maturada/i }));
    await user.click(screen.getByRole("button", { name: /escolher os sabores/i }));

    expect(screen.getByRole("button", { name: /nozes/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /castanha de caju/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /granola/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /tomate seco/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /berinjela/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /queijo parmesão/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /branca/i })).not.toBeInTheDocument();
  });

  it("preserva farinha, complementos e texto livre ao voltar e revisar", async () => {
    const user = userEvent.setup();
    render(
      <CartProvider>
        <BreadBuilder />
      </CartProvider>,
    );

    await user.click(await screen.findByRole("button", { name: /branca/i }));
    await user.click(screen.getByRole("button", { name: /maturada/i }));
    await user.click(screen.getByRole("button", { name: /escolher os sabores/i }));
    await user.click(screen.getByRole("button", { name: /nozes/i }));
    await user.click(screen.getByRole("button", { name: /granola/i }));
    await user.type(screen.getByPlaceholderText("Ex.: pepperoni…"), "pepperoni");
    expect(screen.getByText(/Pão personalizado: 500 g · R\$\s*70,00 por unidade/)).toBeInTheDocument();
    expect(screen.getByText("9/500")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /escolher a forma/i }));
    await user.click(screen.getByRole("button", { name: /voltar/i }));
    expect(screen.getByRole("button", { name: /nozes/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /granola/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByPlaceholderText("Ex.: pepperoni…")).toHaveValue("pepperoni");
    await user.click(screen.getByRole("button", { name: /voltar/i }));
    expect(screen.getByRole("button", { name: /maturada/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /branca/i })).toHaveAttribute("aria-pressed", "true");

    await user.click(screen.getByRole("button", { name: /escolher os sabores/i }));
    await user.click(screen.getByRole("button", { name: /escolher a forma/i }));
    await user.click(screen.getByRole("button", { name: /pão de forma/i }));
    await user.click(screen.getByRole("button", { name: /combinar o encontro/i }));

    const review = screen.getByRole("button", { name: /revisar pedido/i });
    expect(review).toBeDisabled();
    const enabledDay = screen.getAllByRole("button").find((button) => {
      return button.classList.contains("day") && !button.hasAttribute("disabled");
    });
    expect(enabledDay).toBeTruthy();
    await user.click(enabledDay!);
    expect(review).toBeEnabled();
    await user.click(review);

    expect(screen.getByRole("button", { name: "Ir para identificação e envio" })).toBeInTheDocument();
    expect(screen.getByText(/ainda não envia o pedido/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Branca/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Maturada/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Nozes \+ Granola \+ pepperoni/)).toBeInTheDocument();
    expect(screen.getAllByText(/500 g/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/70,00/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/simulação/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "14h–16h" })).not.toBeInTheDocument();
  });
});
