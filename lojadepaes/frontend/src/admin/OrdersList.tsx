import type { FormEvent } from "react";
import { financialKindLabel, formatDateTime, formatMoney, modalityLabel, statusLabel } from "./format";
import type { OrderFilters, OrderListResponse } from "./types";

type ListProps = {
  filters: OrderFilters;
  data: OrderListResponse | null;
  loading: boolean;
  error: string | null;
  emptyHint: "none" | "filtered" | null;
  onChange: (filters: OrderFilters) => void;
  onSubmit: (event: FormEvent) => void;
  onRefresh: () => void;
  onOpen: (id: string) => void;
  onPage: (page: number) => void;
};

export function OrdersList({
  filters,
  data,
  loading,
  error,
  emptyHint,
  onChange,
  onSubmit,
  onRefresh,
  onOpen,
  onPage,
}: ListProps) {
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

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

      <form className="admin-filters" onSubmit={onSubmit}>
        <label>
          Referência
          <input
            value={filters.reference}
            onChange={(event) => onChange({ ...filters, reference: event.target.value })}
            maxLength={20}
          />
        </label>
        <label>
          Estado
          <select
            value={filters.status}
            onChange={(event) => onChange({ ...filters, status: event.target.value })}
          >
            <option value="">Todos</option>
            <option value="draft">Rascunho</option>
            <option value="confirmed">Confirmado</option>
            <option value="in_production">Em produção</option>
            <option value="ready">Pronto</option>
            <option value="completed">Concluído</option>
            <option value="cancelled">Cancelado</option>
          </select>
        </label>
        <label>
          Modalidade
          <select
            value={filters.modality}
            onChange={(event) => onChange({ ...filters, modality: event.target.value })}
          >
            <option value="">Todas</option>
            <option value="pickup">Retirada</option>
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

      {loading ? <p className="admin-muted">Carregando pedidos…</p> : null}
      {error ? <p className="admin-error" role="alert">{error}</p> : null}
      {emptyHint === "none" ? <p className="admin-empty">Nenhum pedido ainda.</p> : null}
      {emptyHint === "filtered" ? <p className="admin-empty">Nenhum pedido com esses filtros.</p> : null}

      {data && data.items.length > 0 ? (
        <>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Referência</th>
                  <th>Criado</th>
                  <th>Cliente</th>
                  <th>Pães</th>
                  <th>Estado</th>
                  <th>Recebimento</th>
                  <th>Total</th>
                  <th>Financeiro</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td data-label="Referência">
                      <button type="button" className="admin-link" onClick={() => onOpen(item.id)}>
                        {item.public_reference}
                      </button>
                    </td>
                    <td data-label="Criado">{formatDateTime(item.created_at)}</td>
                    <td data-label="Cliente">{item.customer_name ?? "Visitante sem nome"}</td>
                    <td data-label="Pães">{item.bread_units}</td>
                    <td data-label="Estado">{statusLabel(item.status)}</td>
                    <td data-label="Recebimento">
                      {modalityLabel(item.fulfillment_modality)}
                      {item.production_batch_code ? ` · ${item.production_batch_code}` : ""}
                    </td>
                    <td data-label="Total">{formatMoney(item.total)}</td>
                    <td data-label="Financeiro">{financialKindLabel(item.financial_kind)}</td>
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
