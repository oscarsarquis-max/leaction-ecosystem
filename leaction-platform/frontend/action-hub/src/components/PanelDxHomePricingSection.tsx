'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Loader2 } from 'lucide-react';
import { PanelDxPricingCards } from '@/components/PanelDxPricingCards';
import { resolveClientBrand } from '@/lib/client-branding';
import { isPanelDxHubLinked } from '@/lib/paneldx-hub-link';
import {
  fetchPanelDxPlanosVitrineWithMeta,
  formatVitrineUpdatedAt,
  type PanelDxPlanoVitrine,
  type PanelDxVitrineSource,
} from '@/lib/paneldx-api';

const PANELDX_BRAND = resolveClientBrand('paneldx')!;

type PanelDxHomePricingSectionProps = {
  sectionId?: string;
  showCheckoutLink?: boolean;
};

/** Planos PanelDX — valores do CRM (via gateway), não hardcoded. */
export function PanelDxHomePricingSection(props: PanelDxHomePricingSectionProps) {
  if (!isPanelDxHubLinked()) return null;
  return <PanelDxHomePricingSectionInner {...props} />;
}

function PanelDxHomePricingSectionInner({
  sectionId = 'planos-paneldx',
  showCheckoutLink = true,
}: PanelDxHomePricingSectionProps) {
  const [planos, setPlanos] = useState<PanelDxPlanoVitrine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [source, setSource] = useState<PanelDxVitrineSource | undefined>();
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setLoading(true);
        setError('');
        const result = await fetchPanelDxPlanosVitrineWithMeta();
        if (cancelled) return;
        setPlanos(result.planos);
        setSource(result.source);
        setUpdatedAt(formatVitrineUpdatedAt(result.received_at));
        if (!result.planos.length) {
          setError(
            'Nenhum plano ativo no CRM PanelDX. Cadastre planos no admin e publique a vitrine.'
          );
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Planos indisponíveis.');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const sourceLabel =
    source === 'paneldx_live'
      ? 'Valores em tempo real do CRM PanelDX'
      : source === 'hub_cache'
        ? 'Valores do cache publicado (CRM offline)'
        : null;

  return (
    <section
      id={sectionId}
      className="scroll-mt-6 border-t border-slate-200 bg-white px-4 py-16 md:px-6 md:py-20"
      aria-labelledby="planos-paneldx-titulo"
    >
      <div className="mx-auto max-w-6xl">
        <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="text-center md:text-left">
            <h2 id="planos-paneldx-titulo" className="text-3xl font-extrabold tracking-tight text-red-950 md:text-4xl">
              Nosso Catálogo — Planos PanelDX
            </h2>
            <p className="mt-3 max-w-2xl text-slate-700">
              Catálogo sincronizado com o CRM PanelDX — altere preços no admin e eles aparecem aqui
              automaticamente.
            </p>
            {sourceLabel ? (
              <p className="mt-2 text-xs font-medium text-slate-500">
                {sourceLabel}
                {updatedAt ? ` · ${updatedAt}` : ''}
              </p>
            ) : null}
          </div>
          {showCheckoutLink ? (
            <Link
              href="/checkout/paneldx"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-red-600 px-6 py-3 text-sm font-bold text-white transition hover:bg-red-700"
            >
              Ver checkout white-label
              <ArrowRight className="size-4" aria-hidden />
            </Link>
          ) : null}
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-slate-600">
            <Loader2 className="size-5 animate-spin" aria-hidden />
            Carregando planos do CRM...
          </div>
        ) : error ? (
          <p className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-900">{error}</p>
        ) : (
          <PanelDxPricingCards
            planos={planos}
            brand={PANELDX_BRAND}
            onAssinar={(plano) => {
              window.location.href = `/checkout/paneldx?plan_id=${plano.id}`;
            }}
          />
        )}
      </div>
    </section>
  );
}
