import { CatalogTabs } from "./CatalogTabs";
import type { WeekRecipeAdmin } from "../shop/weekRecipe";

const STATUS: Record<string, string> = {
  draft: "Rascunho",
  published: "Publicada",
  archived: "Arquivada",
};

type Props = {
  items: WeekRecipeAdmin[];
  loading: boolean;
  error: string | null;
  busyId: string | null;
  onNew: () => void;
  onOpen: (id: string) => void;
  onPublish: (id: string) => void;
  onFeature: (id: string) => void;
  onUnfeature: (id: string) => void;
  onArchive: (id: string) => void;
};

export function WeekRecipesList({
  items,
  loading,
  error,
  busyId,
  onNew,
  onOpen,
  onPublish,
  onFeature,
  onUnfeature,
  onArchive,
}: Props) {
  return (
    <section className="admin-page">
      <CatalogTabs current="recipes" />
      <header className="admin-page-head">
        <div>
          <p className="admin-eyebrow">Catálogo</p>
          <h1>Receitas da semana</h1>
          <p className="admin-lead">
            Conteúdo editorial de uso dos pães. Não é produto, não entra no carrinho e não pontua na
            fidelidade. Publicar não troca o destaque sozinho.
          </p>
        </div>
        <button type="button" className="admin-primary" onClick={onNew}>
          Nova receita
        </button>
      </header>
      {error ? <p className="admin-error">{error}</p> : null}
      {loading ? <p className="admin-muted">Carregando receitas…</p> : null}
      {!loading && items.length === 0 ? (
        <p className="admin-empty">Ainda não há receitas cadastradas. O destaque só aparece na vitrine depois de publicar e marcar como destaque da semana.</p>
      ) : null}
      {items.length > 0 ? (
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Título</th>
                <th>Estado</th>
                <th>Destaque</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td data-label="Título">{item.title || "Sem título"}</td>
                  <td data-label="Estado">{STATUS[item.editorial_status] ?? item.editorial_status}</td>
                  <td data-label="Destaque">{item.is_featured ? "Destaque da semana" : "—"}</td>
                  <td data-label="Ações">
                    <div className="admin-actions">
                      <button type="button" className="admin-link" onClick={() => onOpen(item.id)}>
                        Editar
                      </button>
                      {item.editorial_status !== "published" ? (
                        <button
                          type="button"
                          className="admin-secondary"
                          disabled={busyId === item.id}
                          onClick={() => onPublish(item.id)}
                        >
                          Publicar
                        </button>
                      ) : null}
                      {item.editorial_status === "published" && !item.is_featured ? (
                        <button
                          type="button"
                          className="admin-secondary"
                          disabled={busyId === item.id}
                          onClick={() => onFeature(item.id)}
                        >
                          Destacar
                        </button>
                      ) : null}
                      {item.is_featured ? (
                        <button
                          type="button"
                          className="admin-secondary"
                          disabled={busyId === item.id}
                          onClick={() => onUnfeature(item.id)}
                        >
                          Retirar destaque
                        </button>
                      ) : null}
                      {item.editorial_status !== "archived" ? (
                        <button
                          type="button"
                          className="admin-text"
                          disabled={busyId === item.id}
                          onClick={() => onArchive(item.id)}
                        >
                          Arquivar
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
