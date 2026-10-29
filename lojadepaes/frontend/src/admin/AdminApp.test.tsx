import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AdminApiError, unpaidProductionPrompt } from "./api";
import { DateRequestDetailView } from "./DateRequestDetail";
import { OrderDetailView } from "./OrderDetail";
import { OrdersList } from "./OrdersList";
import type { DateRequestDetail, OrderDetail, OrderListResponse } from "./types";

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
    expect(screen.getByText("Nenhum pedido nesta fila de atendimento.")).toBeInTheDocument();
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

  it("mostra solicitações de data na fila e não trata erro da lista como vazio", async () => {
    const user = userEvent.setup();
    const onOpen = vi.fn();
    const onRefresh = vi.fn();
    const onClearFilters = vi.fn();
    const mixed: OrderListResponse = {
      items: [
        {
          id: "15bd4592-0000-4000-8000-000000000001",
          public_reference: "SD15BD4592",
          created_at: "2026-10-05T21:30:00Z",
          status: "pending",
          customer_name: "Cliente da solicitação",
          bread_units: 1,
          fulfillment_modality: null,
          production_batch_id: null,
          production_batch_code: null,
          fulfillment_slot_id: null,
          slot_starts_at: null,
          slot_ends_at: null,
          total: { cents: null, currency: "BRL" },
          financial_kind: "none",
          source: "date_request",
          row_key: "date_request:15bd4592-0000-4000-8000-000000000001",
          desired_date: "2026-10-06",
          context_label: "1× Focaccia Alta (500g)",
          pending_hours: 30,
          overdue: true,
        },
      ],
      page: 1,
      page_size: 20,
      total: 1,
    };
    const { rerender } = render(
      <OrdersList
        filters={{ reference: "", status: "", created_from: "", created_to: "", modality: "" }}
        data={mixed}
        loading={false}
        error={null}
        emptyHint={null}
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={onRefresh}
        onOpen={onOpen}
        onPage={() => undefined}
      />,
    );
    expect(screen.getByText("Solicitação de data")).toBeInTheDocument();
    expect(screen.getAllByText("Sem cobrança").length).toBeGreaterThan(0);
    expect(screen.getByText(/pendente há 30 h/)).toBeInTheDocument();
    expect(screen.queryByText(/Abrir Agenda/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Avaliar e responder" }));
    expect(onOpen).toHaveBeenCalled();

    rerender(
      <OrdersList
        filters={{ reference: "LP", status: "", created_from: "", created_to: "", modality: "" }}
        data={emptyList}
        loading={false}
        error={null}
        emptyHint="filtered"
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={onRefresh}
        onClearFilters={onClearFilters}
        onOpen={() => undefined}
        onPage={() => undefined}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Limpar filtros" }));
    expect(onClearFilters).toHaveBeenCalled();

    rerender(
      <OrdersList
        filters={{ reference: "", status: "", created_from: "", created_to: "", modality: "" }}
        data={null}
        loading={false}
        error="falha ao carregar a lista"
        emptyHint={null}
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={onRefresh}
        onOpen={() => undefined}
        onPage={() => undefined}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("falha ao carregar a lista");
    expect(screen.queryByText("Nenhum pedido nesta fila de atendimento.")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(onRefresh).toHaveBeenCalled();
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

  it("aceita a data pedida, propõe uma alternativa e exige justificativa para encerrar", async () => {
    const onAct = vi.fn();
    const request = {
      id: "15bd4592-0000-4000-8000-000000000001",
      public_reference: "SD15BD4592",
      status: "pending",
      desired_date: "2026-10-06",
      proposed_date: null,
      customer_name: "Cliente da solicitação",
      customer_email: "cliente@example.test",
      intended_quantity: 1,
      message: "quero essa data",
      admin_note: null,
      cart_context: [{ product_name: "Focaccia Alta", variant_name: "500g", quantity: 1 }],
      created_at: "2026-10-05T21:30:00Z",
      events: [{ action: "created", actor_ref: null, detail: "data desejada 2026-10-06", created_at: "2026-10-05T21:30:00Z" }],
      notifications: [{ id: "out-1", kind: "date_request_received", status: "skipped", last_error: "não configurado" }],
      allowed_actions: ["accept", "propose", "close", "request_completion"],
      reply_preview: "Aceitar a data pedida formaliza o pedido.",
      accept_preview: {
        can_accept: true,
        gaps: [],
        desired_date: "2026-10-06",
        accepted_date: "2026-10-06",
        items: [{ product_name: "Focaccia Alta", variant_name: "500g", quantity: 1, unit_cents: 2490, line_cents: 2490 }],
        total_cents: 2490,
        currency: "BRL",
        has_address: false,
        delivery_pending: true,
        converted_order_id: null,
        awaiting_details: false,
      },
    } satisfies DateRequestDetail;
    const user = userEvent.setup();
    render(
      <DateRequestDetailView
        request={request}
        loading={false}
        error={null}
        busyAction={null}
        onBack={() => undefined}
        onReload={() => undefined}
        onAct={onAct}
        onRetry={() => undefined}
      />,
    );
    expect(screen.getByText("SD15BD4592")).toBeInTheDocument();
    expect(screen.getByText(/Sem cobrança até o aceite/)).toBeInTheDocument();
    expect(screen.getByText(/Dados de entrega pendentes/)).toBeInTheDocument();
    expect(screen.queryByText("Cliente avisado")).not.toBeInTheDocument();
    expect(screen.queryByText("Encerrar sem enviar mensagem")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Data alternativa")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Aceitar data solicitada e enviar para pagamento" }));
    expect(onAct).toHaveBeenCalledWith("accept", expect.objectContaining({ address: null }));
    await user.click(screen.getByRole("button", { name: "Propor outra data" }));
    expect(screen.getAllByLabelText("Data alternativa")).toHaveLength(1);
    await user.click(screen.getByRole("button", { name: "Não será possível atender" }));
    expect(screen.getByRole("button", { name: "Enviar justificativa e encerrar" })).toBeDisabled();
    await user.type(screen.getByLabelText("Justificativa ao cliente"), "nessa data não dá");
    await user.click(screen.getByRole("button", { name: "Enviar justificativa e encerrar" }));
    expect(onAct).toHaveBeenCalledWith("close", { note: "nessa data não dá" });
  });

  it("mostra a quantidade informada e só aceita depois de confirmar o pão", async () => {
    const onAct = vi.fn();
    const onQuote = vi.fn(async () => ({
      can_accept: true,
      gaps: [],
      desired_date: "2026-10-23",
      accepted_date: "2026-10-23",
      items: [
        {
          product_name: "Focaccia Alta",
          variant_name: "500 g",
          quantity: 1,
          unit_cents: 2490,
          line_cents: 2490,
        },
      ],
      total_cents: 2490,
      currency: "BRL",
      has_address: false,
      delivery_pending: true,
      converted_order_id: null,
      awaiting_details: false,
      needs_catalog_choice: true,
      informed_quantity: 1,
      ask_customer: false,
      complementary_pending: ["endereço de entrega", "telefone"],
    }));
    const user = userEvent.setup();
    render(
      <DateRequestDetailView
        request={{
          id: "3cc4c139-0000-4000-8000-000000000100",
          public_reference: "SD3CC4C139",
          status: "pending",
          desired_date: "2026-10-23",
          proposed_date: null,
          customer_name: "Cliente da solicitação",
          customer_email: "cliente@example.test",
          intended_quantity: 1,
          message: "Rolled Bread de pepperoni",
          admin_note: null,
          cart_context: null,
          created_at: "2026-10-20T12:00:00Z",
          events: [],
          notifications: [],
          allowed_actions: ["accept", "propose", "close", "request_completion"],
          reply_preview: null,
          accept_preview: {
            can_accept: false,
            gaps: [
              "A quantidade 1 está informada. O pão está na mensagem. Confirme o produto do catálogo para ver o preço vigente e aceitar.",
            ],
            desired_date: "2026-10-23",
            accepted_date: "2026-10-23",
            items: [],
            total_cents: null,
            currency: "BRL",
            has_address: false,
            delivery_pending: true,
            converted_order_id: null,
            awaiting_details: false,
            needs_catalog_choice: true,
            informed_quantity: 1,
            ask_customer: false,
            suggestion: {
              product_name: "Focaccia Alta",
              variant_name: "500 g",
              variant_id: "variant-500",
              unit_cents: 2490,
              reason: "correspondência única com o nome na mensagem; confirme antes de aceitar",
            },
            catalog_choices: [
              {
                product_id: "product-1",
                variant_id: "variant-500",
                product_name: "Focaccia Alta",
                variant_name: "500 g",
                unit_cents: 2490,
              },
            ],
            complementary_pending: ["endereço de entrega", "telefone"],
          },
        }}
        loading={false}
        error={null}
        busyAction={null}
        onBack={() => undefined}
        onReload={() => undefined}
        onAct={onAct}
        onQuote={onQuote}
      />,
    );
    expect(screen.getByText(/A quantidade 1 está informada/)).toBeInTheDocument();
    expect(screen.queryByText(/faltam os pães/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enviar acesso para o cliente completar" })).not.toBeInTheDocument();
    expect(screen.getByText(/Pendências que não impedem o aceite nem o pagamento/)).toBeInTheDocument();
    expect(await screen.findByText(/24,90/)).toBeInTheDocument();
    const accept = screen.getByRole("button", { name: "Aceitar data solicitada e enviar para pagamento" });
    expect(accept).toBeEnabled();
    await user.click(accept);
    expect(onAct).toHaveBeenCalledWith(
      "accept",
      expect.objectContaining({
        lines: [{ variant_id: "variant-500", quantity: 1 }],
      }),
    );
  });
});

describe("produção sem pagamento", () => {
  const order = {
    id: "11111111-1111-1111-1111-111111111111",
    public_reference: "LPSEM1",
    created_at: "2026-10-21T12:00:00Z",
    updated_at: "2026-10-21T12:00:00Z",
    status: "confirmed",
    allowed_actions: ["start_production", "cancel"],
    visible_label: "Aceito",
    visible_stage: "accepted",
    customer_name: "Cliente fictício",
    customer_email: "ficticio@example.test",
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
    slot_starts_at: null,
    slot_ends_at: null,
    confirmed_at: "2026-10-21T12:00:00Z",
    production_started_at: null,
    ready_at: null,
    completed_at: null,
    cancelled_at: null,
    cancellation_reason: null,
    currency: "BRL",
    subtotal: { cents: 4500, currency: "BRL" },
    delivery_fee: { cents: 0, currency: "BRL" },
    discount: { cents: 0, currency: "BRL" },
    total: { cents: 4500, currency: "BRL" },
    items: [],
    history: [],
    notes: [],
    payment_records: [],
    payment_events: [],
    financial_kind: "open",
    financially_settled: false,
    holds_capacity: true,
    snapshots_locked: true,
    production_local_date: null,
    preferred_time: null,
    proposed_production_date: null,
  } as OrderDetail;

  const prompt = {
    public_reference: "LPSEM1",
    total_cents: 4500,
    currency: "BRL",
    financial_label: "Aguardando pagamento",
    uncertain: false,
  };

  it("volta sem agir e só confirma no segundo botão", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    const onDismiss = vi.fn();
    const onConfirm = vi.fn();
    const view = render(
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
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Iniciar produção" }));
    expect(onAction).toHaveBeenCalledTimes(1);
    expect(onAction).toHaveBeenCalledWith("start_production");

    view.rerender(
      <OrderDetailView
        order={order}
        loading={false}
        error={null}
        conflict={false}
        busyAction={null}
        noteError={null}
        productionPrompt={prompt}
        onDismissProduction={onDismiss}
        onConfirmUnpaidProduction={onConfirm}
        onBack={() => undefined}
        onReload={() => undefined}
        onAction={onAction}
        onNote={() => undefined}
        onEvaluateAdaptation={() => undefined}
      />,
    );
    expect(
      screen.getByRole("dialog", {
        name: "Este pedido ainda não está pago. Deseja iniciar a produção mesmo assim?",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText("Referência LPSEM1")).toBeInTheDocument();
    expect(screen.getByText(/Total:/)).toHaveTextContent("45,00");
    expect(screen.getByText("Condição financeira: Aguardando pagamento")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Voltar" }));
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(onConfirm).not.toHaveBeenCalled();
    expect(onAction).toHaveBeenCalledTimes(1);

    view.rerender(
      <OrderDetailView
        order={order}
        loading={false}
        error={null}
        conflict={false}
        busyAction={null}
        noteError={null}
        productionPrompt={prompt}
        onDismissProduction={onDismiss}
        onConfirmUnpaidProduction={onConfirm}
        onBack={() => undefined}
        onReload={() => undefined}
        onAction={onAction}
        onNote={() => undefined}
        onEvaluateAdaptation={() => undefined}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Iniciar mesmo sem pagamento" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onAction).toHaveBeenCalledTimes(1);
  });

  it("não inventa total quando a resposta não traz valor", () => {
    const error = new AdminApiError(409, "O pagamento deste pedido não pôde ser confirmado.", "unpaid_production", {
      public_reference: "LPSEM1",
      total_cents: null,
      currency: "BRL",
      financial_label: "Estado financeiro desconhecido",
      uncertain: true,
    });
    expect(unpaidProductionPrompt(error)?.total_cents).toBeNull();
    expect(unpaidProductionPrompt(error)?.uncertain).toBe(true);
  });
});
