import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PartnerOrders } from "./PartnerOrders";
import { partnerApi, type PartnerOrder } from "./partnerApi";

const order: PartnerOrder = {
  id: "o1",
  public_reference: "PC-1",
  combo_ref: "CB-1",
  product_name: "Queijo meia cura 500 g",
  house_product_name: "Fermentação natural",
  requested_date: "2030-01-15",
  customer_name: "Ana Souza",
  address_line: "Rua A, 10 · Centro · Fortaleza/CE",
  item_quantity: 1,
  item_cents: 5800,
  freight_cents: 1200,
  fee_cents: 250,
  status: "submitted",
  accept_deadline: "2030-01-13T15:00:00Z",
};

beforeEach(() => {
  vi.spyOn(partnerApi, "orders").mockResolvedValue([order]);
});
afterEach(() => vi.restoreAllMocks());

describe("pedidos do parceiro", () => {
  it("com quantidade, o valor do produto já vem total e o recebimento soma o frete uma vez", async () => {
    vi.mocked(partnerApi.orders).mockResolvedValue([{ ...order, item_quantity: 2, item_cents: 11600 }]);
    render(<PartnerOrders onBack={vi.fn()} />);
    const card = (await screen.findByText(/Queijo meia cura 500 g/)).closest("li") as HTMLElement;
    expect(within(card).getByText(/^2 ×/)).toBeInTheDocument();
    const receive = within(card).getByLabelText("Seu recebimento no pedido PC-1");
    expect(within(receive).getByText("Seu produto (2 un.)")).toBeInTheDocument();
    expect(within(receive).getByText("R$ 125,50")).toBeInTheDocument();
  });

  it("mostra só a parte do parceiro e confirma", async () => {
    const user = userEvent.setup();
    vi.spyOn(partnerApi, "acceptOrder").mockResolvedValue({ ...order, status: "accepted" });
    render(<PartnerOrders onBack={vi.fn()} />);
    const card = (await screen.findByText("Queijo meia cura 500 g")).closest("li") as HTMLElement;
    const receive = within(card).getByLabelText("Seu recebimento no pedido PC-1");
    expect(within(receive).getByText("R$ 67,50")).toBeInTheDocument();
    expect(within(card).queryByText(/R\$ 36,00|R\$ 8,00|R\$ 114,00/)).toBeNull();
    await user.click(within(card).getByRole("button", { name: "Confirmar entrega nesta data" }));
    expect(partnerApi.acceptOrder).toHaveBeenCalledWith("o1");
    expect(await screen.findByText(/Pedido confirmado/)).toBeInTheDocument();
  });

  it("recusa exige motivo", async () => {
    const user = userEvent.setup();
    vi.spyOn(partnerApi, "refuseOrder").mockResolvedValue({ ...order, status: "refused", refuse_reason: "Sem estoque" });
    render(<PartnerOrders onBack={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "Não consigo" }));
    await user.click(screen.getByRole("button", { name: "Recusar pedido" }));
    expect(screen.getByText("Diga ao cliente por que não vai dar.")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Motivo (o cliente vê)"), "Sem estoque");
    await user.click(screen.getByRole("button", { name: "Recusar pedido" }));
    expect(partnerApi.refuseOrder).toHaveBeenCalledWith("o1", "Sem estoque");
  });
});
