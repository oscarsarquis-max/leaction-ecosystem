import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/errors";
import type { RecipeCard } from "../api/types";
import { EmptyState, ErrorState, ListLive, LoadingState, StatusBadge } from "../components/Feedback";
import {
  recipeIdentityLabel,
  recipeStatusTone,
  recipeVersionLabel,
} from "../language/recipes";
import { useOrganization } from "../session/OrganizationContext";

export function RecipesPage() {
  const { api, hasPermission, active } = useOrganization();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [state, setState] = useState<
    | { kind: "carregando" }
    | { kind: "ok"; items: RecipeCard[]; total: number }
    | { kind: "erro"; error: unknown }
  >({ kind: "carregando" });
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

  const orgId = active?.organization_id ?? null;
  useEffect(() => {
    if (!orgId) return;
    let alive = true;
    setState({ kind: "carregando" });
    api
      .listRecipes(query)
      .then((page) => {
        if (alive) setState({ kind: "ok", items: page.items, total: page.total });
      })
      .catch((error) => {
        if (alive) setState({ kind: "erro", error });
      });
    return () => {
      alive = false;
    };
  }, [api, query, orgId]);

  const offset = Number(query.offset ?? 0);
  const limit = Number(query.limit ?? 20);
  const total = state.kind === "ok" ? state.total : 0;

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
        empty={state.kind === "ok" && state.items.length === 0}
        entityLabel={state.kind === "ok" && state.items[0] ? state.items[0].display_name : "receita"}
        status={state.kind === "ok" ? `${state.total} itens` : undefined}
      />
      <div>
        <div className="page-head">
          <div>
            <h1>Minhas receitas</h1>
          </div>
        </div>
        <p className="lede">
          {hasPermission("recipe.create") ? (
            <Link className="primary" to="/receitas/novo">
              Nova receita
            </Link>
          ) : (
            "criação oculta neste papel"
          )}{" "}
          {hasPermission("recipe.ai.propose") ? (
            <Link to="/receitas/assistente">Assistente de receitas</Link>
          ) : null}
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
              <option value="development">Em desenvolvimento</option>
              <option value="active">Ativa</option>
              <option value="retired">Aposentada</option>
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
        {state.kind === "erro" ? (
          <ErrorState
            error={state.error instanceof ApiError ? state.error : new Error("Falha ao listar")}
          />
        ) : null}
        {state.kind === "ok" && state.items.length === 0 ? (
          <EmptyState>Nenhuma receita nesta organização.</EmptyState>
        ) : null}
        {state.kind === "ok" && state.items.length > 0 ? (
          <table>
            <caption className="visually-hidden">Receitas da organização</caption>
            <thead>
              <tr>
                <th>Código</th>
                <th>Nome</th>
                <th>Situação</th>
                <th>Versão</th>
              </tr>
            </thead>
            <tbody>
              {state.items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <Link to={`/receitas/${item.id}`}>{item.code}</Link>
                  </td>
                  <td>{item.display_name}</td>
                  <td>
                    <StatusBadge tone={recipeStatusTone(item.status)} label={recipeIdentityLabel(item.status)} />
                  </td>
                  <td>
                    {item.current_version ? (
                      <StatusBadge
                        tone={recipeStatusTone(item.current_version.status)}
                        label={recipeVersionLabel(item.current_version.status)}
                      />
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {total > limit ? (
          <p>
            <button
              type="button"
              disabled={offset <= 0}
              onClick={() => setParams({ ...Object.fromEntries(params), offset: String(Math.max(0, offset - limit)) })}
            >
              Anterior
            </button>{" "}
            <button
              type="button"
              disabled={offset + limit >= total}
              onClick={() => setParams({ ...Object.fromEntries(params), offset: String(offset + limit) })}
            >
              Próxima
            </button>
          </p>
        ) : null}
      </div>
      <aside className="panel">
        <h2>Receitas</h2>
        <p>A ficha técnica nasce da versão. Não há cadastro paralelo.</p>
        <button type="button" className="ghost" onClick={() => navigate("/inicio")}>
          Voltar ao início
        </button>
      </aside>
    </div>
  );
}
