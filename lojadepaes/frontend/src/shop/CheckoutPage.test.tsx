import { render, screen } from "@testing-library/react";
import { CartProvider } from "./CartContext";
import { CheckoutPage } from "./CheckoutPage";
import { OrderStatusPage } from "./OrderStatusPage";
import { fetchStorefrontOrder } from "./checkoutApi";

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
  };
});

describe("checkout da vitrine", () => {
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
    expect(screen.queryByText("Pago")).not.toBeInTheDocument();
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
