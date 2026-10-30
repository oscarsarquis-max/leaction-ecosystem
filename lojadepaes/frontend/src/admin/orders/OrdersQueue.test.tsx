import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { OrderListItem, OrderListResponse, QueueLens } from "../types";
import { OrdersQueue } from "./OrdersQueue";
import { trackAccessibleName } from "./TrackChip";

const lenses: QueueLens[] = [
  { key: "vigentes", label: "Vigentes", count: 3 },
  { key: "work:needs_action", label: "Precisa de ação", count: 1 },
  { key: "stage:open", label: "Abertos", count: 1 },
  { key: "stage:accepted", label: "Aceitos sem pagamento", count: 1 },
  { key: "stage:paid", label: "Pagos", count: 0 },
  { key: "stage:in_production", label: "Em produção", count: 0 },
  { key: "stage:delivered", label: "Entregues", count: 0 },
  { key: "stage:cancelled", label: "Cancelados", count: 0 },
  { key: "all", label: "Todos", count: 4 },
];

const filters = { reference: "", status: "", created_from: "", created_to: "", modality: "", lens: "" };

function item(partial: Partial<OrderListItem> = {}): OrderListItem {
  return {
    id: "11111111-1111-1111-1111-111111111111",
    public_reference: "LPDEMO1",
    created_at: "2026-10-30T12:00:00Z",
    status: "submitted",
    customer_name: "Cliente demonstração",
    bread_units: 1,
    fulfillment_modality: "delivery",
    production_batch_id: null,
    production_batch_code: null,
    fulfillment_slot_id: null,
    slot_starts_at: null,
    slot_ends_at: null,
    total: { cents: 1800, currency: "BRL" },
    financial_kind: "none",
    source: "order",
    visible_stage: "open",
    visible_label: "Aberto",
    items_summary: "Fermentação natural de trigo · 500 g",
    production_local_date: "2026-10-30",
    tracks: {
      commercial: { state: "open", label: "Aberto", tone: "open" },
      payment: { state: "no_charge", label: "Após aceite", tone: "none", hint: "A cobrança abre depois do aceite" },
      production: { state: "not_started", label: "Não iniciada", tone: "none" },
      delivery: { state: "awaiting", label: "Aguardando", tone: "none", hint: "Entrega exige confirmação da equipe" },
    },
    next_action: { code: "accept", label: "Avaliar e aceitar", primary: true },
    ...partial,
  };
}

function list(items: OrderListItem[], extra: Partial<OrderListResponse> = {}): OrderListResponse {
  return { items, page: 1, page_size: 20, total: items.length, ...extra };
}

function renderQueue(props: Partial<Parameters<typeof OrdersQueue>[0]> = {}) {
  const onOpen = vi.fn();
  const onSelectLens = vi.fn();
  const onClear = vi.fn();
  const onPage = vi.fn();
  render(
    <OrdersQueue
      filters={filters}
      data={list([item()])}
      loading={false}
      error={null}
      emptyHint={null}
      lenses={lenses}
      onChange={() => undefined}
      onSubmit={(event) => event.preventDefault()}
      onRefresh={() => undefined}
      onClearFilters={onClear}
      onOpen={onOpen}
      onPage={onPage}
      onSelectLens={onSelectLens}
      {...props}
    />,
  );
  return { onOpen, onSelectLens, onClear, onPage };
}

describe("fila de pedidos", () => {
  beforeEach(() => {
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(1200);
  });

  it("mostra as lentes com contagem e deixa Vigentes pressionada", () => {
    renderQueue();
    const vigentes = screen.getByRole("button", { name: /Vigentes/ });
    expect(vigentes).toHaveAttribute("aria-pressed", "true");
    expect(vigentes).toHaveTextContent("3");
    expect(screen.getByRole("button", { name: /Precisa de ação/ })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("group", { name: "Lentes da fila" })).toBeInTheDocument();
  });

  it("marca a lente vinda do ciclo e guarda as outras na situação", async () => {
    const user = userEvent.setup();
    const { onSelectLens } = renderQueue({ filters: { ...filters, lens: "stage:open" } });
    expect(screen.getByRole("button", { name: /Abertos/ })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Vigentes/ })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("option", { name: /Pronto — aguardando confirmação de entrega/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /^Abertos/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Precisa de ação/ }));
    expect(onSelectLens).toHaveBeenCalledWith("work:needs_action");
  });

  it("mostra Limpar só com filtro ativo", () => {
    const { onClear } = renderQueue({
      filters: { ...filters, reference: "LP" },
      data: list([]),
      emptyHint: "filtered",
    });
    expect(screen.getByRole("button", { name: "Limpar" })).toBeInTheDocument();
    expect(screen.getByText("Nenhum pedido com esses filtros.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Limpar filtros" })).toBeInTheDocument();
    onClear.mockClear();
  });

  it("usa tabela larga e o selo que a API mandou", () => {
    renderQueue();
    expect(screen.getByRole("table", { name: "Fila de pedidos" })).toBeInTheDocument();
    expect(screen.getByText("Aberto")).toBeInTheDocument();
    expect(screen.getByText("Após aceite")).toBeInTheDocument();
    expect(
      trackAccessibleName("Pagamento", {
        state: "no_charge",
        label: "Após aceite",
        tone: "none",
        hint: "A cobrança abre depois do aceite",
      }),
    ).toBe("Pagamento: Após aceite. A cobrança abre depois do aceite");
    expect(screen.getByText("Pagamento: Após aceite. A cobrança abre depois do aceite")).toBeInTheDocument();
  });

  it("usa cartões quando o conteúdo é estreito", () => {
    vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(700);
    renderQueue();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(document.querySelector("[data-queue='card']")).toBeTruthy();
    expect(document.querySelector(".queue-cards")?.className).toContain("is-two");
  });

  it("o próximo passo só navega", async () => {
    const user = userEvent.setup();
    const { onOpen } = renderQueue();
    await user.click(screen.getByRole("button", { name: "Avaliar e aceitar — abrir LPDEMO1" }));
    expect(onOpen).toHaveBeenCalledTimes(1);
    expect(onOpen.mock.calls[0][0].public_reference).toBe("LPDEMO1");
  });

  it("separa os três vazios e o erro parcial", () => {
    const { rerender } = render(
      <OrdersQueue
        filters={filters}
        data={list([])}
        loading={false}
        error={null}
        emptyHint="none"
        lenses={lenses}
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={() => undefined}
        onOpen={() => undefined}
        onPage={() => undefined}
      />,
    );
    expect(screen.getByText("Nenhum pedido na fila agora.")).toBeInTheDocument();
    rerender(
      <OrdersQueue
        filters={{ ...filters, lens: "work:needs_action" }}
        data={list([])}
        loading={false}
        error={null}
        emptyHint="needs_action"
        lenses={lenses}
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={() => undefined}
        onOpen={() => undefined}
        onPage={() => undefined}
      />,
    );
    expect(screen.getByText("Nada precisa de você agora.")).toBeInTheDocument();
    rerender(
      <OrdersQueue
        filters={filters}
        data={list([item()], { orders_error: "Não foi possível carregar as encomendas." })}
        loading={false}
        error={null}
        emptyHint={null}
        lenses={lenses}
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={() => undefined}
        onOpen={() => undefined}
        onPage={() => undefined}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível carregar as encomendas.");
    expect(screen.getByRole("link", { name: "LPDEMO1" })).toBeInTheDocument();
  });

  it("mostra o esqueleto enquanto carrega e pagina sem perder o botão", async () => {
    const user = userEvent.setup();
    const onPage = vi.fn();
    const { rerender } = render(
      <OrdersQueue
        filters={filters}
        data={null}
        loading
        error={null}
        emptyHint={null}
        lenses={lenses}
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={() => undefined}
        onOpen={() => undefined}
        onPage={onPage}
      />,
    );
    expect(document.querySelectorAll(".queue-skel")).toHaveLength(6);
    expect(document.querySelector("[data-queue='refresh']")).toBeDisabled();
    rerender(
      <OrdersQueue
        filters={filters}
        data={list([item()], { page: 1, total: 40 })}
        loading={false}
        error={null}
        emptyHint={null}
        lenses={lenses}
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={() => undefined}
        onOpen={() => undefined}
        onPage={onPage}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Seguinte" }));
    expect(onPage).toHaveBeenCalledWith(2);
    expect(screen.getByText("Mostrando 1 de 40")).toBeInTheDocument();
  });
});
