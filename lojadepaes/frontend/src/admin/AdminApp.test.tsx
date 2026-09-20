import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OrderDetailView } from "./OrderDetail";
import { OrdersList } from "./OrdersList";
import type { OrderDetail, OrderListResponse } from "./types";

const emptyList: OrderListResponse = { items: [], page: 1, page_size: 20, total: 0 };

describe("gestão de pedidos", () => {
  it("mostra o acesso do cabeçalho com login e senha", async () => {
    const user = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: async () => JSON.stringify({ detail: "não autenticado" }),
      }),
    );
    const { HeaderAccount } = await import("../components/HeaderAccount");
    render(<HeaderAccount />);
    await user.type(await screen.findByLabelText("Usuário"), "padaria");
    await user.click(screen.getByRole("button", { name: "Avançar" }));
    await user.type(screen.getByLabelText("Senha"), "secreta");
    await user.click(screen.getByRole("button", { name: "Entrar" }));
    expect(screen.getByLabelText("Senha")).toHaveAttribute("autocomplete", "current-password");
  });

  it("distingue lista vazia de filtro sem resultado", () => {
    const { rerender } = render(
      <OrdersList
        filters={{ reference: "", status: "", created_from: "", created_to: "", modality: "" }}
        data={emptyList}
        loading={false}
        error={null}
        emptyHint="none"
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={() => undefined}
        onOpen={() => undefined}
        onPage={() => undefined}
      />,
    );
    expect(screen.getByText("Nenhum pedido ainda.")).toBeInTheDocument();
    rerender(
      <OrdersList
        filters={{ reference: "LP", status: "", created_from: "", created_to: "", modality: "" }}
        data={emptyList}
        loading={false}
        error={null}
        emptyHint="filtered"
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={() => undefined}
        onOpen={() => undefined}
        onPage={() => undefined}
      />,
    );
    expect(screen.getByText("Nenhum pedido com esses filtros.")).toBeInTheDocument();
  });

  it("mantém identificação e ações de cada pedido para o layout em cartão", () => {
    const data: OrderListResponse = {
      items: [
        {
          id: "11111111-1111-1111-1111-111111111111",
          public_reference: "LPDEMO1",
          created_at: "2026-09-16T12:00:00Z",
          status: "confirmed",
          customer_name: "Cliente demonstração",
          bread_units: 2,
          fulfillment_modality: "pickup",
          production_batch_id: null,
          production_batch_code: "B-1",
          fulfillment_slot_id: null,
          slot_starts_at: null,
          slot_ends_at: null,
          total: { cents: 4990, currency: "BRL" },
          financial_kind: "none",
        },
      ],
      page: 1,
      page_size: 20,
      total: 1,
    };
    render(
      <OrdersList
        filters={{ reference: "", status: "", created_from: "", created_to: "", modality: "" }}
        data={data}
        loading={false}
        error={null}
        emptyHint={null}
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={() => undefined}
        onOpen={() => undefined}
        onPage={() => undefined}
      />,
    );
    const row = screen.getByRole("button", { name: "LPDEMO1" }).closest("tr");
    expect(row?.querySelector('[data-label="Referência"]')).toBeTruthy();
    expect(row?.querySelector('[data-label="Estado"]')).toHaveTextContent("Confirmado");
    expect(row?.querySelector('[data-label="Financeiro"]')).toHaveTextContent("Sem registro financeiro");
  });

  it("exige motivo para cancelar e não oferece cobrança", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    const order = {
      id: "11111111-1111-1111-1111-111111111111",
      public_reference: "LPDEMO1",
      created_at: "2026-09-16T12:00:00Z",
      updated_at: "2026-09-16T12:00:00Z",
      status: "confirmed",
      allowed_actions: ["start_production", "cancel"],
      customer_name: "Cliente demonstração",
      customer_email: "demo@example.test",
      customer_phone: null,
      address: {
        street: null,
        number: null,
        complement: null,
        district: null,
        city: null,
        state: null,
        postal_code: null,
      },
      customer_note: "",
      fulfillment_modality: "pickup",
      production_batch_code: "B-1",
      slot_starts_at: "2026-09-17T12:00:00Z",
      slot_ends_at: "2026-09-17T14:00:00Z",
      confirmed_at: "2026-09-16T12:00:00Z",
      production_started_at: null,
      ready_at: null,
      completed_at: null,
      cancelled_at: null,
      cancellation_reason: null,
      currency: "BRL",
      subtotal: { cents: null, currency: "BRL" },
      delivery_fee: { cents: null, currency: "BRL" },
      discount: { cents: null, currency: "BRL" },
      total: { cents: null, currency: "BRL" },
      items: [],
      history: [],
      notes: [],
      payment_records: [],
      payment_events: [],
      financial_kind: "none",
      financially_settled: false,
      holds_capacity: true,
      snapshots_locked: true,
    } satisfies OrderDetail;

    render(
      <OrderDetailView
        order={order}
        loading={false}
        error={null}
        conflict={false}
        busyAction={null}
        noteError={null}
        onBack={() => undefined}
        onReload={() => undefined}
        onAction={onAction}
        onNote={() => undefined}
      />,
    );
    expect(screen.getAllByText((_, node) => node?.textContent?.includes("Não calculado") ?? false).length).toBeGreaterThan(
      0,
    );
    expect(screen.getByText("Sem registro financeiro")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /cobrar|aprovar pagamento|gerar link|estornar/i })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    const confirmCancel = screen.getByRole("button", { name: "Confirmar cancelamento" });
    expect(confirmCancel).toBeDisabled();
    await user.type(screen.getByLabelText(/Motivo do cancelamento/), "cliente desistiu");
    await user.click(confirmCancel);
    expect(onAction).toHaveBeenCalledWith("cancel", "cliente desistiu");
  });
});
