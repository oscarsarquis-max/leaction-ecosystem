'use client';

import { useState } from 'react';
import { Search } from 'lucide-react';
import { fetchMarketplaceOffers, SEARCH_CATEGORIES } from './marketplaceApi';
import { OffersGrid } from './OffersGrid';

/**
 * Motor de busca unificado — categorias de dor do cliente + termo livre.
 */
export function MultivendorSearchBox({ className = '' }) {
  const [category, setCategory] = useState('');
  const [query, setQuery] = useState('');
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  async function handleSearch(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    setNotice('');
    setHasSearched(true);

    try {
      const data = await fetchMarketplaceOffers({
        q: query,
        category,
        limit: 12,
      });
      setOffers(data.offers);
      setNotice(data.notice);
    } catch (err) {
      setOffers([]);
      setError(
        err instanceof Error ? err.message : 'Não foi possível buscar soluções no momento.'
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={className}>
      <div className="rounded-2xl border border-slate-200/80 bg-white p-6 shadow-xl shadow-slate-200/50 md:p-8">
        <div className="mb-6 text-center md:mb-8">
          <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-orange-500">
            Buscador de Soluções
          </p>
          <h2 className="text-2xl font-extrabold tracking-tight text-red-950 md:text-3xl">
            Encontre recursos para sua transformação digital
          </h2>
          <p className="mx-auto mt-2 max-w-2xl text-sm text-slate-600 md:text-base">
            Filtre por categoria de necessidade e refine com palavras-chave. Resultados curados de
            múltiplas fontes, organizados para decisores e gestores.
          </p>
        </div>

        <form
          onSubmit={handleSearch}
          className="flex flex-col gap-3 md:flex-row md:items-stretch md:gap-4"
        >
          <div className="md:w-72">
            <label htmlFor="marketplace-category" className="sr-only">
              Categoria
            </label>
            <select
              id="marketplace-category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="h-full w-full rounded-xl border border-slate-300 bg-white px-4 py-3.5 text-sm font-medium text-slate-800 shadow-sm outline-none transition focus:border-orange-400 focus:ring-2 focus:ring-orange-400/20"
            >
              {SEARCH_CATEGORIES.map((opt) => (
                <option key={opt.value || 'all'} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex-1">
            <label htmlFor="marketplace-query" className="sr-only">
              Termo de busca
            </label>
            <input
              id="marketplace-query"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ex.: liderança digital, switch gerenciável, LMS corporativo…"
              className="h-full w-full rounded-xl border border-slate-300 bg-white px-4 py-3.5 text-sm text-slate-800 shadow-sm outline-none transition placeholder:text-slate-400 focus:border-orange-400 focus:ring-2 focus:ring-orange-400/20"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-orange-500 px-8 py-3.5 text-sm font-bold text-white shadow-lg shadow-orange-500/20 transition hover:bg-orange-400 disabled:cursor-not-allowed disabled:opacity-70 md:min-w-[180px]"
          >
            <Search className="size-4" aria-hidden />
            {loading ? 'Buscando…' : 'Buscar Soluções'}
          </button>
        </form>
      </div>

      {hasSearched ? (
        <div className="mt-8 md:mt-10">
          {notice ? (
            <p className="mb-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
              {notice}
            </p>
          ) : null}

          {!loading && !error && offers.length > 0 ? (
            <p className="mb-4 text-sm font-medium text-slate-600">
              {offers.length} {offers.length === 1 ? 'resultado' : 'resultados'} encontrados
            </p>
          ) : null}

          <OffersGrid
            offers={offers}
            loading={loading}
            error={error}
            emptyMessage="Nenhuma solução encontrada. Tente outra categoria ou termo de busca."
          />
        </div>
      ) : null}
    </div>
  );
}
