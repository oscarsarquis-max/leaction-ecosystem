import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OrderDetailView } from "./OrderDetail";
import { historyEventName, isoDatesToBr } from "./format";
import type { OrderDetail } from "./types";

const VOIDED = "Cancelado — registro anulado por duplicidade";

function voidedOrder(): OrderDetail {
  const money = { cents: 7000, currency: "BRL" };
  return {
    id: "order",
    public_reference: "LP-DUP",
    status: "completed",
    visible_stage: "voided",
    visible_label: "Anulado",
    payment_attention: "Pagamento pendente",
    created_at: "2026-10-27T20:00:00Z",
    currency: "BRL",
    total: money,
    subtotal: money,
    delivery_fee: { ...money, cents: 0 },
    discount: { ...money, cents: 0 },
    items: [],
    notes: [],
    history: [
      {
        id: "h1",
        from_status: "completed",
        to_status: "completed",
        reason: "anulado como duplicado de LP-ORIG. Motivo: pedido repetido",
        actor_ref: "gestor",
        created_at: "2026-10-30T12:00:00Z",
      },
      {
        id: "h2",
        from_status: "completed",
        to_status: "completed",
        reason: "Exceção de data. Solicitado 2026-11-18. Operacional 2026-11-18 → 2026-11-20.",
        actor_ref: "gestor",
        created_at: "2026-10-30T12:05:00Z",
      },
    ],
    allowed_actions: [],
    payment_records: [],
    payment_events: [],
    financially_settled: false,
    financial_kind: "open",
    address: {},
    fulfillment_modality: "delivery",
    holds_capacity: false,
    void_banner: { original_reference: "LP-ORIG", original_id: "orig", at: null, actor: null, reason: "repetido em 2026-10-27" },
  } as unknown as OrderDetail;
}

describe("detalhe de pedido anulado", () => {
  it("troca os três textos de pagamento, esconde Recarregar e a nota e usa o nome do evento", () => {
    render(
      <OrderDetailView
        order={voidedOrder()}
        loading={false}
        error={null}
        conflict={false}
        busyAction={null}
        noteError={null}
        onBack={() => {}}
        onReload={() => {}}
        onAction={() => {}}
        onNote={() => {}}
        onEvaluateAdaptation={() => {}}
      />,
    );
    expect(screen.getAllByText(VOIDED)).toHaveLength(3);
    expect(screen.queryByText("Pagamento pendente")).not.toBeInTheDocument();
    expect(screen.queryByText("Pagamento: Em aberto")).not.toBeInTheDocument();
    expect(screen.queryByText("Aguardando confirmação do pagamento")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Recarregar" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Forma e valor recebido serão exibidos/)).not.toBeInTheDocument();
    expect(screen.getByText(/Anulado como duplicado ·/)).toBeInTheDocument();
    expect(screen.getByText(/Exceção de data ·/)).toBeInTheDocument();
    expect(screen.queryByText(/Finalizado → Finalizado/)).not.toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/\d{4}-\d{2}-\d{2}/);
  });

  it("formata datas ISO e nomeia o evento", () => {
    expect(isoDatesToBr("de 2026-11-18 para 2026-11-20")).toBe("de 18/11/2026 para 20/11/2026");
    expect(historyEventName("x anulado como duplicado deste pedido")).toBe("Anulado como duplicado");
  });
});
