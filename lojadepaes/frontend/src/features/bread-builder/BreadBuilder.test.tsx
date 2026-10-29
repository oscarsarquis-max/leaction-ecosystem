import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CartProvider } from "../../shop/CartContext";
import { BreadBuilder } from "./BreadBuilder";

vi.mock("../../shop/operationsApi", () => ({
  fetchOperations: vi.fn(async () => ({
    preview_protection: false,
    orders_enabled: true,
    payments_enabled: true,
    date_requests_enabled: true,
    house_fidelity_active: true,
    business_date: "2026-10-01",
    message: null,
  })),
}));

vi.mock("../../shop/calendarApi", () => ({
  previewCalendar: vi.fn(async (payload: { start?: string } = {}) => {
    const start = payload.start ?? "2026-10-01";
    const date = `${start.slice(0, 8)}07`;
    return {
      occupancy_enabled: true,
      reservation_policy: "admin_accept",
      timezone: "America/Sao_Paulo",
      selected_date: null,
      selected_status: null,
      full_message: null,
      alternatives: [],
      notice: null,
      days: [
        {
          date,
          status: "available",
          origin: "default",
          daily_physical_limit: 8,
          daily_base_limit: 4,
          committed_physical: 0,
          remaining_physical: 8,
          reason: "none",
          accessible_label: `${date}: fornada disponível`,
          weekday_name: "quarta",
          eligible: true,
          windows: [],
        },
      ],
    };
  }),
}));

const fetchBuilderProposal = vi.fn();
const fetchBuilderTip = vi.fn();

vi.mock("./builderApi", () => ({
  fetchBuilderProposal: (...args: unknown[]) => fetchBuilderProposal(...args),
  fetchBuilderTip: (...args: unknown[]) => fetchBuilderTip(...args),
  fetchBuilderCatalog: vi.fn(async () => ({
    price_cents: 7000,
    weight_grams: 500,
    currency: "BRL",
    fulfillment: "delivery",
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
    sessionStorage.clear();
    fetchBuilderProposal.mockReset();
    fetchBuilderTip.mockReset();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo) => {
        const url = String(input);
        if (url.includes("/gigio/status")) {
          return { ok: true, json: async () => ({ enabled: true }) } as Response;
        }
        return { ok: false, json: async () => ({}) } as Response;
      }),
    );
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

    expect(await screen.findByText(/A Loja faz somente entregas/)).toBeInTheDocument();
    expect(screen.queryByText(/retirada é a modalidade/i)).not.toBeInTheDocument();
    const review = screen.getByRole("button", { name: /revisar pedido/i });
    expect(review).toBeDisabled();
    const enabledDay = await screen.findByRole("button", { name: /fornada disponível/ });
    await user.click(enabledDay);
    expect(review).toBeEnabled();
    await user.click(review);

    expect(screen.getByRole("button", { name: "Adicionar ao carrinho" })).toBeInTheDocument();
    expect(screen.getByText(/ainda não envia o pedido/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Branca/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Maturada/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Nozes \+ Granola \+ pepperoni/)).toBeInTheDocument();
    expect(screen.getAllByText(/500 g/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/70,00/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/simulação/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "14h–16h" })).not.toBeInTheDocument();
  });

  it("carrega a proposta do Gigio sem criar pedido", async () => {
    fetchBuilderProposal.mockResolvedValue({
      token_ok: true,
      flour_id: "f1",
      flour_name: "Branca (Strong white)",
      dough_id: "d3",
      dough_name: "Fermentação natural curta (Classic sourdough)",
      ingredient_ids: ["i6"],
      ingredient_names: ["Queijo parmesão"],
      shape_id: "s1",
      shape_name: "Pão de forma",
      free_text: "",
      needs_choice: [],
      dropped: [],
      notice: "Sugestão do Gigio. Você pode alterar.",
      source: "gigio",
    });
    render(
      <CartProvider>
        <BreadBuilder />
      </CartProvider>,
    );
    await screen.findByRole("heading", { name: "Criador de Pães" });
    window.dispatchEvent(new CustomEvent("lojadepaes:builder-proposal", { detail: { token: "abc.token" } }));
    expect(await screen.findByRole("status")).toHaveTextContent(/Sugestão do Gigio/);
    expect(screen.getByRole("button", { name: /branca/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /fermentação natural curta/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("button", { name: "Adicionar ao carrinho" })).not.toBeInTheDocument();
  });

  it("não sobrescreve composição existente sem escolha", async () => {
    const user = userEvent.setup();
    fetchBuilderProposal.mockResolvedValue({
      token_ok: true,
      flour_id: "f2",
      flour_name: "Integral de trigo (Whole wheat)",
      dough_id: "d3",
      dough_name: "Fermentação natural curta (Classic sourdough)",
      ingredient_ids: [],
      ingredient_names: [],
      shape_id: "s1",
      shape_name: "Pão de forma",
      free_text: "",
      needs_choice: [],
      dropped: [],
      notice: "Sugestão do Gigio. Você pode alterar.",
      source: "gigio",
    });
    render(
      <CartProvider>
        <BreadBuilder />
      </CartProvider>,
    );
    await user.click(await screen.findByRole("button", { name: /branca/i }));
    await user.click(screen.getByRole("button", { name: /maturada/i }));
    window.dispatchEvent(new CustomEvent("lojadepaes:builder-proposal", { detail: { token: "other.token" } }));
    expect(await screen.findByText(/já está montando outro pão/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Manter o atual" }));
    expect(screen.getByRole("button", { name: /branca/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /maturada/i })).toHaveAttribute("aria-pressed", "true");
  });

  it("mostra a dica da composição atual e aplica só o que foi apresentado", async () => {
    const user = userEvent.setup();
    fetchBuilderTip.mockResolvedValue({
      ok: true,
      observation: "Farinha branca com fermentação natural curta está no Criador.",
      serving: "Fatie e monte sanduíches.",
      composition: {
        flour: "Branca (Strong white)",
        preparation: "Fermentação natural curta (Classic sourdough)",
        inclusions: [],
        shape: "Pão de forma",
        note: "",
      },
      suggestion: {
        label: "Incluir queijo parmesão na massa",
        changes: [{ field: "inclusions", from: "sem complementos", to: "Queijo parmesão" }],
        patch: {
          flour_id: "f1",
          flour_name: "Branca (Strong white)",
          dough_id: "d3",
          dough_name: "Fermentação natural curta (Classic sourdough)",
          ingredient_ids: ["i6"],
          ingredient_names: ["Queijo parmesão"],
          shape_id: "s1",
          shape_name: "Pão de forma",
        },
      },
      cta: null,
      notice: "",
    });
    render(
      <CartProvider>
        <BreadBuilder />
      </CartProvider>,
    );
    await user.click(await screen.findByRole("button", { name: /branca/i }));
    await user.click(screen.getByRole("button", { name: /fermentação natural curta/i }));
    await user.click(screen.getByRole("button", { name: /escolher os sabores/i }));
    await user.click(screen.getByRole("button", { name: /escolher a forma/i }));
    expect(await screen.findByText(/Escolha o formato acima para o Gigio/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /pão de forma/i }));
    expect(await screen.findByText(/Farinha branca com fermentação natural/)).toBeInTheDocument();
    expect(screen.getByText("Uma dica do Gigio para o seu pão")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /combinar o encontro/i })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Aplicar sugestão" }));
    await user.click(screen.getByRole("button", { name: /voltar/i }));
    expect(screen.getByRole("button", { name: /queijo parmesão/i })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByPlaceholderText("Ex.: pepperoni…")).toHaveValue("");
  });
});
