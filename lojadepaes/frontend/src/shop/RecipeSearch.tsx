import { FormEvent, useEffect, useState } from "react";
import { ApiError } from "../services/http";
import { readRecipeSearch, rememberRecipeSearch } from "./recipeSearchMemory";
import { fetchRecipeSearch } from "./weekRecipeApi";
import type { RecipeSearchPage } from "./weekRecipe";

type Props = {
  compact?: boolean;
  initialQ?: string;
  initialPage?: number;
};

function startState(compact: boolean, initialQ: string, initialPage: number) {
  if (!compact) {
    return { q: initialQ, page: initialPage, active: true };
  }
  const stored = readRecipeSearch();
  if (stored?.from === "home" && stored.q.trim()) {
    return { q: stored.q, page: stored.page, active: true };
  }
  return { q: initialQ, page: 1, active: Boolean(initialQ) };
}

export function RecipeSearch({ compact = false, initialQ = "", initialPage = 1 }: Props) {
  const from = compact ? "home" : "archive";
  const pageSize = compact ? 5 : 12;
  const start = startState(compact, initialQ, initialPage);
  const [q, setQ] = useState(start.q);
  const [page, setPage] = useState(start.page);
  const [active, setActive] = useState(start.active);
  const [result, setResult] = useState<RecipeSearchPage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function load(nextQ: string, nextPage: number) {
    setLoading(true);
    setError(null);
    rememberRecipeSearch({ q: nextQ.trim(), page: nextPage, from });
    fetchRecipeSearch(nextQ, nextPage, pageSize)
      .then((data) => {
        setResult(data);
        setPage(data.page);
      })
      .catch((reason: unknown) => {
        setResult(null);
        if (reason instanceof ApiError && reason.message === "rede-indisponivel") {
          setError("Não foi possível buscar receitas agora.");
          return;
        }
        setError("Não foi possível buscar receitas agora.");
      })
      .finally(() => {
        setLoading(false);
      });
  }

  useEffect(() => {
    if (!active) {
      return;
    }
    load(q, page);
    // First paint only; later loads go through submit/pagination.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    setActive(true);
    setPage(1);
    load(q, 1);
  }

  const pages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1;

  return (
    <section className={compact ? "week-recipe-search" : "recipe-archive-search"} aria-labelledby="recipe-search-title">
      <h4 id="recipe-search-title" className="recipe-search-heading">
        Mais ideias para sua mesa
      </h4>
      <form className="recipe-search-form" onSubmit={onSubmit}>
        <label className="recipe-search-label" htmlFor={compact ? "home-recipe-q" : "archive-recipe-q"}>
          Buscar receitas
        </label>
        <div className="recipe-search-row">
          <input
            id={compact ? "home-recipe-q" : "archive-recipe-q"}
            type="search"
            value={q}
            onChange={(event) => setQ(event.target.value)}
            placeholder="Receita ou ingrediente…"
            maxLength={120}
            autoComplete="off"
          />
          <button className="primary" type="submit" disabled={loading}>
            Buscar
          </button>
        </div>
      </form>
      {loading ? <p className="recipe-search-status">Buscando receitas…</p> : null}
      {error ? (
        <p className="recipe-search-status" role="alert">
          {error}{" "}
          <button type="button" className="text-button" onClick={() => load(q, page)}>
            Tentar novamente
          </button>
        </p>
      ) : null}
      {result && !loading && !error && result.total === 0 ? (
        <p className="recipe-search-status">Nenhuma receita encontrada.</p>
      ) : null}
      {result && result.items.length > 0 ? (
        <ul className="recipe-search-results">
          {result.items.map((item) => (
            <li key={item.slug}>
              <a
                href={item.href}
                onClick={() => rememberRecipeSearch({ q: result.q, page: result.page, from })}
              >
                {item.title}
              </a>
              {item.summary ? <p>{item.summary}</p> : null}
            </li>
          ))}
        </ul>
      ) : null}
      {result && pages > 1 ? (
        <div className="recipe-search-pager">
          <button
            type="button"
            className="text-button"
            disabled={loading || page <= 1}
            onClick={() => {
              const next = page - 1;
              setPage(next);
              load(q, next);
            }}
          >
            Página anterior
          </button>
          <span>
            Página {result.page} de {pages}
          </span>
          <button
            type="button"
            className="text-button"
            disabled={loading || page >= pages}
            onClick={() => {
              const next = page + 1;
              setPage(next);
              load(q, next);
            }}
          >
            Próxima página
          </button>
        </div>
      ) : null}
      {compact ? (
        <a className="recipe-search-archive" href="/receitas">
          Ver o acervo de receitas
        </a>
      ) : null}
    </section>
  );
}
