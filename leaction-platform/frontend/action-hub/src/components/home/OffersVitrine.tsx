'use client';

import { useEffect, useMemo, useState, type MouseEvent } from 'react';
import { Loader2, Search, ShoppingBag } from 'lucide-react';
import { MarketplaceProductImage } from '@/components/Marketplace/MarketplaceProductImage';
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

export function OffersVitrine() {
  const { addToCart, cartItems } = useCart();
  const { requireLogin } = useAuthGate();
  const [offers, setOffers] = useState<Offer[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      try {
        const res = await fetch('/marketplace-api/vitrine?limit=8', {
          cache: 'no-store',
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        });
        const data = (await res.json().catch(() => ({}))) as VitrinePayload;
        const list = flattenOffers(data);
        if (!cancelled) {
          setOffers(list.length ? list : PLACEHOLDER_OFFERS);
        }
      } catch {
        if (!cancelled) setOffers(PLACEHOLDER_OFFERS);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return offers;
    return offers.filter(
      (o) =>
        o.title.toLowerCase().includes(q) ||
        (o.category || '').toLowerCase().includes(q) ||
        (o.vendor || '').toLowerCase().includes(q)
    );
  }, [offers, query]);

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
            Carregando vitrine…
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-stone-200 bg-white px-6 py-16 text-center text-sm text-stone-500">
            Nenhuma oferta encontrada para “{query}”.
          </div>
        ) : (
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {filtered.map((offer) => {
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
