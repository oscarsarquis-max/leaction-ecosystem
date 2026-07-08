'use client';

import { useEffect, useMemo, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { fetchMarketplaceOffers } from './marketplaceApi';
import { OffersGrid } from './OffersGrid';

/**
 * Prateleira temática — busca automática por categoria + termo fixos.
 */
export function MultivendorGrid({
  title,
  subtitle,
  category = '',
  query = '',
  limit = 4,
  className = '',
}) {
  const [offers, setOffers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const fetchKey = useMemo(
    () => `${category}|${query}|${limit}`,
    [category, query, limit]
  );

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError('');
      setNotice('');
      try {
        const data = await fetchMarketplaceOffers({
          q: query,
          category,
          limit,
          signal: controller.signal,
        });
        if (!cancelled) {
          setOffers(data.offers);
          setNotice(data.notice);
        }
      } catch (err) {
        if (!cancelled && err?.name !== 'AbortError') {
          setOffers([]);
          setError(
            err instanceof Error
              ? err.message
              : 'Não foi possível carregar as soluções desta prateleira.'
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [fetchKey, category, query, limit]);

  return (
    <section
      className={`rounded-2xl border border-slate-200 bg-white p-6 shadow-sm md:p-8 ${className}`}
      aria-labelledby={`shelf-${title.replace(/\s+/g, '-').toLowerCase()}`}
    >
      <div className="mb-6 max-w-3xl">
        <p className="mb-2 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-orange-500">
          <Sparkles className="size-3.5" aria-hidden />
          Curadoria LeAction
        </p>
        <h3
          id={`shelf-${title.replace(/\s+/g, '-').toLowerCase()}`}
          className="text-2xl font-extrabold tracking-tight text-red-950 md:text-3xl"
        >
          {title}
        </h3>
        {subtitle ? (
          <p className="mt-2 text-sm leading-relaxed text-slate-600 md:text-base">{subtitle}</p>
        ) : null}
      </div>

      {notice ? (
        <p className="mb-4 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
          {notice}
        </p>
      ) : null}

      <OffersGrid
        offers={offers}
        loading={loading}
        error={error}
        emptyMessage="Nenhuma solução disponível nesta prateleira no momento."
      />
    </section>
  );
}
