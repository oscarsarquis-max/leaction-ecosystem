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
    expect(row?.querySelector('[data-label="Financeiro"]')).toHaveTextContent("Pagamento: Sem cobrança");
  });

  it("sinaliza adaptação pendente na lista sem detalhar a restrição", () => {
    const data: OrderListResponse = {
      items: [
        {
          id: "11111111-1111-1111-1111-111111111111",
          public_reference: "LPADAPT",
          created_at: "2026-09-16T12:00:00Z",
          status: "submitted",
          customer_name: "Cliente demonstração",
          bread_units: 1,
          fulfillment_modality: "pickup",
          production_batch_id: null,
          production_batch_code: null,
          fulfillment_slot_id: null,
          slot_starts_at: null,
          slot_ends_at: null,
          total: { cents: 2490, currency: "BRL" },
          financial_kind: "open",
          adaptation_attention: true,
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
    expect(screen.getByText("Adaptação: Aguardando avaliação")).toBeInTheDocument();
    expect(screen.queryByText(/gergelim|lactose|glúten/i)).not.toBeInTheDocument();
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
      production_local_date: null,
      preferred_time: null,
      proposed_production_date: null,
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
        onEvaluateAdaptation={() => undefined}
      />,
    );
    expect(screen.getAllByText((_, node) => node?.textContent?.includes("Não calculado") ?? false).length).toBeGreaterThan(
      0,
    );
    expect(screen.getAllByText("Pagamento: Sem cobrança").length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: /cobrar|aprovar pagamento|gerar link|estornar/i })).toBeNull();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    const confirmCancel = screen.getByRole("button", { name: "Confirmar cancelamento" });
    expect(confirmCancel).toBeDisabled();
    await user.type(screen.getByLabelText(/Motivo do cancelamento/), "cliente desistiu");
    await user.click(confirmCancel);
    expect(onAction).toHaveBeenCalledWith("cancel", "cliente desistiu");
  });

  it("não diz que o pedido mudou quando a agenda impede o aceite", async () => {
    const order = {
      id: "11111111-1111-1111-1111-111111111111",
      public_reference: "LP6D0411EE5C",
      created_at: "2026-09-26T12:32:32Z",
      updated_at: "2026-09-26T12:32:32Z",
      status: "submitted",
      allowed_actions: ["confirm", "cancel"],
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
      fulfillment_modality: "delivery",
      production_batch_code: null,
      slot_starts_at: null,
      slot_ends_at: null,
      confirmed_at: null,
      production_started_at: null,
      ready_at: null,
      completed_at: null,
      cancelled_at: null,
      cancellation_reason: null,
      currency: "BRL",
      subtotal: { cents: 7000, currency: "BRL" },
      delivery_fee: { cents: 0, currency: "BRL" },
      discount: { cents: 0, currency: "BRL" },
      total: { cents: 7000, currency: "BRL" },
      items: [
        {
          id: "22222222-2222-2222-2222-222222222222",
          dough_name: "Rolled Bread de Pepperoni",
          shape_name: "500 g",
          quantity: 1,
          unit_price: { cents: 7000, currency: "BRL" },
          line_total: { cents: 7000, currency: "BRL" },
          extras: [],
          origin: "product",
          weight_grams: 500,
          snapshot_complete: true,
          provisional: false,
        },
      ],
      history: [],
      notes: [],
      payment_records: [],
      payment_events: [],
      financial_kind: "settled",
      financially_settled: true,
      holds_capacity: false,
      snapshots_locked: true,
      production_local_date: "2026-09-27",
      preferred_time: "16:30",
      proposed_production_date: null,
    } satisfies OrderDetail;

    const { rerender } = render(
      <OrderDetailView
        order={order}
        loading={false}
        error="domingo, 27 de setembro: indisponível para esta seleção"
        conflict={false}
        busyAction={null}
        noteError={null}
        onBack={() => undefined}
        onReload={() => undefined}
        onAction={() => undefined}
        onNote={() => undefined}
        onEvaluateAdaptation={() => undefined}
      />,
    );
    expect(screen.queryByText(/pedido mudou/i)).not.toBeInTheDocument();
    expect(screen.getByText(/27 de setembro/)).toBeInTheDocument();
    expect(screen.getByText(/não vinculada neste fluxo/i)).toBeInTheDocument();
    expect(screen.getByText(/preferência, não uma janela confirmada/i)).toBeInTheDocument();

    rerender(
      <OrderDetailView
        order={order}
        loading={false}
        error={null}
        conflict
        busyAction={null}
        noteError={null}
        onBack={() => undefined}
        onReload={() => undefined}
        onAction={() => undefined}
        onNote={() => undefined}
        onEvaluateAdaptation={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: "Atualizar pedido" })).toBeInTheDocument();

    const onAction = vi.fn();
    rerender(
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
        onEvaluateAdaptation={() => undefined}
      />,
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "Aceitar e reservar a data" }));
    expect(onAction).toHaveBeenCalledWith("confirm");
  });
});
