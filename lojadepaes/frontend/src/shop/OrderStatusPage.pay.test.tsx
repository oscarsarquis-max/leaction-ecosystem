import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrderStatusPage } from "./OrderStatusPage";
import { fetchStorefrontOrder, reconcileStorefrontOrder, startStorefrontCheckout } from "./checkoutApi";
import { fetchOperations } from "./operationsApi";

vi.mock("./checkoutApi", async () => {
  const actual = await vi.importActual<typeof import("./checkoutApi")>("./checkoutApi");
  return {
    ...actual,
    fetchStorefrontOrder: vi.fn(),
    startStorefrontCheckout: vi.fn(),
    reconcileStorefrontOrder: vi.fn(),
  };
});

vi.mock("./operationsApi", () => ({
  fetchOperations: vi.fn(async () => {
    throw new Error("operations-offline");
  }),
}));

const acceptedUnpaid = {
  public_reference: "LP42TEST",
  status: "in_production",
  visitor_state: "accepted",
  requested_date: "2026-10-06",
  proposed_date: null,
  confirmed: true,
  holds_capacity: true,
  financially_settled: false,
  payment_available: true,
  delivery_pending: true,
  customer_name: "Ana",
  customer_email: "ana@example.com",
  fulfillment_modality: "delivery",
  delivery_address: null,
  total_cents: 9000,
  currency: "BRL",
  items: [{ product_name: "Focaccia Alta", variant_name: "500 g", quantity: 1, line_cents: 9000 }],
  payment: {
    financial_status: "pending",
    expected_cents: 9000,
    amount_paid_cents: null,
    external_reference: null,
    sanitized_error: null,
    method: null,
    pix: null,
  },
  notice: "Você pode pagar agora.",
};

describe("pedido aceito no link do e-mail", () => {
  it("continua verificando um pagamento pendente mesmo depois do aceite", async () => {
    vi.useFakeTimers();
    const pending = {...acceptedUnpaid,payment:{...acceptedUnpaid.payment,external_reference:"hub-test",method:"card"}};
    vi.mocked(fetchStorefrontOrder).mockResolvedValue(pending);
    vi.mocked(reconcileStorefrontOrder).mockResolvedValue(pending);
    try {
      await act(async () => {render(<OrderStatusPage reference="LP42TEST" />);});
      await act(async () => {await vi.advanceTimersByTimeAsync(16000);});
      expect(reconcileStorefrontOrder).toHaveBeenCalledWith("LP42TEST");
      expect(startStorefrontCheckout).not.toHaveBeenCalled();
    } finally {vi.useRealTimers();}
  });
  it("mostra Pix e cartão sem endereço e sem /operations", async () => {
    vi.mocked(fetchStorefrontOrder).mockResolvedValue(acceptedUnpaid);
    render(<OrderStatusPage reference="LP42TEST" />);
    expect(await screen.findByRole("button", { name: "Pagar com Pix" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Pagar com cartão" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Salvar endereço de entrega" })).toBeInTheDocument();
    expect(fetchOperations).toHaveBeenCalledTimes(0);
    const pix = screen.getByRole("button", { name: "Pagar com Pix" });
    const save = screen.getByRole("button", { name: "Salvar endereço de entrega" });
    expect(pix.compareDocumentPosition(save) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("dispara o checkout real ao clicar em Pix", async () => {
    const user = userEvent.setup();
    vi.mocked(fetchStorefrontOrder).mockResolvedValue(acceptedUnpaid);
    vi.mocked(startStorefrontCheckout).mockResolvedValue({
      checkout_url: null,
      external_reference: "hub-71",
      expected_cents: 9000,
      reused: false,
      method: "pix",
      pix: {
        qr_code: "00020126pix71",
        qr_code_base64: "abc",
        ticket_url: null,
        date_of_expiration: "2026-10-06T18:00:00-03:00",
        mp_payment_id: "71",
      },
    });
    render(<OrderStatusPage reference="LP42TEST" />);
    await user.click(await screen.findByRole("button", { name: "Pagar com Pix" }));
    expect(startStorefrontCheckout).toHaveBeenCalledWith("LP42TEST", "pix", false);
  });

  it("pedido cancelado não vira pagamento vazio", async () => {
    vi.mocked(fetchStorefrontOrder).mockResolvedValue({
      ...acceptedUnpaid,
      status: "cancelled",
      visitor_state: "cancelled",
      confirmed: false,
      payment_available: false,
      payment_unavailable_reason: "Este pedido foi cancelado. Não há cobrança a abrir.",
    });
    render(<OrderStatusPage reference="LP42TEST" />);
    expect(await screen.findByText("Este pedido foi cancelado. Não há cobrança a abrir.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pagar com Pix" })).not.toBeInTheDocument();
  });
});
