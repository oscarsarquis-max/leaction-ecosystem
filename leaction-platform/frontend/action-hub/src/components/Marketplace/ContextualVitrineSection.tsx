'use client';

import { useEffect, useMemo, useState, type MouseEvent } from 'react';
import { ExternalLink, Loader2, ShoppingCart, Sparkles, Target } from 'lucide-react';
import { MarketplaceProductImage } from '@/components/Marketplace/MarketplaceProductImage';
import { MarketplaceShelf } from '@/components/Marketplace/MarketplaceShelf';
import { useCart } from '@/context/CartContext';
import { openExternalUrl } from '@/utils/openExternalUrl';

export type ContextualOffer = {
  id: string;
  title: string;
  price?: number | null;
  price_label?: string;
  image?: string | null;
  link: string;
  vendor?: string;
  fallback?: boolean;
  matched_category?: string;
};

type ShelfPayload = {
  category: string;
  category_label?: string;
  offers?: ContextualOffer[];
};

type VitrinePayload = {
  status?: string;
  mode?: 'generic' | 'contextual';
  title?: string;
  subtitle?: string;
  recommended?: ContextualOffer[];
  shelves?: ShelfPayload[];
  sprints?: Array<{ id_sprn?: number; nome?: string; status?: string }>;
  error?: string;
};

const SHELF_META: Record<string, { title: string; description: string }> = {
  formacao: {
    title: 'Biblioteca da Transformação',
    description: 'Conteúdo executivo e metodologias',
  },
  equipamentos: {
    title: 'Infraestrutura Inteligente',
    description: 'Equipamentos corporativos de rede e automação',
  },
  software: {
    title: 'Sistemas Core',
    description: 'Licenças e softwares de gestão e segurança',
  },
};

function openOfferLink(event: MouseEvent<HTMLButtonElement>, url: string) {
  event.preventDefault();
  event.stopPropagation();
  openExternalUrl(url);
}

function readContextFromUrl(): { id_matu?: string; id_clie?: string; id_projeto?: string } {
  if (typeof window === 'undefined') return {};
  const params = new URLSearchParams(window.location.search);
  const pick = (key: string) => {
    const v = (params.get(key) || '').trim();
    return v || undefined;
  };
  return {
    id_matu: pick('id_matu'),
    id_clie: pick('id_clie') || pick('client_id'),
    id_projeto: pick('id_projeto'),
  };
}

function OfferGrid({
  offers,
  keyPrefix,
}: {
  offers: ContextualOffer[];
  keyPrefix: string;
}) {
  const { addToCart, cartItems } = useCart();

  return (
    <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      {offers.map((offer) => {
        const inCart = cartItems.some((i) => String(i.id) === String(offer.id));
        return (
          <li key={`${keyPrefix}-${offer.id}`}>
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
                      inCart
                        ? `Já no carrinho: ${offer.title}`
                        : `Adicionar ao carrinho: ${offer.title}`
                    }
                    disabled={inCart}
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
                    {inCart ? 'No carrinho' : 'Adicionar ao carrinho'}
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
        );
      })}
    </ul>
  );
}

export function ContextualVitrineSection() {
  const [payload, setPayload] = useState<VitrinePayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const context = useMemo(() => readContextFromUrl(), []);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError('');
      try {
        const params = new URLSearchParams();
        params.set('limit', '4');
        if (context.id_matu) params.set('id_matu', context.id_matu);
        if (context.id_clie) params.set('id_clie', context.id_clie);
        if (context.id_projeto) params.set('id_projeto', context.id_projeto);

        const res = await fetch(`/marketplace-api/vitrine?${params.toString()}`, {
          cache: 'no-store',
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        });
        const data = (await res.json().catch(() => ({}))) as VitrinePayload;
        if (!res.ok) {
          throw new Error(data.error || `Erro HTTP ${res.status}`);
        }
        if (!cancelled) setPayload(data);
      } catch (err) {
        if (!cancelled && err instanceof Error && err.name !== 'AbortError') {
          setError(err.message || 'Não foi possível carregar a vitrine.');
          setPayload(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void load();
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [context.id_matu, context.id_clie, context.id_projeto]);

  const isContextual = payload?.mode === 'contextual';
  const recommended = payload?.recommended || [];
  const title = isContextual
    ? payload?.title || 'Soluções recomendadas para suas Sprints Ativas'
    : payload?.title || 'Explore nossas Soluções';
  const subtitle = isContextual
    ? payload?.subtitle ||
      'Itens alinhados às iniciativas priorizadas do seu projeto PanelDX.'
    : payload?.subtitle ||
      'Conteúdo organizado pela dor do cliente, com filtros de relevância corporativa.';

  return (
    <div className="mx-auto max-w-5xl space-y-10 md:space-y-12">
      <div className="mx-auto max-w-2xl text-center">
        <p className="mb-1.5 text-sm font-semibold uppercase tracking-wider text-orange-600">
          {isContextual ? 'Recomendação PanelDX' : 'Curadoria B2B'}
        </p>
        <h2
          id="vitrine-prateleiras-titulo"
          className="text-2xl font-bold tracking-tight text-slate-900 md:text-3xl"
        >
          {title}
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-500 md:text-base">{subtitle}</p>
      </div>

      {loading ? (
        <div className="flex min-h-[160px] items-center justify-center gap-2 text-slate-500">
          <Loader2 className="size-5 animate-spin" aria-hidden />
          <span className="text-sm font-medium">Montando vitrine…</span>
        </div>
      ) : null}

      {!loading && error ? (
        <div
          className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
          role="alert"
        >
          {error} — exibindo prateleiras padrão.
        </div>
      ) : null}

      {!loading && isContextual && recommended.length > 0 ? (
        <section
          className="rounded-2xl border border-orange-200/80 bg-white p-5 shadow-sm md:p-6"
          aria-labelledby="vitrine-recomendadas"
        >
          <div className="mb-5 flex flex-wrap items-start gap-3">
            <div className="rounded-xl bg-orange-50 p-2 text-orange-600">
              <Target className="size-4" aria-hidden />
            </div>
            <div className="min-w-0 flex-1">
              <h3
                id="vitrine-recomendadas"
                className="text-lg font-bold tracking-tight text-slate-900 md:text-xl"
              >
                Soluções recomendadas para suas Sprints Ativas
              </h3>
              <p className="mt-1 text-sm text-slate-500">
                Match por tags entre sprints priorizadas e o catálogo.
              </p>
              {payload?.sprints && payload.sprints.length > 0 ? (
                <p className="mt-2 text-xs font-medium text-orange-700">
                  <Sparkles className="mr-1 inline size-3.5" aria-hidden />
                  {payload.sprints.length} sprint(s) ativas consideradas
                </p>
              ) : null}
            </div>
          </div>
          <OfferGrid offers={recommended} keyPrefix="rec" />
        </section>
      ) : null}

      {/* Prateleiras padrão (genérico ou complementar ao contextual) */}
      <MarketplaceShelf
        title={SHELF_META.formacao.title}
        description={SHELF_META.formacao.description}
        category="formacao"
        limit={4}
      />
      <MarketplaceShelf
        title={SHELF_META.equipamentos.title}
        description={SHELF_META.equipamentos.description}
        category="equipamentos"
        limit={4}
      />
      <MarketplaceShelf
        title={SHELF_META.software.title}
        description={SHELF_META.software.description}
        category="software"
        limit={4}
      />
    </div>
  );
}
