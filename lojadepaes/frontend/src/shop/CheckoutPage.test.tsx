import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CartProvider } from "./CartContext";
import { CheckoutPage } from "./CheckoutPage";
import { OrderStatusPage } from "./OrderStatusPage";
import { SELECTION_KEY } from "./selection";
import { fetchStorefrontOrder, quoteOrder, reconcileStorefrontOrder, submitOrder } from "./checkoutApi";

vi.mock("./calendarApi", () => ({
  previewCalendar: vi.fn(async () => ({
    occupancy_enabled: true,
    reservation_policy: "admin_accept",
    timezone: "America/Sao_Paulo",
    selected_date: null,
    selected_status: null,
    full_message: null,
    alternatives: [],
    notice: null,
    days: [],
  })),
}));

vi.mock("./checkoutApi", async () => {
  const actual = await vi.importActual<typeof import("./checkoutApi")>("./checkoutApi");
  return {
    ...actual,
    fetchStorefrontOrder: vi.fn(),
    startStorefrontCheckout: vi.fn(),
    reconcileStorefrontOrder: vi.fn(),
    quoteOrder: vi.fn(),
    submitOrder: vi.fn(),
  };
});

vi.mock("../features/bread-builder/builderApi", () => ({
  fetchBuilderCatalog: vi.fn(async () => ({
    price_cents: 7000,
    weight_grams: 500,
    currency: "BRL",
    fulfillment: "pickup",
    doughs: [{ id: "dough-1", name: "Sovada (Kneaded dough)", description: "" }],
    flours: [{ id: "flour-1", name: "Branca (Strong white)", description: "", assistant_role: "flour" }],
    ingredients: [],
    shapes: [{ id: "shape-1", name: "Rústico de cesto", description: "" }],
  })),
}));

describe("checkout da vitrine", () => {
  it("pede nome e e-mail antes de enviar o personalizado e não chama a API", async () => {
    const user = userEvent.setup();
    sessionStorage.setItem("lojadepaes_preferred_date", "2026-10-07");
    localStorage.setItem(
      SELECTION_KEY,
      JSON.stringify([
        {
          key: "custom-1",
          slug: "pao-personalizado",
          variantId: "",
          quantity: 1,
          adaptation: null,
          custom: {
            doughTypeId: "dough-1",
            breadShapeId: "shape-1",
            ingredientIds: ["flour-1"],
            doughName: "Sovada (Kneaded dough)",
            shapeName: "Rústico de cesto",
            ingredientNames: ["Branca (Strong white)"],
            flourId: "flour-1",
            flourName: "Branca (Strong white)",
            weightGrams: 500,
            unitCents: 7000,
          },
        },
      ]),
    );
    vi.mocked(quoteOrder).mockResolvedValue({
      requested_date: "2026-10-07",
      currency: "BRL",
      subtotal_cents: 7000,
      total_cents: 7000,
      date_label: "quarta-feira",
      occupies_capacity: true,
      notice: null,
      items: [],
    });
    render(
      <CartProvider>
        <CheckoutPage />
      </CartProvider>,
    );
    expect(
      await screen.findByText(
        "Usaremos este e-mail para avisar sobre a avaliação do seu pão e enviar o acesso ao pagamento após o aceite.",
      ),
    ).toBeInTheDocument();
    const send = await screen.findByRole("button", { name: "Enviar pedido para avaliação" });
    await vi.waitFor(() => expect(send).toBeEnabled());
    await user.click(send);
    expect(await screen.findByText("Informe o nome de quem pede.")).toBeInTheDocument();
    expect(submitOrder).not.toHaveBeenCalled();
    await user.type(screen.getByLabelText("Nome de quem pede"), "Ana Isolada");
    await user.click(screen.getByRole("button", { name: "Enviar pedido para avaliação" }));
    expect(await screen.findByText("Informe um e-mail para acompanhar o pedido.")).toBeInTheDocument();
    expect(screen.getByLabelText("Nome de quem pede")).toHaveValue("Ana Isolada");
    expect(submitOrder).not.toHaveBeenCalled();
  });

  it("pede seleção antes de enviar o pedido", () => {
    render(
      <CartProvider>
        <CheckoutPage />
      </CartProvider>,
    );
    expect(screen.getByText(/Sua seleção está vazia/)).toBeInTheDocument();
    expect(screen.getByText(/Pagar não confirma a fornada/)).toBeInTheDocument();
  });

  it("mostra Pix sem marcar o pedido como pago no navegador", async () => {
    vi.mocked(fetchStorefrontOrder).mockResolvedValue({
      public_reference: "LPTEST",
      status: "submitted",
      visitor_state: "payment_processing",
      requested_date: "2026-09-23",
      proposed_date: null,
      confirmed: false,
      holds_capacity: false,
      financially_settled: false,
      customer_name: "Ana",
      customer_email: "ana@example.com",
      delivery_address: null,
      total_cents: 2490,
      currency: "BRL",
      items: [{ product_name: "Pão teste", variant_name: "500 g", quantity: 1, line_cents: 2490 }],
      payment: {
        financial_status: "pending",
        expected_cents: 2490,
        amount_paid_cents: null,
        external_reference: "hub-1",
        sanitized_error: null,
        method: "pix",
        pix: {
          qr_code: "00020126pix",
          qr_code_base64: null,
          ticket_url: null,
          date_of_expiration: "2026-09-20T18:00:00-03:00",
          mp_payment_id: "9",
        },
      },
      notice: "Após o pagamento, vamos conferir",
    });
    render(
      <CartProvider>
        <OrderStatusPage reference="LPTEST" />
      </CartProvider>,
    );
    expect(await screen.findByText("Código Pix")).toBeInTheDocument();
    expect(screen.getByText(/Esta tela não marca o pedido como pago/)).toBeInTheDocument();
    expect(screen.getByText(/Abra o aplicativo do seu banco/)).toBeInTheDocument();
    expect(screen.queryByText("Pagamento: Pago")).not.toBeInTheDocument();
    expect(screen.getByText("Pagamento: Aguardando confirmação")).toBeInTheDocument();
    expect(screen.getByText("Encomenda: Aguardando avaliação de A Loja")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Verificar pagamento" })).toBeInTheDocument();
  });

  it("mostra pagamento e encomenda separados quando o Pix já foi conciliado", async () => {
    vi.mocked(fetchStorefrontOrder).mockResolvedValue({
      public_reference: "LPAGO",
      status: "submitted",
      visitor_state: "paid_awaiting_accept",
      requested_date: "2026-09-27",
      proposed_date: null,
      confirmed: false,
      holds_capacity: false,
      financially_settled: true,
      customer_name: "Ana",
      customer_email: "ana@example.com",
      delivery_address: null,
      total_cents: 7000,
      currency: "BRL",
      items: [
        {
          product_name: "Pão",
          variant_name: "unidade",
          quantity: 1,
          line_cents: 7000,
          adaptation: {
            status: "pending",
            customer_text: "sem sal",
            reason: "preference",
            bakery_response: "",
            client_decision: null,
            applies_to_all_units_of_this_line: true,
          },
        },
      ],
      payment: {
        financial_status: "paid",
        expected_cents: 7000,
        amount_paid_cents: 7000,
        external_reference: "hub-1",
        sanitized_error: null,
        method: "pix",
        pix: null,
      },
      notice: "Recebemos seu pagamento.",
    });
    render(
      <CartProvider>
        <OrderStatusPage reference="LPAGO" />
      </CartProvider>,
    );
    expect(
      await screen.findByText(
        "Recebemos seu pagamento. A Loja está avaliando sua encomenda e confirmará a data.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Pagamento: Pago")).toBeInTheDocument();
    expect(screen.getByText("Encomenda: Aguardando avaliação de A Loja")).toBeInTheDocument();
    expect(screen.getByText("Adaptação: Aguardando avaliação")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pagar com Pix" })).not.toBeInTheDocument();
    expect(screen.queryByText("Código Pix")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aumentar quantidade" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Quantidade")).not.toBeInTheDocument();
    expect(screen.getByText("1 un.")).toBeInTheDocument();
    expect(screen.getByText(/Total R\$ 70,00/)).toBeInTheDocument();
  });

  it("verificar pagamento consulta o backend e não declara pago se a consulta falha", async () => {
    vi.mocked(fetchStorefrontOrder).mockResolvedValue({
      public_reference: "LPTEST",
      status: "submitted",
      visitor_state: "payment_processing",
      requested_date: "2026-09-27",
      proposed_date: null,
      confirmed: false,
      holds_capacity: false,
      financially_settled: false,
      customer_name: "Ana",
      customer_email: "ana@example.com",
      delivery_address: null,
      total_cents: 7000,
      currency: "BRL",
      items: [{ product_name: "Pão", variant_name: "unidade", quantity: 1, line_cents: 7000 }],
      payment: {
        financial_status: "pending",
        expected_cents: 7000,
        amount_paid_cents: null,
        external_reference: "hub-1",
        sanitized_error: null,
        method: "pix",
        pix: null,
      },
      notice: "Aguardando",
    });
    vi.mocked(reconcileStorefrontOrder).mockRejectedValue(new Error("hub"));
    const user = userEvent.setup();
    render(
      <CartProvider>
        <OrderStatusPage reference="LPTEST" />
      </CartProvider>,
    );
    await user.click(await screen.findByRole("button", { name: "Verificar pagamento" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Não foi possível consultar o pagamento. Isso não marca o pedido como pago.",
    );
    expect(screen.getByText("Pagamento: Aguardando confirmação")).toBeInTheDocument();
  });

  it("mostra a adaptação no pedido protegido sem tratar proposta como aceite", async () => {
    vi.mocked(fetchStorefrontOrder).mockResolvedValue({
      public_reference: "LPADAPT",
      status: "submitted",
      visitor_state: "awaiting_payment",
      requested_date: "2026-09-23",
      proposed_date: null,
      confirmed: false,
      holds_capacity: false,
      financially_settled: false,
      customer_name: "Ana",
      customer_email: "ana@example.com",
      delivery_address: null,
      total_cents: 2490,
      currency: "BRL",
      items: [
        {
          id: "item-1",
          product_name: "Pão teste",
          variant_name: "500 g",
          quantity: 1,
          line_cents: 2490,
          adaptation: {
            status: "alternative_proposed",
            customer_text: "retirar gergelim",
            reason: "dietary_restriction",
            bakery_response: "podemos assar sem gergelim por cima",
            client_decision: null,
            applies_to_all_units_of_this_line: true,
          },
        },
      ],
      payment: {
        financial_status: "pending",
        expected_cents: 2490,
        amount_paid_cents: null,
        external_reference: null,
        sanitized_error: null,
        method: null,
        pix: null,
      },
      notice: "Há adaptação pendente de avaliação",
    });
    render(
      <CartProvider>
        <OrderStatusPage reference="LPADAPT" />
      </CartProvider>,
    );
    expect(await screen.findByText("retirar gergelim")).toBeInTheDocument();
    expect(screen.getByText(/Silêncio não confirma/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Concordar com a alternativa" })).toBeInTheDocument();
  });
});
