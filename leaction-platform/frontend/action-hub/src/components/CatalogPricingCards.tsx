'use client';

import { CheckCircle2, Loader2 } from 'lucide-react';
import {
  formatCatalogCurrency,
  type CatalogPlanPublic,
} from '@/lib/catalog-api';
import type { ClientBrandTheme } from '@/lib/client-branding';

type Props = {
  plans: CatalogPlanPublic[];
  brand: ClientBrandTheme;
  selectedSku?: string | null;
  loadingSku?: string | null;
  onSelect: (plan: CatalogPlanPublic) => void;
  highlightMiddle?: boolean;
  ctaLabel?: string;
};

function periodLabel(plan: CatalogPlanPublic): string | null {
  const months = plan.period_months;
  const raw = (plan.periodicidade || '').toLowerCase();
  if (raw.includes('anual') || months === 12) return '/ano';
  if (raw.includes('mensal') || months === 1) return '/mês';
  if (plan.type === 'credit_pack') return 'avulso';
  return null;
}

export function CatalogPricingCards({
  plans,
  brand,
  selectedSku,
  loadingSku,
  onSelect,
  highlightMiddle = true,
  ctaLabel,
}: Props) {
  if (!plans.length) {
    return (
      <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-600">
        Não há planos disponíveis no momento. Tente novamente em breve.
      </p>
    );
  }

  const middleIndex = Math.floor(plans.length / 2);

  return (
    <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
      {plans.map((plan, index) => {
        const isHighlight =
          Boolean(plan.recommended) ||
          (highlightMiddle && !plans.some((p) => p.recommended) && plans.length > 1 && index === middleIndex);
        const isSelected = selectedSku === plan.sku;
        const isLoading = loadingSku === plan.sku;
        const period = periodLabel(plan);

        return (
          <article
            key={plan.id}
            className={`flex flex-col rounded-2xl border bg-white p-6 shadow-md transition md:p-8 ${
              isHighlight || isSelected
                ? 'border-2 shadow-lg'
                : 'border-slate-200 hover:-translate-y-0.5 hover:shadow-lg'
            }`}
            style={
              isHighlight || isSelected
                ? { borderColor: brand.colors.accent }
                : undefined
            }
          >
            {isHighlight ? (
              <span
                className="mb-4 inline-flex w-fit rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide text-white"
                style={{ backgroundColor: brand.colors.accent }}
              >
                Recomendado
              </span>
            ) : null}

            <h3 className="text-2xl font-bold" style={{ color: brand.colors.accentHover }}>
              {plan.name}
            </h3>

            <div className="mt-4">
              <p className="text-3xl font-black text-slate-900">
                {formatCatalogCurrency(plan.price, plan.currency)}
                {period ? (
                  <span className="ml-1 text-base font-semibold text-slate-500">{period}</span>
                ) : null}
              </p>
              {period === '/mês' ? (
                <p className="mt-1 text-xs font-medium text-slate-500">cobrança mensal</p>
              ) : null}
              {period === '/ano' ? (
                <p className="mt-1 text-xs font-medium text-slate-500">pagamento anual antecipado</p>
              ) : null}
              {plan.type === 'credit_pack' && plan.credits != null ? (
                <p
                  className="mt-3 inline-flex rounded-lg px-3 py-1.5 text-sm font-bold"
                  style={{
                    color: brand.colors.accentHover,
                    backgroundColor: `${brand.colors.accent}14`,
                  }}
                >
                  +{plan.credits} desafio{plan.credits === 1 ? '' : 's'}
                </p>
              ) : null}
              {plan.licenses_granted != null && plan.licenses_granted > 0 ? (
                <p
                  className="mt-3 inline-flex rounded-lg px-3 py-1.5 text-sm font-bold"
                  style={{
                    color: brand.colors.accentHover,
                    backgroundColor: `${brand.colors.accent}14`,
                  }}
                >
                  {plan.licenses_granted}{' '}
                  {plan.licenses_granted === 1 ? 'licença de professor' : 'licenças de professor'}
                </p>
              ) : null}
            </div>

            <ul className="mt-6 flex-1 space-y-3">
              {(plan.features || []).map((beneficio) => (
                <li key={beneficio} className="flex gap-2 text-sm text-slate-700">
                  <CheckCircle2
                    className="mt-0.5 h-4 w-4 shrink-0"
                    style={{ color: brand.colors.accent }}
                  />
                  <span>{beneficio}</span>
                </li>
              ))}
            </ul>

            <button
              type="button"
              disabled={Boolean(loadingSku)}
              onClick={() => onSelect(plan)}
              className="mt-8 inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold text-white transition hover:opacity-95 disabled:cursor-wait disabled:opacity-70"
              style={{ backgroundColor: brand.colors.accent }}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Preparando…
                </>
              ) : ctaLabel ? (
                ctaLabel
              ) : plan.type === 'credit_pack' ? (
                'Comprar agora'
              ) : (
                'Quero este plano'
              )}
            </button>
          </article>
        );
      })}
    </div>
  );
}
