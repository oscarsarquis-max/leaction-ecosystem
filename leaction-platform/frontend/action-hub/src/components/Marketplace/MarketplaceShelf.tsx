'use client';

import { useEffect, useMemo, useState, type MouseEvent } from 'react';
import { ExternalLink, Loader2, ShoppingCart } from 'lucide-react';
import { MarketplaceProductImage } from '@/components/Marketplace/MarketplaceProductImage';
import { openExternalUrl } from '@/utils/openExternalUrl';
import { useCart } from '@/context/CartContext';
import { buildOffersUrl } from './marketplaceApi';

export type MarketplaceOffer = {
  id: string;
  title: string;
  price?: number | null;
  price_label?: string;
  image?: string | null;
  link: string;
  vendor?: string;
  fallback?: boolean;
};

type MarketplaceShelfProps = {
  title: string;
  description: string;
  category: string;
  limit?: number;
  className?: string;
};

function openOfferLink(event: MouseEvent<HTMLButtonElement>, url: string) {
  event.preventDefault();
  event.stopPropagation();
  openExternalUrl(url);
}

export function MarketplaceShelf({
  title,
  description,
  category,
  limit = 4,
  className = '',
}: MarketplaceShelfProps) {
  const { addToCart, cartItems } = useCart();
  const [offers, setOffers] = useState<MarketplaceOffer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const offersUrl = useMemo(
    () => buildOffersUrl({ category, limit }),
    [category, limit]
  );

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function loadOffers() {
      setLoading(true);
      setError('');
      try {
        const response = await fetch(offersUrl, {
          cache: 'no-store',
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data.error || `Erro HTTP ${response.status}`);
        }
        const list = Array.isArray(data.offers) ? data.offers : [];
        if (!cancelled) setOffers(list);
      } catch (err) {
        if (!cancelled && err instanceof Error && err.name !== 'AbortError') {
          setOffers([]);
          setError(err.message || 'Não foi possível carregar esta prateleira.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadOffers();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [offersUrl]);

  const sectionId = `shelf-${category}`;

  return (
    <section
      className={`rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-6 ${className}`}
      aria-labelledby={sectionId}
    >
      <div className="mb-5 max-w-2xl">
        <h2 id={sectionId} className="text-xl font-bold tracking-tight text-slate-900 md:text-2xl">
          {title}
        </h2>
        <p className="mt-1 text-sm leading-relaxed text-slate-500">{description}</p>
      </div>

      {loading ? (
        <div className="flex min-h-[180px] items-center justify-center gap-2 text-slate-500">
          <Loader2 className="size-5 animate-spin" aria-hidden />
          <span className="text-sm font-medium">Carregando ofertas…</span>
        </div>
      ) : null}

      {!loading && error ? (
        <div
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
          role="alert"
        >
          {error}
        </div>
      ) : null}

      {!loading && !error && offers.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-10 text-center text-sm text-slate-500">
          Nenhuma oferta disponível nesta categoria no momento.
        </p>
      ) : null}

      {!loading && !error && offers.length > 0 ? (
        <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {offers.map((offer) => (
            <li key={`${category}-${offer.id}`}>
              <article className="flex h-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white transition hover:border-orange-200 hover:shadow-md">
                <div className="relative h-40 w-full shrink-0 overflow-hidden bg-slate-50">
                  <MarketplaceProductImage
                    src={offer.image}
                    title={offer.title}
                  />
                </div>
                <div className="flex flex-1 flex-col gap-3 p-4">
                  <h3 className="line-clamp-2 min-h-[2.5rem] text-sm font-semibold leading-snug text-slate-800">
                    {offer.title}
                  </h3>
                  <p className="text-lg font-bold text-red-700">
                    {offer.price_label || 'Consulte'}
                  </p>
                  <div className="mt-auto flex flex-col gap-2">
                    <button
                      type="button"
                      aria-label={
                        cartItems.some((i) => String(i.id) === String(offer.id))
                          ? `Já no carrinho: ${offer.title}`
                          : `Adicionar ao carrinho: ${offer.title}`
                      }
                      disabled={cartItems.some((i) => String(i.id) === String(offer.id))}
                      onClick={() =>
                        addToCart({
                          id: offer.id,
                          sku: offer.id,
                          nome: offer.title,
                          price: offer.price,
                          price_label: offer.price_label,
                          image: offer.image,
                          link: offer.link,
                          vendor: offer.vendor,
                        })
                      }
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-xs font-semibold text-orange-800 transition hover:bg-orange-100 disabled:cursor-default disabled:opacity-70"
                    >
                      <ShoppingCart className="size-3.5 shrink-0" aria-hidden />
                      {cartItems.some((i) => String(i.id) === String(offer.id))
                        ? 'No carrinho'
                        : 'Adicionar ao carrinho'}
                    </button>
                    <button
                      type="button"
                      aria-label={`Ver oferta: ${offer.title}`}
                      onClick={(event) => openOfferLink(event, offer.link)}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:border-orange-300 hover:bg-orange-50 hover:text-orange-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500"
                    >
                      Ver oferta
                      <ExternalLink className="size-3.5 shrink-0" aria-hidden />
                    </button>
                  </div>
                </div>
              </article>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
