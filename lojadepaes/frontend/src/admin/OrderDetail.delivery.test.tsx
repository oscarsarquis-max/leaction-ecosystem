import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OrderDetailView, type ConfirmDeliveryBody } from "./OrderDetail";
import type { OrderDetail } from "./types";

function today(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: "America/Sao_Paulo" }).format(new Date());
}

function order(extra: Partial<OrderDetail>): OrderDetail {
  const money = { cents: 7000, currency: "BRL" };
  return {
    id: "order",
    public_reference: "LP-TEST",
    status: "in_production",
    created_at: "2026-11-10T20:00:00Z",
    currency: "BRL",
    total: money,
    subtotal: money,
    delivery_fee: { ...money, cents: 0 },
    discount: { ...money, cents: 0 },
    items: [],
    notes: [],
    history: [],
    allowed_actions: ["confirm_delivery"],
    payment_records: [],
    payment_events: [],
    financially_settled: true,
    financial_kind: "settled",
    address: {},
    fulfillment_modality: "delivery",
    holds_capacity: true,
    production_local_date: today(),
    ...extra,
  } as unknown as OrderDetail;
}

function show(row: OrderDetail, handlers: { confirm?: (body: ConfirmDeliveryBody) => Promise<void>; info?: (body: unknown) => Promise<void> }) {
  const onAction = vi.fn();
  render(
    <OrderDetailView
      order={row}
      loading={false}
      error={null}
      conflict={false}
      busyAction={null}
      noteError={null}
      onBack={() => {}}
      onReload={() => {}}
      onAction={onAction}
      onNote={() => {}}
      onEvaluateAdaptation={() => {}}
      onConfirmDelivery={handlers.confirm}
      onUpdateDeliveryInfo={handlers.info as never}
    />,
  );
  return onAction;
}

describe("confirmação de entrega", () => {
  it("sem preencher nada, confirma como antes (mesmo corpo de hoje)", async () => {
    const user = userEvent.setup();
    const confirm = vi.fn(async () => {});
    show(order({}), { confirm });
    await user.click(screen.getByRole("button", { name: "Confirmar entrega" }));
    expect(screen.queryByText(/A fornada registrada é/)).not.toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: "Confirmar entrega" }).at(-1)!);
    expect(confirm).toHaveBeenCalledWith({ align_date_to_delivery: false, align_origin: "customer" });
  });

  it("envia quem recebeu e a observação, sem espaços sobrando", async () => {
    const user = userEvent.setup();
    const confirm = vi.fn(async () => {});
    show(order({}), { confirm });
    await user.click(screen.getByRole("button", { name: "Confirmar entrega" }));
    await user.type(screen.getByLabelText("Quem recebeu (opcional)"), "  Maria   (portaria) ");
    await user.type(screen.getByLabelText("Observação da entrega (opcional)"), "Deixado às 10h20");
    await user.click(screen.getAllByRole("button", { name: "Confirmar entrega" }).at(-1)!);
    expect(confirm).toHaveBeenCalledWith({
      align_date_to_delivery: false,
      align_origin: "customer",
      received_by: "Maria (portaria)",
      note: "Deixado às 10h20",
    });
  });

  it("com fornada em outro dia, mantém o ajuste de data e acrescenta quem recebeu", async () => {
    const user = userEvent.setup();
    const confirm = vi.fn(async () => {});
    show(order({ production_local_date: "2026-01-02" }), { confirm });
    await user.click(screen.getByRole("button", { name: "Confirmar entrega" }));
    expect(screen.getByText(/A fornada registrada é/)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Quem recebeu (opcional)"), "João");
    await user.click(screen.getAllByRole("button", { name: "Confirmar entrega" }).at(-1)!);
    expect(confirm).toHaveBeenCalledWith({ align_date_to_delivery: true, align_origin: "customer", received_by: "João" });
  });

  it("depois de entregue mostra quem recebeu e permite corrigir", async () => {
    const user = userEvent.setup();
    const info = vi.fn(async () => {});
    show(
      order({
        status: "completed",
        allowed_actions: [],
        delivery_confirmed_at: "2026-11-13T13:20:00Z",
        delivery_received_by: "Maria",
        delivery_note: null,
      }),
      { info },
    );
    expect(screen.getByText(/Recebido por Maria/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Editar dados da entrega" }));
    const field = screen.getByLabelText("Quem recebeu (opcional)");
    await user.clear(field);
    await user.type(field, "Maria Souza");
    await user.click(screen.getByRole("button", { name: "Salvar dados da entrega" }));
    expect(info).toHaveBeenCalledWith({ received_by: "Maria Souza", note: null });
  });
});
