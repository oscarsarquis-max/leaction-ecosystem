import { formatCents } from "../lib/money";
import { useState, type FormEvent } from "react";
import { AdminApiError, adminRequest } from "./api";
import { ShowcasePanel } from "./ShowcasePanel";
import type { AdminProductList, AdminProductListItem } from "./productTypes";

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
  onRefresh: () => void;
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
  onRefresh,
}: ListProps) {
  const totalPages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [showcaseKey, setShowcaseKey] = useState(0);

  async function removeProduct(item: AdminProductListItem) {
    const kind = item.editorial_status === "archived" ? "cadastro arquivado" : "rascunho";
    if (!window.confirm(`Apagar o ${kind} “${item.name}”? Isso não pode ser desfeito.`)) {
      return;
    }
    setDeletingId(item.id);
    setDeleteError(null);
    try {
      await adminRequest(`/api/v1/admin/products/${item.id}`, { method: "DELETE" });
      setShowcaseKey((current) => current + 1);
      onRefresh();
    } catch (reason) {
      setDeleteError(reason instanceof AdminApiError ? reason.message : "Não foi possível apagar o cadastro.");
    } finally {
      setDeletingId(null);
    }
  }

  function vitrineLabel(item: AdminProductListItem): string {
    if (item.editorial_status !== "published") {
      return "—";
    }
    if (item.showcase_position) {
      return `Posição ${item.showcase_position}`;
    }
    return "Fora da vitrine";
  }

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
      {deleteError ? <p className="admin-error">{deleteError}</p> : null}
      <ShowcasePanel key={showcaseKey} />
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
                <th>Vitrine</th>
                <th>Disponibilidade</th>
                <th>Preço</th>
                <th>Ações</th>
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
                  <td data-label="Vitrine">{vitrineLabel(item)}</td>
                  <td data-label="Disponibilidade">
                    {item.is_available ? "Disponível" : "Temporariamente indisponível"}
                  </td>
                  <td data-label="Preço">
                    {item.from_price.cents ? formatCents(item.from_price.cents) : "Sem preço à venda"}
                  </td>
                  <td data-label="Ações">
                    {item.editorial_status === "draft" || item.editorial_status === "archived" ? (
                      <button
                        type="button"
                        className="admin-danger"
                        disabled={deletingId === item.id}
                        onClick={() => void removeProduct(item)}
                      >
                        {deletingId === item.id ? "Apagando…" : "Apagar"}
                      </button>
                    ) : (
                      "—"
                    )}
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
