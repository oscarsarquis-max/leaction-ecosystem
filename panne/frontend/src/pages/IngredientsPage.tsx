import { useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import type { IngredientCard, IngredientPage } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import { useAsyncResource } from "../hooks/useAsyncResource";
import {
  ingredientIdentityLabel,
  ingredientStatusTone,
  ingredientVersionLabel,
} from "../language/ingredients";
import { useOrganization } from "../session/OrganizationContext";

export function IngredientsPage() {
  const { api, hasPermission, active } = useOrganization();
  const orgId = active?.organization_id ?? null;
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const query = useMemo(
    () => ({
      q: params.get("q") || undefined,
      status: params.get("status") || undefined,
      version_status: params.get("version_status") || undefined,
      limit: params.get("limit") || "20",
      offset: params.get("offset") || "0",
    }),
    [params],
  );

  const { state } = useAsyncResource<IngredientPage>(
    () => api.listIngredients(query),
    [api, query, orgId],
    Boolean(orgId),
  );

  const offset = Number(query.offset ?? 0);
  const limit = Number(query.limit ?? 20);
  const total = state.kind === "ok" ? state.data.total : 0;
  const items = state.kind === "ok" ? state.data.items : [];

  function applyFilters(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setParams({
      q: String(data.get("q") ?? ""),
      status: String(data.get("status") ?? ""),
      version_status: String(data.get("version_status") ?? ""),
      offset: "0",
    });
  }

  return (
    <div className="stage">
      <ListLive
        kind={state.kind}
        empty={state.kind === "ok" && items.length === 0}
        entityLabel={items[0]?.display_name ?? "ingrediente"}
        status={state.kind === "ok" ? `${total} itens` : undefined}
      />
      <div>
        <h1>Ingredientes</h1>
        <p className="lede">
          Ação interna:{" "}
          {hasPermission("ingredient.create") ? (
            <Link className="primary" to="/componentes/ingredientes/novo">
              Novo ingrediente
            </Link>
          ) : (
            "criação oculta neste papel"
          )}
        </p>
        <form className="filters" onSubmit={applyFilters}>
          <label>
            Pesquisa
            <input name="q" defaultValue={query.q ?? ""} />
          </label>
          <label>
            Situação
            <select name="status" defaultValue={query.status ?? ""}>
              <option value="">Todas</option>
              <option value="active">Ativa</option>
              <option value="inactive">Inativa</option>
            </select>
          </label>
          <label>
            Versão
            <select name="version_status" defaultValue={query.version_status ?? ""}>
              <option value="">Todas</option>
              <option value="draft">Rascunho</option>
              <option value="published">Publicada</option>
              <option value="retired">Aposentada</option>
            </select>
          </label>
          <button type="submit" className="primary">
            Filtrar
          </button>
        </form>
        {state.kind === "carregando" ? <LoadingState /> : null}
        {state.kind === "erro" ? <ErrorState error={state.error} /> : null}
        {state.kind === "ok" && items.length === 0 ? (
          <EmptyState>Não há ingredientes neste recorte.</EmptyState>
        ) : null}
        {items.length > 0 ? (
          <div className="table-wrap">
            <table>
              <caption>Ingredientes da organização</caption>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Código</th>
                  <th>Versão</th>
                  <th>Situação</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <IngredientRow
                    key={item.id}
                    item={item}
                    onRowNavigate={(to) => navigate(to)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
        {state.kind === "ok" && total > limit ? (
          <p>
            <button
              type="button"
              disabled={offset <= 0}
              onClick={() =>
                setParams({ ...Object.fromEntries(params), offset: String(Math.max(0, offset - limit)) })
              }
            >
              Anterior
            </button>{" "}
            <button
              type="button"
              disabled={offset + limit >= total}
              onClick={() =>
                setParams({ ...Object.fromEntries(params), offset: String(offset + limit) })
              }
            >
              Seguinte
            </button>
          </p>
        ) : null}
      </div>
      <aside className="panel">
        <h2>Qualidade</h2>
        <p>
          <StatusBadge tone="sucesso" label="Publicada" />
        </p>
        <p>
          <StatusBadge tone="atencao" label="Rascunho / nutrição incompleta" />
        </p>
        <p>
          <StatusBadge tone="neutro" label="Aposentada" />
        </p>
        <p className="meta">Completude não é conformidade regulatória.</p>
      </aside>
    </div>
  );
}

function IngredientRow({
  item,
  onRowNavigate,
}: {
  item: IngredientCard;
  onRowNavigate: (to: string) => void;
}) {
  const detailTo = `/componentes/ingredientes/${item.id}`;
  const nameLabel = `Abrir detalhe de ${item.display_name}`;
  const codeLabel = `Abrir detalhe do código ${item.code}`;
  const detailActionLabel = `Detalhe de ${item.display_name}`;
  const version = item.current_version;

  return (
    <tr
      onClick={(event) => {
        const target = event.target as HTMLElement;
        if (target.closest("a")) return;
        onRowNavigate(detailTo);
      }}
    >
      <td>
        <Link to={detailTo} aria-label={nameLabel}>
          {item.display_name}
        </Link>
      </td>
      <td>
        <Link to={detailTo} aria-label={codeLabel}>
          {item.code}
        </Link>
      </td>
      <td>
        {version ? (
          <StatusBadge
            tone={ingredientStatusTone(version.status)}
            label={`${ingredientVersionLabel(version.status)} v${version.version_number}`}
          />
        ) : (
          "—"
        )}
      </td>
      <td>{ingredientIdentityLabel(item.status)}</td>
      <td>
        <Link to={detailTo} aria-label={detailActionLabel}>
          Detalhe
        </Link>
      </td>
    </tr>
  );
}
