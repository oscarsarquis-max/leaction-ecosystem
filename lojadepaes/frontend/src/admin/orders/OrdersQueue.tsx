import { useLayoutEffect, useState, type FormEvent } from "react";
import { Button } from "../shell/Button";
import { PageHeader } from "../shell/PageHeader";
import type { AttendanceSummary, OrderFilters, OrderListItem, OrderListResponse, QueueLens } from "../types";
import { QueueCards } from "./QueueCards";
import { QueueFilters, PILL_KEYS } from "./QueueFilters";
import { QueueLenses } from "./QueueLenses";
import { QueueTable } from "./QueueTable";
import "./queue.css";

type Props = {
  filters: OrderFilters;
  data: OrderListResponse | null;
  loading: boolean;
  error: string | null;
  emptyHint: "none" | "filtered" | "needs_action" | null;
  lenses?: QueueLens[];
  summary?: AttendanceSummary | null;
  secondary?: QueueLens[];
  onChange: (filters: OrderFilters) => void;
  onSubmit: (event: FormEvent) => void;
  onRefresh: () => void;
  onClearFilters?: () => void;
  onOpen: (item: OrderListItem) => void;
  onPage: (page: number) => void;
  onSelectLens?: (key: string) => void;
};

const FALLBACK_LENSES: QueueLens[] = [
  { key: "vigentes", label: "Vigentes", count: 0 },
  { key: "work:needs_action", label: "Precisa de ação", count: 0 },
  { key: "stage:open", label: "Abertos", count: 0 },
  { key: "stage:accepted", label: "Aceitos sem pagamento", count: 0 },
  { key: "stage:paid", label: "Pagos", count: 0 },
  { key: "stage:in_production", label: "Em produção", count: 0 },
  { key: "stage:delivered", label: "Entregues", count: 0 },
  { key: "stage:cancelled", label: "Cancelados", count: 0 },
  { key: "all", label: "Todos", count: 0 },
];

const FALLBACK_SECONDARY: QueueLens[] = [
  { key: "stage:ready_legacy", label: "Pronto — aguardando confirmação de entrega", count: 0 },
  { key: "stage:finalized", label: "Finalizado", count: 0 },
  { key: "stage:rejected", label: "Rejeitadas", count: 0 },
  { key: "date_pending", label: "Solicitações de data", count: 0 },
  { key: "payment:awaiting", label: "Aguardando pagamento", count: 0 },
  { key: "payment:processing", label: "Em processamento", count: 0 },
  { key: "payment:paid", label: "Pagos", count: 0 },
  { key: "payment:failed", label: "Falha de pagamento", count: 0 },
  { key: "payment:no_charge", label: "Sem cobrança iniciada", count: 0 },
  { key: "payment:no_amount", label: "Sem valor a pagar", count: 0 },
  { key: "payment:refunded", label: "Estornados", count: 0 },
  { key: "payment:partial_refund", label: "Estorno parcial", count: 0 },
  { key: "payment:unknown", label: "Estado financeiro desconhecido", count: 0 },
  { key: "payment:charge_cancelled", label: "Cobrança cancelada no registro", count: 0 },
  { key: "payment:cancelled_open", label: "Pedido cancelado, sem pagamento regular", count: 0 },
  { key: "pending:address", label: "Endereço de entrega incompleto", count: 0 },
  { key: "pending:notice_pending", label: "Aviso ao cliente ainda na fila de envio", count: 0 },
  { key: "pending:notice_failed", label: "Falha efetiva no aviso ao cliente", count: 0 },
  { key: "pending:notice_skipped", label: "Aviso ao cliente registrado, envio não disparado", count: 0 },
  { key: "pending:overdue", label: "Data da fornada ou data desejada já passou", count: 0 },
  { key: "pending:adaptation", label: "Adaptação ainda sem desfecho", count: 0 },
  { key: "work:payment:awaiting", label: "Aguardando no fluxo", count: 0 },
  { key: "work:payment:processing", label: "Em processamento no fluxo", count: 0 },
  { key: "work:payment:paid", label: "Quitados no fluxo", count: 0 },
  { key: "work:payment:failed", label: "Falha no fluxo", count: 0 },
  { key: "audit:tests", label: "Testes fora da operação", count: 0 },
];

function useBoxWidth(node: HTMLElement | null): number {
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    if (!node) {
      return;
    }
    const read = () => setWidth(node.clientWidth);
    read();
    if (typeof ResizeObserver === "undefined") {
      return;
    }
    const observer = new ResizeObserver(read);
    observer.observe(node);
    return () => observer.disconnect();
  }, [node]);
  return width;
}

function usePhone(): boolean {
  const [phone, setPhone] = useState(false);
  useLayoutEffect(() => {
    if (typeof window.matchMedia !== "function") {
      return;
    }
    const query = window.matchMedia("(max-width: 959px)");
    const apply = () => setPhone(query.matches);
    apply();
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, []);
  return phone;
}

function pressedLens(filters: OrderFilters): string {
  const extra = Boolean(
    filters.reference.trim() || filters.status || filters.modality || filters.created_from || filters.created_to,
  );
  if (extra) {
    return "";
  }
  if (!filters.lens || filters.lens === "vigentes") {
    return "vigentes";
  }
  if (PILL_KEYS.has(filters.lens)) {
    return filters.lens;
  }
  return "";
}

export function secondaryLenses(summary: AttendanceSummary | null | undefined): QueueLens[] {
  const base = FALLBACK_SECONDARY.map((item) => ({ ...item }));
  const byKey = new Map(base.map((item) => [item.key, item]));
  const board = summary?.board;
  if (summary) {
    const pending = byKey.get("date_pending");
    if (pending) pending.count = summary.date_requests_awaiting;
  }
  if (!board) {
    return base;
  }
  const metrics = [
    ...(board.exceptions ?? []),
    ...board.history,
    ...board.stages,
    ...board.payments,
    ...board.payment_other,
    ...(board.work_payments ?? []),
    ...board.pendings,
  ];
  for (const metric of metrics) {
    if (PILL_KEYS.has(metric.lens)) continue;
    const existing = byKey.get(metric.lens);
    if (existing) {
      existing.count = metric.count;
    } else {
      const added = { key: metric.lens, label: metric.label, count: metric.count };
      byKey.set(metric.lens, added);
      base.push(added);
    }
  }
  const tests = byKey.get("audit:tests");
  if (tests && board.excluded_tests != null) tests.count = board.excluded_tests;
  return base;
}

export function OrdersQueue({
  filters,
  data,
  loading,
  error,
  emptyHint,
  lenses,
  summary,
  secondary,
  onChange,
  onSubmit,
  onRefresh,
  onClearFilters,
  onOpen,
  onPage,
  onSelectLens,
}: Props) {
  const [root, setRoot] = useState<HTMLElement | null>(null);
  const width = useBoxWidth(root);
  const phone = usePhone();
  const table = width >= 1120;
  const partial = [data?.orders_error, data?.date_requests_error].filter(Boolean) as string[];
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const items = data?.items ?? [];

  function selectLens(key: string) {
    onSelectLens?.(key);
  }

  function changePage(page: number) {
    onPage(page);
    const heading = root?.querySelector("h1");
    if (heading && typeof heading.scrollIntoView === "function") {
      heading.scrollIntoView({ block: "start" });
    }
  }

  return (
    <section className="admin-queue" ref={setRoot} data-queue="page">
      <PageHeader
        title="Pedidos"
        description="Encomendas e solicitações de data numa fila só. Cada linha mostra as quatro trilhas do pedido e o próximo passo."
        actions={
          <Button type="button" onClick={onRefresh} disabled={loading} data-queue="refresh">
            <svg className="queue-refresh-icon" viewBox="0 0 16 16" aria-hidden="true">
              <path
                d="M13.5 8a5.5 5.5 0 1 1-1.4-3.6"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.6"
                strokeLinecap="round"
              />
              <path d="M13.6 2.2v3.2H10.4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {loading ? "Atualizando…" : "Atualizar"}
          </Button>
        }
      />
      <QueueLenses lenses={lenses?.length ? lenses : FALLBACK_LENSES} pressed={pressedLens(filters)} onSelect={selectLens} />
      <QueueFilters
        filters={filters}
        secondary={secondary?.length ? secondary : secondaryLenses(summary)}
        loading={loading}
        phone={phone}
        onChange={onChange}
        onSubmit={onSubmit}
        onClear={onClearFilters}
      />
      {filters.created_from || filters.created_to ? (
        <p className="queue-note">Recorte pela data em que o registro foi criado, não pela data da fornada.</p>
      ) : null}
      {data?.filter_label ? (
        <p className="queue-note" role="status">
          Filtro do resumo: {data.filter_label}. {data.total} registro(s).
          {filters.reference.trim()
            ? " A busca por nome vale dentro deste filtro; limpe o filtro para procurar no histórico."
            : ""}
          {data.state_counts
            ? ` Vigentes ${data.state_counts.queue} · Todos ${data.state_counts.all} · Concluídos ${data.state_counts.completed} · Cancelados ${data.state_counts.cancelled}.`
            : ""}
          {onClearFilters ? (
            <>
              {" "}
              <button type="button" className="queue-link" onClick={onClearFilters}>
                Limpar filtro
              </button>
            </>
          ) : null}
        </p>
      ) : data?.search_scope ? (
        <p className="queue-note" role="status">
          {data.search_scope === "histórico completo"
            ? "Busca no histórico completo — não só a fila vigente."
            : data.search_scope === "todos os estados"
              ? "Todos os estados acessíveis, inclusive finalizados e cancelados."
              : "Fila operacional: só vigentes."}
        </p>
      ) : null}
      {error ? (
        <p className="queue-alert" role="alert">
          {error}{" "}
          <button type="button" className="queue-link" onClick={onRefresh} disabled={loading}>
            Tentar de novo
          </button>
        </p>
      ) : null}
      {partial.length > 0 ? (
        <p className="queue-alert" role="alert">
          Carga parcial: {partial.join(" ")}{" "}
          <button type="button" className="queue-link" onClick={onRefresh} disabled={loading}>
            Tentar de novo
          </button>
        </p>
      ) : null}
      {loading && items.length === 0 ? (
        <div className="queue-skel-list" aria-hidden="true">
          {Array.from({ length: 6 }, (_, index) => (
            <div key={index} className="queue-skel" />
          ))}
        </div>
      ) : null}
      {emptyHint === "none" ? <p className="queue-empty">Nenhum pedido na fila agora.</p> : null}
      {emptyHint === "needs_action" ? <p className="queue-empty">Nada precisa de você agora.</p> : null}
      {emptyHint === "filtered" ? (
        <p className="queue-empty">
          Nenhum pedido com esses filtros.
          {onClearFilters ? (
            <>
              {" "}
              <button type="button" className="queue-link" onClick={onClearFilters}>
                Limpar filtros
              </button>
            </>
          ) : null}
        </p>
      ) : null}
      {items.length > 0 && !loading ? (
        table ? (
          <QueueTable items={items} onOpen={onOpen} />
        ) : (
          <QueueCards items={items} two={width >= 640} onOpen={onOpen} />
        )
      ) : null}
      {items.length > 0 ? (
        <div className="queue-foot">
          <p aria-live="polite">
            Mostrando {items.length} de {data?.total ?? items.length}
          </p>
          <div>
            <Button type="button" disabled={loading || (data?.page ?? 1) <= 1} onClick={() => changePage((data?.page ?? 1) - 1)}>
              Anterior
            </Button>{" "}
            <Button
              type="button"
              disabled={loading || (data?.page ?? 1) >= totalPages}
              onClick={() => changePage((data?.page ?? 1) + 1)}
            >
              Seguinte
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
