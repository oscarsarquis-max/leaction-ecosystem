'use client';

import { Loader2 } from 'lucide-react';
import { OfferCard } from './OfferCard';

export function OffersGrid({ offers, loading, error, emptyMessage, className = '' }) {
  if (loading) {
    return (
      <div
        className={`flex min-h-[140px] items-center justify-center gap-2 text-slate-500 ${className}`}
      >
        <Loader2 className="size-5 animate-spin" aria-hidden />
        <span className="text-sm font-medium">Buscando soluções…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 ${className}`}
        role="alert"
      >
        {error}
        <p className="mt-2 text-xs text-amber-800/80">
          Verifique se o plugin Marketplace está ativo:{' '}
          <code className="rounded bg-amber-100 px-1">cd backend &amp;&amp; python run.py</code>
        </p>
      </div>
    );
  }

  if (!offers.length) {
    return (
      <p
        className={`rounded-xl border border-dashed border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500 ${className}`}
      >
        {emptyMessage || 'Nenhuma solução encontrada para este contexto.'}
      </p>
    );
  }

  return (
    <ul className={`grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 ${className}`}>
      {offers.map((offer) => (
        <li key={offer.id || offer.link}>
          <OfferCard offer={offer} />
        </li>
      ))}
    </ul>
  );
}
