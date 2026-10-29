import type { FormEvent } from "react";
import { financialKindLabel, formatDateTime, formatDay, formatMoney, modalityLabel, pendingAgeLabel, statusLabel } from "./format";
import type { OrderFilters, OrderListItem, OrderListResponse } from "./types";

type ListProps = {
  filters: OrderFilters;
  data: OrderListResponse | null;
  loading: boolean;
  error: string | null;
  emptyHint: "none" | "filtered" | null;
  onChange: (filters: OrderFilters) => void;
  onSubmit: (event: FormEvent) => void;
  onRefresh: () => void;
  onClearFilters?: () => void;
  onOpen: (item: OrderListItem) => void;
  onPage: (page: number) => void;
};

function rowStatus(item: OrderListItem): string {
  if (item.visible_label) {
    return item.visible_label;
  }
  if (item.source === "date_request") {
    return statusLabel(item.status);
  }
  if (item.status === "submitted") {
    return "Encomenda: Aguardando avaliação de A Loja";
  }
  return statusLabel(item.status, item.fulfillment_modality);
}

function stageClass(stage?: string | null): string {
  return stage ? `admin-stage is-${stage.replaceAll("_", "-")}` : "admin-stage";
}

function rowTotal(item: OrderListItem): string {
  if (item.source === "date_request" || item.financial_kind === "none" && item.total.cents == null) {
    return item.source === "date_request" ? "Sem cobrança" : formatMoney(item.total);
  }
  return formatMoney(item.total);
}

function rowFinancial(item: OrderListItem): string {
  return item.source === "date_request" ? "Sem cobrança" : financialKindLabel(item.financial_kind);
}

export function OrdersList({
  filters,
  data,
  loading,
  error,
  emptyHint,
  onChange,
  onSubmit,
  onRefresh,
  onClearFilters,
  onOpen,
  onPage,
}: ListProps) {
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const partial = [data?.orders_error, data?.date_requests_error].filter(Boolean) as string[];

  return (
    <section className="admin-page">
      <header className="admin-page-head">
        <div>
          <p className="admin-eyebrow">Operação</p>
          <h1>Pedidos</h1>
        </div>
        <button type="button" className="admin-secondary" onClick={onRefresh} disabled={loading}>
          Atualizar
        </button>
      </header>

      <p className="admin-lead">
        Fila única de encomendas e solicitações de data. Responda aqui; a Agenda continua só para
        configurar a produção.
      </p>

      <form className="admin-filters" onSubmit={onSubmit}>
        <label>
          Buscar
          <input
            value={filters.reference}
            onChange={(event) => onChange({ ...filters, reference: event.target.value })}
            maxLength={80}
            placeholder="Nome ou referência"
          />
        </label>
        <label>
          Estado
          <select
            value={filters.lens?.startsWith("stage:") ? filters.lens : filters.status}
            onChange={(event) => {
              const value = event.target.value;
              if (value.startsWith("stage:")) {
                onChange({ ...filters, status: "", lens: value });
              } else {
                onChange({ ...filters, status: value, lens: "" });
              }
            }}
          >
            <option value="">Fila operacional</option>
            <option value="all">Todos</option>
            <option value="date_pending">Solicitações de data</option>
            <option value="stage:open">Aberto</option>
            <option value="stage:accepted">Aceito</option>
            <option value="stage:paid">Pago</option>
            <option value="stage:in_production">Em produção</option>
            <option value="stage:ready_legacy">Pronto — aguardando confirmação de entrega</option>
            <option value="stage:delivered">Entregue</option>
            <option value="stage:finalized">Finalizado</option>
            <option value="stage:cancelled">Cancelados</option>
            <option value="stage:rejected">Rejeitadas</option>
          </select>
        </label>
        <label>
          Modalidade
          <select
            value={filters.modality}
            onChange={(event) => onChange({ ...filters, modality: event.target.value })}
          >
            <option value="">Todas</option>
            <option value="pickup">Retirada (histórico)</option>
            <option value="delivery">Entrega</option>
          </select>
        </label>
        <label>
          Criado de
          <input
            type="date"
            value={filters.created_from}
            onChange={(event) => onChange({ ...filters, created_from: event.target.value })}
          />
        </label>
        <label>
          até
          <input
            type="date"
            value={filters.created_to}
            onChange={(event) => onChange({ ...filters, created_to: event.target.value })}
          />
        </label>
        <button className="admin-primary" type="submit" disabled={loading}>
          Filtrar
        </button>
      </form>

      {filters.created_from || filters.created_to ? (
        <p className="admin-muted">Recorte pela data em que o registro foi criado, não pela data da fornada.</p>
      ) : null}
      {data?.filter_label ? (
        <p className="admin-muted" role="status">
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
              <button type="button" className="admin-link" onClick={onClearFilters}>
                Limpar filtro
              </button>
            </>
          ) : null}
        </p>
      ) : data?.search_scope ? (
        <p className="admin-muted" role="status">
          {data.search_scope === "histórico completo"
            ? "Busca no histórico completo — não só a fila vigente."
            : data.search_scope === "todos os estados"
              ? "Todos os estados acessíveis, inclusive finalizados e cancelados."
              : "Fila operacional: só vigentes."}
          {data.state_counts
            ? ` Vigentes ${data.state_counts.queue} · Todos ${data.state_counts.all} · Concluídos ${data.state_counts.completed} · Cancelados ${data.state_counts.cancelled}.`
            : ""}
        </p>
      ) : null}
      {loading ? <p className="admin-muted">Carregando pedidos…</p> : null}
      {error ? (
        <p className="admin-error" role="alert">
          {error}{" "}
          <button type="button" className="admin-link" onClick={onRefresh} disabled={loading}>
            Tentar de novo
          </button>
        </p>
      ) : null}
      {partial.length > 0 ? (
        <p className="admin-error" role="alert">
          Carga parcial: {partial.join(" ")}{" "}
          <button type="button" className="admin-link" onClick={onRefresh} disabled={loading}>
            Tentar de novo
          </button>
        </p>
      ) : null}
      {emptyHint === "none" ? <p className="admin-empty">Nenhum pedido nesta fila de atendimento.</p> : null}
      {emptyHint === "filtered" ? (
        <p className="admin-empty">
          Nenhum pedido com esses filtros.
          {onClearFilters ? (
            <>
              {" "}
              <button type="button" className="admin-link" onClick={onClearFilters}>
                Limpar filtros
              </button>
            </>
          ) : null}
        </p>
      ) : null}

      {data && data.items.length > 0 ? (
        <>
          <div className="admin-table-wrap">
            <table className="admin-table admin-orders-table">
              <thead>
                <tr>
                  <th>Referência</th>
                  <th>Criado</th>
                  <th>Cliente</th>
                  <th>Contexto</th>
                  <th>Estado</th>
                  <th>Recebimento</th>
                  <th>Total</th>
                  <th>Financeiro</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.row_key || `${item.source || "order"}:${item.id}`} className={item.overdue ? "is-overdue" : undefined}>
                    <td data-label="Referência">
                      <button type="button" className="admin-link" onClick={() => onOpen(item)}>
                        {item.public_reference}
                      </button>
                      {item.source === "date_request" ? (
                        <span className="admin-tag admin-tag-request">Solicitação de data</span>
                      ) : null}
                    </td>
                    <td data-label="Criado">
                      {formatDateTime(item.created_at)}
                      {pendingAgeLabel(item.pending_hours) ? (
                        <span className="admin-muted"> · {pendingAgeLabel(item.pending_hours)}</span>
                      ) : null}
                    </td>
                    <td data-label="Cliente">{item.customer_name ?? "Visitante sem nome"}</td>
                    <td data-label="Contexto">
                      {item.source === "date_request"
                        ? `${item.context_label ?? `${item.bread_units || "—"} pão(ães)`} · data ${formatDay(item.desired_date)}`
                        : `${item.bread_units} pães`}
                    </td>
                    <td data-label="Estado">
                      <span className={stageClass(item.visible_stage)}>{rowStatus(item)}</span>
                      {item.payment_attention ? (
                        <span className="admin-tag admin-tag-pay">{item.payment_attention}</span>
                      ) : null}
                      {item.overdue ? <span className="admin-tag admin-tag-attention">Data vencida — revisar</span> : null}
                      {item.custom_awaiting ? (
                        <span className="admin-tag admin-tag-attention">Nova solicitação de pão personalizado</span>
                      ) : null}
                      {item.adaptation_attention ? (
                        <span className="admin-tag admin-tag-attention">Adaptação: Aguardando avaliação</span>
                      ) : null}
                      {item.delivery_pending ? (
                        <span className="admin-tag admin-tag-attention">Dados de entrega pendentes</span>
                      ) : null}
                    </td>
                    <td data-label="Recebimento">
                      {item.source === "date_request"
                        ? "Sem encomenda"
                        : `${modalityLabel(item.fulfillment_modality)}${item.production_batch_code ? ` · ${item.production_batch_code}` : ""}`}
                    </td>
                    <td data-label="Total">{rowTotal(item)}</td>
                    <td data-label="Financeiro">{rowFinancial(item)}</td>
                    <td data-label="Ação">
                      {item.source === "date_request" &&
                      (item.status === "pending" ||
                        item.status === "alternative_proposed" ||
                        item.status === "awaiting_details") ? (
                        <button type="button" className="admin-primary" onClick={() => onOpen(item)}>
                          Avaliar e responder
                        </button>
                      ) : (
                        <button type="button" className="admin-secondary" onClick={() => onOpen(item)}>
                          Abrir
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="admin-pager">
            <button
              type="button"
              className="admin-secondary"
              disabled={loading || data.page <= 1}
              onClick={() => onPage(data.page - 1)}
            >
              Anterior
            </button>
            <span>
              Página {data.page} de {totalPages}
            </span>
            <button
              type="button"
              className="admin-secondary"
              disabled={loading || data.page >= totalPages}
              onClick={() => onPage(data.page + 1)}
            >
              Seguinte
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}
