'use client';

import { useEffect, useState, type MouseEvent } from 'react';
import { Loader2, Search, ShoppingBag } from 'lucide-react';
import { MarketplaceProductImage } from '@/components/Marketplace/MarketplaceProductImage';
import { fetchMarketplaceOffers } from '@/components/Marketplace/marketplaceApi';
import { useCart } from '@/context/CartContext';
import { useAuthGate } from '@/lib/require-hub-login';
import { openExternalUrl } from '@/utils/openExternalUrl';

type Offer = {
  id: string;
  title: string;
  price?: number | null;
  price_label?: string;
  image?: string | null;
  link: string;
  vendor?: string;
  category?: string;
  fallback?: boolean;
};

type VitrinePayload = {
  recommended?: Offer[];
  shelves?: Array<{ category?: string; category_label?: string; offers?: Offer[] }>;
  error?: string;
};

const PLACEHOLDER_OFFERS: Offer[] = [
  {
    id: 'mock-formacao-1',
    title: 'Trilha Executiva de Transformação Digital',
    price_label: 'R$ 297',
    price: 297,
    link: '#',
    category: 'Formação',
    image: '/marketplace/placeholders/livro.svg',
    fallback: true,
  },
  {
    id: 'mock-infra-1',
    title: 'Kit Infraestrutura Inteligente — Edge & Rede',
    price_label: 'R$ 1.890',
    price: 1890,
    link: '#',
    category: 'Equipamentos',
    image: '/marketplace/placeholders/rede.svg',
    fallback: true,
  },
  {
    id: 'mock-soft-1',
    title: 'Licença Annual — Gestão & Compliance Core',
    price_label: 'R$ 89/mês',
    price: 89,
    link: '#',
    category: 'Software',
    image: '/marketplace/placeholders/digital.svg',
    fallback: true,
  },
  {
    id: 'mock-soft-2',
    title: 'Suite de Analytics Contextual B2B',
    price_label: 'R$ 149/mês',
    price: 149,
    link: '#',
    category: 'Software',
    image: '/marketplace/placeholders/gestao.svg',
    fallback: true,
  },
];

const SEARCH_DEBOUNCE_MS = 400;

function flattenOffers(payload: VitrinePayload | null): Offer[] {
  if (!payload) return [];
  const fromRecommended = Array.isArray(payload.recommended) ? payload.recommended : [];
  const fromShelves = (payload.shelves || []).flatMap((shelf) =>
    (shelf.offers || []).map((o) => ({
      ...o,
      category: o.category || shelf.category_label || shelf.category || 'Marketplace',
    }))
  );
  const map = new Map<string, Offer>();
  [...fromRecommended, ...fromShelves].forEach((o) => {
    if (o?.id) map.set(String(o.id), o);
  });
  return Array.from(map.values());
}

function normalizeSearchOffer(raw: Record<string, unknown>): Offer | null {
  const id = String(raw.id || '').trim();
  const title = String(raw.title || '').trim();
  const link = String(raw.link || '').trim();
  if (!id || !title || !link) return null;
  return {
    id,
    title,
    price: typeof raw.price === 'number' ? raw.price : null,
    price_label: typeof raw.price_label === 'string' ? raw.price_label : undefined,
    image: typeof raw.image === 'string' ? raw.image : null,
    link,
    vendor: typeof raw.vendor === 'string' ? raw.vendor : undefined,
    category: typeof raw.category === 'string' ? raw.category : undefined,
    fallback: Boolean(raw.fallback),
  };
}

export function OffersVitrine() {
  const { addToCart, cartItems } = useCart();
  const { requireLogin } = useAuthGate();
  const [vitrineOffers, setVitrineOffers] = useState<Offer[]>([]);
  const [searchOffers, setSearchOffers] = useState<Offer[] | null>(null);
  const [loadingVitrine, setLoadingVitrine] = useState(true);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedQuery(query.trim());
    }, SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function load() {
      setLoadingVitrine(true);
      try {
        const res = await fetch('/marketplace-api/vitrine?limit=8', {
          cache: 'no-store',
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        });
        const data = (await res.json().catch(() => ({}))) as VitrinePayload;
        const list = flattenOffers(data);
        if (!cancelled) {
          setVitrineOffers(list.length ? list : PLACEHOLDER_OFFERS);
        }
      } catch {
        if (!cancelled) setVitrineOffers(PLACEHOLDER_OFFERS);
      } finally {
        if (!cancelled) setLoadingVitrine(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  useEffect(() => {
    if (!debouncedQuery) {
      setSearchOffers(null);
      setSearchError('');
      setSearching(false);
      return;
    }

    let cancelled = false;
    const controller = new AbortController();

    async function runSearch() {
      setSearching(true);
      setSearchError('');
      try {
        const data = await fetchMarketplaceOffers({
          q: debouncedQuery,
          limit: 12,
          signal: controller.signal,
        });
        if (cancelled) return;
        const rawOffers = Array.isArray(data.offers) ? data.offers : [];
        const list = rawOffers
          .map((offer: unknown) => normalizeSearchOffer(offer as Record<string, unknown>))
          .filter((offer: Offer | null): offer is Offer => Boolean(offer));
        setSearchOffers(list);
      } catch (err) {
        if (cancelled || (err instanceof DOMException && err.name === 'AbortError')) return;
        setSearchOffers([]);
        setSearchError(
          err instanceof Error ? err.message : 'Não foi possível buscar soluções no momento.'
        );
      } finally {
        if (!cancelled) setSearching(false);
      }
    }

    void runSearch();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [debouncedQuery]);

  const isSearchMode = Boolean(debouncedQuery);
  const displayedOffers = isSearchMode ? searchOffers || [] : vitrineOffers;
  const loading = isSearchMode ? searching : loadingVitrine;

  function acquire(offer: Offer, event: MouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    if (
      !requireLogin(
        '/dashboard?view=cart',
        'Faça login para adicionar ao carrinho (Marketplace).'
      )
    ) {
      return;
    }
    addToCart({
      id: offer.id,
      sku: offer.id,
      nome: offer.title,
      price: offer.price,
      price_label: offer.price_label,
      image: offer.image,
      link: offer.link,
      vendor: offer.vendor,
    });
    if (offer.link && offer.link !== '#') {
      openExternalUrl(offer.link);
    }
  }

  return (
    <section id="vitrine" className="flex h-full min-h-0 flex-col">
      <header className="mb-5 shrink-0">
        <h1 className="text-2xl font-bold tracking-tight text-stone-900 md:text-3xl">
          Descubra Soluções
        </h1>
        <p className="mt-1 text-sm text-stone-500">
          Marketplace B2B curado — formação, infraestrutura e software.
        </p>
        <label className="relative mt-4 block">
          <span className="sr-only">Buscar soluções</span>
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-stone-400"
            aria-hidden
          />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Buscar por oferta, categoria ou fornecedor…"
            className="w-full rounded-xl border border-stone-200 bg-white py-2.5 pl-10 pr-3 text-sm text-stone-800 shadow-sm outline-none transition placeholder:text-stone-400 focus:border-orange-300 focus:ring-2 focus:ring-orange-100"
          />
        </label>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-20 text-sm text-stone-500">
            <Loader2 className="size-4 animate-spin" aria-hidden />
            {isSearchMode ? 'Buscando soluções…' : 'Carregando vitrine…'}
          </div>
        ) : searchError ? (
          <div className="rounded-2xl border border-amber-200 bg-amber-50 px-6 py-10 text-center text-sm text-amber-900">
            {searchError}
          </div>
        ) : displayedOffers.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-stone-200 bg-white px-6 py-16 text-center text-sm text-stone-500">
            Nenhuma oferta encontrada para “{query.trim()}”.
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {displayedOffers.map((offer) => {
              const inCart = cartItems.some((i) => String(i.id) === String(offer.id));
              return (
                <li key={offer.id}>
                  <article className="flex h-full flex-col overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-sm transition hover:border-orange-200 hover:shadow-md">
                    <div className="relative h-40 w-full shrink-0 overflow-hidden rounded-t-xl bg-stone-100">
                      <MarketplaceProductImage
                        src={offer.image}
                        title={offer.title}
                      />
                    </div>
                    <div className="flex flex-1 flex-col gap-2 p-4">
                      <span className="inline-flex w-fit rounded-full bg-orange-50 px-2.5 py-0.5 text-[11px] font-semibold text-orange-700">
                        {offer.category || offer.vendor || 'Marketplace'}
                      </span>
                      <h2 className="line-clamp-2 text-sm font-semibold leading-snug text-stone-900">
                        {offer.title}
                      </h2>
                      <p className="text-lg font-bold text-orange-950">
                        {offer.price_label || 'Consulte'}
                      </p>
                      <button
                        type="button"
                        disabled={inCart}
                        onClick={(event) => acquire(offer, event)}
                        className="mt-auto inline-flex w-full items-center justify-center gap-2 rounded-xl bg-orange-500 px-3 py-2.5 text-xs font-semibold text-white transition hover:bg-orange-600 disabled:cursor-default disabled:opacity-70"
                      >
                        <ShoppingBag className="size-3.5" aria-hidden />
                        {inCart ? 'No carrinho' : 'Adquirir'}
                      </button>
                    </div>
                  </article>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
