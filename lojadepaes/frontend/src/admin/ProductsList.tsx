import { formatCents } from "../lib/money";
import type { FormEvent } from "react";
import type { AdminProductList } from "./productTypes";

const STATUS: Record<string, string> = {
  draft: "Rascunho",
  published: "Publicado",
  archived: "Arquivado",
};

type Filters = { query: string; status: string; available: string };

type ListProps = {
  filters: Filters;
  data: AdminProductList | null;
  loading: boolean;
  error: string | null;
  onChange: (filters: Filters) => void;
  onSubmit: (event: FormEvent) => void;
  onNew: () => void;
  onOpen: (id: string) => void;
  onPage: (page: number) => void;
};

export function ProductsList({
  filters,
  data,
  loading,
  error,
  onChange,
  onSubmit,
  onNew,
  onOpen,
  onPage,
}: ListProps) {
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <section className="admin-page">
      <header className="admin-page-head">
        <div>
          <p className="admin-eyebrow">Catálogo</p>
          <h1>Produtos</h1>
        </div>
        <button type="button" className="admin-primary" onClick={onNew}>
          Novo produto
        </button>
      </header>
      <form className="admin-filters" onSubmit={onSubmit}>
        <label>
          Busca
          <input
            value={filters.query}
            onChange={(event) => onChange({ ...filters, query: event.target.value })}
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
            <option value="published">Publicado</option>
            <option value="archived">Arquivado</option>
          </select>
        </label>
        <label>
          Disponibilidade
          <select
            value={filters.available}
            onChange={(event) => onChange({ ...filters, available: event.target.value })}
          >
            <option value="">Todas</option>
            <option value="true">Disponível</option>
            <option value="false">Indisponível</option>
          </select>
        </label>
        <button type="submit" className="admin-secondary">
          Filtrar
        </button>
      </form>
      {error ? <p className="admin-error">{error}</p> : null}
      {loading ? <p className="admin-muted">Carregando…</p> : null}
      {!loading && data && data.items.length === 0 ? (
        <p className="admin-empty">Nenhum produto com esses filtros.</p>
      ) : null}
      {data && data.items.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Foto</th>
                <th>Nome</th>
                <th>Estado</th>
                <th>Disponibilidade</th>
                <th>Preço</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((item) => (
                <tr key={item.id}>
                  <td data-label="Foto">
                    {item.thumbnail_url ? (
                      <img className="admin-thumb" src={item.thumbnail_url} alt="" />
                    ) : (
                      "—"
                    )}
                  </td>
                  <td data-label="Nome">
                    <button type="button" className="admin-link" onClick={() => onOpen(item.id)}>
                      {item.name}
                    </button>
                  </td>
                  <td data-label="Estado">{STATUS[item.editorial_status] ?? item.editorial_status}</td>
                  <td data-label="Disponibilidade">
                    {item.is_available ? "Disponível" : "Temporariamente indisponível"}
                  </td>
                  <td data-label="Preço">
                    {item.from_price.cents ? formatCents(item.from_price.cents) : "Sem preço à venda"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {data && data.total > data.page_size ? (
        <div className="admin-pager">
          <button
            type="button"
            className="admin-secondary"
            disabled={data.page <= 1}
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
            disabled={data.page >= totalPages}
            onClick={() => onPage(data.page + 1)}
          >
            Próxima
          </button>
        </div>
      ) : null}
    </section>
  );
}
