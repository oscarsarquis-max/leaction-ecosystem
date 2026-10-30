import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AttendanceHistoryPanel, AttendanceSummaryPanel } from "./AttendanceSummary";
import { OrdersQueue } from "./orders/OrdersQueue";
import type { AttendanceBoard, AttendanceSummary, OrderListResponse } from "./types";

function metric(label: string, count: number, lens: string) {
  return { label, count, lens };
}

function board(total = 4): AttendanceBoard {
  return {
    scope: "Situação atual de todos os registros, sem filtro de data de criação.",
    timezone: "America/Sao_Paulo",
    updated_label: "21/10/2026 11:40",
    operational_total: total,
    stages: [
      metric("Aberto", 2, "stage:open"),
      metric("Aceito", 1, "stage:accepted"),
      metric("Pago", 1, "stage:paid"),
      metric("Em produção", 1, "stage:in_production"),
    ],
    history: [
      metric("Entregue", 0, "stage:delivered"),
      metric("Finalizado", 3, "stage:finalized"),
      metric("Cancelado", 1, "stage:cancelled"),
      metric("Rejeitado", 0, "stage:rejected"),
    ],
    exceptions: [],
    composition_note:
      "O total vigente soma Aberto, Aceito, Pago e Em produção com a exceção Pronto — aguardando confirmação de entrega.",
    legacy_note: "Pronto e Finalizado permanecem com o significado original. Não foram convertidos em Entregue.",
    payment_note: "Não soma com o fluxo vigente.",
    payments: [
      metric("Aguardando pagamento", 1, "payment:awaiting"),
      metric("Em processamento", 0, "payment:processing"),
      metric("Pagos", 2, "payment:paid"),
      metric("Falha de pagamento", 0, "payment:failed"),
    ],
    payment_other: [metric("Sem valor a pagar", 1, "payment:no_amount")],
    payment_orders: 5,
    pending_note: "Um mesmo pedido pode ter mais de uma pendência.",
    pendings: [
      metric("Endereço de entrega incompleto", 1, "pending:address"),
      metric("Aviso na fila de envio", 0, "pending:notice_pending"),
      metric("Falha no aviso ao cliente", 0, "pending:notice_failed"),
      metric("Aviso não disparado", 0, "pending:notice_skipped"),
      metric("Data ultrapassada", 0, "pending:overdue"),
      metric("Adaptação em aberto", 0, "pending:adaptation"),
    ],
    not_tracked: [],
  };
}

function summary(total = 4): AttendanceSummary {
  return {
    date_requests_awaiting: 1,
    orders_awaiting_evaluation: 1,
    orders_awaiting_adaptation: 0,
    paid_awaiting_accept: 0,
    confirmed_awaiting_delivery: 2,
    overdue_dates: 0,
    unique_records: total,
    counts_are_subsets: true,
    priority: [],
    updated_at: "2026-10-21T14:40:00+00:00",
    board: board(total),
  };
}

describe("resumo gerencial", () => {
  it("filtra a fila pelo clique e não anuncia ausência de pendência", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <AttendanceSummaryPanel
        data={summary()}
        loading={false}
        error={null}
        activeLens=""
        onRefresh={() => undefined}
        onSelectLens={onSelect}
      />,
    );
    expect(screen.getByText("vigentes agora")).toBeInTheDocument();
    expect(screen.getByText("21/10/2026 11:40", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("horário de Brasília", { exact: false })).toBeInTheDocument();
    expect(screen.queryByText(/Nenhuma pendência prioritária/)).not.toBeInTheDocument();
    expect(screen.queryByText(/tipo \+ ID/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Não foram convertidos em Entregue/)).not.toBeInTheDocument();
    expect(screen.queryByText(/WhatsApp/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Testes fora da operação/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /aguardando confirmação de entrega/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Aceito/ })).toHaveClass("is-accepted");
    expect(screen.getByRole("button", { name: /Em produção/ })).toHaveClass("is-in-production");
    expect(screen.getByRole("button", { name: /Entregue/ })).toHaveClass("is-delivered");
    expect(screen.getByRole("button", { name: /Entregue/ })).toHaveTextContent("No histórico");
    expect(screen.queryByRole("button", { name: /Rejeitado/ })).not.toBeInTheDocument();
    const pago = screen.getByRole("button", {
      name: (name) => name.includes("Pago") && !name.includes("Pagos"),
    });
    expect(pago).toHaveClass("is-paid");
    expect(screen.queryByRole("button", { name: /Pagos/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Pendências/ })).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByRole("button", { name: /Pagamentos dos ativos/ })).toHaveAttribute("aria-expanded", "false");
    await user.click(screen.getByRole("button", { name: /Aberto/ }));
    expect(onSelect).toHaveBeenCalledWith("stage:open");
    await user.click(screen.getByRole("button", { name: /Pendências/ }));
    await user.click(screen.getByRole("button", { name: /Endereço de entrega incompleto/ }));
    expect(onSelect).toHaveBeenCalledWith("pending:address");
  });

  it("mostra a exceção operacional quando há pedido pronto sem entrega", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const data = summary(5);
    const shown = data.board;
    if (!shown) {
      throw new Error("fixture sem quadro");
    }
    shown.exceptions = [
      metric("Pronto — aguardando confirmação de entrega", 1, "stage:ready_legacy"),
    ];
    shown.operational_total = 5;
    render(
      <AttendanceSummaryPanel
        data={data}
        loading={false}
        error={null}
        activeLens=""
        onRefresh={() => undefined}
        onSelectLens={onSelect}
      />,
    );
    await user.click(screen.getByRole("button", { name: /aguardando confirmação de entrega/ }));
    expect(onSelect).toHaveBeenCalledWith("stage:ready_legacy");
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("mantém a leitura anterior quando a atualização falha", () => {
    const { rerender } = render(
      <AttendanceSummaryPanel
        data={summary(7)}
        loading={false}
        error={null}
        activeLens=""
        onRefresh={() => undefined}
        onSelectLens={() => undefined}
      />,
    );
    expect(screen.getByText("7")).toBeInTheDocument();
    rerender(
      <AttendanceSummaryPanel
        data={summary(7)}
        loading={false}
        error="falha de rede"
        activeLens=""
        onRefresh={() => undefined}
        onSelectLens={() => undefined}
      />,
    );
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("desatualizados");
    expect(screen.getByRole("alert")).toHaveTextContent("falha de rede");
    expect(screen.queryByText(/Nenhuma pendência prioritária/)).not.toBeInTheDocument();
  });

  it("não mostra zero quando a primeira leitura falha ou ainda carrega", () => {
    const { rerender } = render(
      <AttendanceSummaryPanel
        data={null}
        loading={true}
        error={null}
        activeLens=""
        onRefresh={() => undefined}
        onSelectLens={() => undefined}
      />,
    );
    expect(screen.getByText("Carregando resumo…")).toBeInTheDocument();
    expect(screen.queryByText("vigentes agora")).not.toBeInTheDocument();
    rerender(
      <AttendanceSummaryPanel
        data={null}
        loading={false}
        error="falha de rede"
        activeLens=""
        onRefresh={() => undefined}
        onSelectLens={() => undefined}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Não foi possível carregar o resumo");
    expect(screen.queryByText("vigentes agora")).not.toBeInTheDocument();
    expect(screen.queryByText("Aguardando avaliação")).not.toBeInTheDocument();
  });

  it("mostra o filtro do resumo e a limpeza sem esconder o histórico", async () => {
    const user = userEvent.setup();
    const onClear = vi.fn();
    const data: OrderListResponse = {
      items: [],
      page: 2,
      page_size: 1,
      total: 3,
      filter_label: "Confirmados",
      search_scope: "Confirmados",
      state_counts: { queue: 4, all: 9, completed: 3, cancelled: 1 },
    };
    render(
      <OrdersQueue
        filters={{ reference: "", status: "", created_from: "", created_to: "", modality: "", lens: "stage:confirmed" }}
        data={data}
        loading={false}
        error={null}
        emptyHint="filtered"
        onChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        onRefresh={() => undefined}
        onClearFilters={onClear}
        onOpen={() => undefined}
        onPage={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: /Aceitos sem pagamento/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Pagos/ })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "Aceito ou pago" })).not.toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: /Pronto — aguardando confirmação de entrega/ }),
    ).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Filtro do resumo: Confirmados");
    expect(screen.getByRole("status")).toHaveTextContent("3 registro(s)");
    expect(screen.getByRole("status")).toHaveTextContent("Concluídos 3");
    expect(screen.getByRole("status")).toHaveTextContent("Cancelados 1");
    await user.click(screen.getByRole("button", { name: "Limpar filtro" }));
    expect(onClear).toHaveBeenCalled();
  });

  it("mantém zeros, pagamento dos vigentes e testes fora da operação", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const data = summary(0);
    const shown = data.board;
    if (!shown) {
      throw new Error("fixture sem quadro");
    }
    shown.operational_total = 0;
    shown.stages = shown.stages.map((item) => ({ ...item, count: 0 }));
    shown.history = shown.history.map((item) => ({ ...item, count: 0 }));
    shown.pendings = shown.pendings.map((item) => ({ ...item, count: 0 }));
    shown.payments = shown.payments.map((item) => ({ ...item, count: 0 }));
    shown.payment_other = [
      metric("Sem cobrança iniciada", 0, "payment:no_charge"),
      metric("Sem valor a pagar", 0, "payment:no_amount"),
    ];
    shown.work_payments = [
      metric("Aguardando no fluxo", 0, "work:payment:awaiting"),
      metric("Em processamento no fluxo", 0, "work:payment:processing"),
      metric("Quitados no fluxo", 0, "work:payment:paid"),
      metric("Falha no fluxo", 0, "work:payment:failed"),
    ];
    shown.work_payment_orders = 0;
    shown.excluded_tests = 0;
    shown.payment_orders = 0;
    render(
      <AttendanceSummaryPanel
        data={data}
        loading={false}
        error={null}
        activeLens=""
        onRefresh={() => undefined}
        onSelectLens={onSelect}
      />,
    );
    expect(screen.queryByRole("button", { name: /Testes fora da operação/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Sem cobrança iniciada/ })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Entregue/ })).toHaveTextContent("0");
    expect(screen.getByRole("button", { name: /Aberto/ })).toHaveTextContent("0");
    expect(screen.queryByRole("button", { name: /aguardando confirmação de entrega/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Pagamentos dos ativos/ }));
    await user.click(screen.getByRole("button", { name: /Quitados no fluxo/ }));
    expect(onSelect).toHaveBeenCalledWith("work:payment:paid");
    expect(screen.getByRole("button", { name: /Quitados no fluxo/ })).not.toHaveClass("is-paid");
    expect(screen.getByText(/Soma deste recorte: 0/)).toBeInTheDocument();
  });

  it("abre o histórico sob demanda e conserva zeros, critérios e filtros", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const onToggle = vi.fn();
    const data = summary(0);
    const shown = data.board;
    if (!shown) {
      throw new Error("fixture sem quadro");
    }
    shown.history = shown.history.map((item) => ({ ...item, count: 0 }));
    shown.payments = shown.payments.map((item) => ({ ...item, count: 0 }));
    shown.payment_other = [metric("Sem cobrança iniciada", 0, "payment:no_charge")];
    shown.payment_orders = 0;
    const { rerender } = render(
      <AttendanceHistoryPanel
        data={data}
        error={null}
        open={false}
        activeLens=""
        onToggle={onToggle}
        onSelectLens={onSelect}
      />,
    );
    expect(screen.queryByRole("button", { name: /Sem cobrança iniciada/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Rejeitado/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/Não foram convertidos em Entregue/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Consultar histórico/ }));
    expect(onToggle).toHaveBeenCalled();
    rerender(
      <AttendanceHistoryPanel
        data={data}
        error={null}
        open
        activeLens=""
        onToggle={onToggle}
        onSelectLens={onSelect}
      />,
    );
    expect(screen.getByRole("button", { name: /Sem cobrança iniciada/ })).toHaveTextContent("0");
    expect(screen.getByRole("button", { name: /Aguardando pagamento/ })).toHaveTextContent("0");
    expect(screen.getByRole("button", { name: /Rejeitado/ })).toHaveClass("is-rejected");
    expect(screen.getByRole("button", { name: /Pagos/ })).not.toHaveClass("is-paid");
    await user.click(screen.getByText("Critérios deste resumo"));
    expect(screen.getByText(/exceção Pronto — aguardando confirmação de entrega/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^Entregue/ }));
    expect(onSelect).toHaveBeenCalledWith("stage:delivered");
  });

  it("o nó Entregue filtra e pede o histórico, sem somar ao total vigente", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const onOpenHistory = vi.fn();
    render(
      <AttendanceSummaryPanel
        data={summary()}
        loading={false}
        error={null}
        activeLens="stage:delivered"
        onRefresh={() => undefined}
        onSelectLens={onSelect}
        onOpenHistory={onOpenHistory}
      />,
    );
    const node = screen.getByRole("button", { name: /Entregue/ });
    expect(node).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Limpar filtro" })).toBeInTheDocument();
    node.focus();
    await user.keyboard("{Enter}");
    expect(onSelect).toHaveBeenCalledWith("stage:delivered");
    expect(onOpenHistory).toHaveBeenCalled();
  });
});
