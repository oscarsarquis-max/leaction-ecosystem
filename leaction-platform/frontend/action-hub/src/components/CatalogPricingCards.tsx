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
};

export function CatalogPricingCards({
  plans,
  brand,
  selectedSku,
  loadingSku,
  onSelect,
  highlightMiddle = true,
}: Props) {
  if (!plans.length) {
    return (
      <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-600">
        Nenhum plano ativo no catálogo. Cadastre em Admin → Planos.
      </p>
    );
  }

  const middleIndex = Math.floor(plans.length / 2);

  return (
    <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
      {plans.map((plan, index) => {
        const isHighlight = highlightMiddle && plans.length > 1 && index === middleIndex;
        const isSelected = selectedSku === plan.sku;
        const isLoading = loadingSku === plan.sku;

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
              </p>
              {plan.credits != null ? (
                <p
                  className="mt-3 inline-flex rounded-lg px-3 py-1.5 text-sm font-bold"
                  style={{
                    color: brand.colors.accentHover,
                    backgroundColor: `${brand.colors.accent}14`,
                  }}
                >
                  +{plan.credits} créditos
                </p>
              ) : (
                <p className="mt-3 text-sm font-semibold text-slate-500">
                  {plan.type === 'credit_pack' ? 'Pacote de créditos' : 'Plano'}
                </p>
              )}
            </div>

            <ul className="mt-6 flex-1 space-y-3">
              {(plan.features || []).map((beneficio) => (
                <li key={beneficio} className="flex items-start gap-2 text-sm text-slate-700">
                  <CheckCircle2
                    className="mt-0.5 size-4 shrink-0"
                    style={{ color: brand.colors.success }}
                    aria-hidden
                  />
                  <span>{beneficio}</span>
                </li>
              ))}
            </ul>

            <button
              type="button"
              disabled={!!loadingSku}
              onClick={() => onSelect(plan)}
              className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-bold text-white transition disabled:cursor-wait disabled:opacity-70"
              style={{ backgroundColor: brand.colors.accent }}
            >
              {isLoading ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden />
                  Abrindo pagamento…
                </>
              ) : (
                'Continuar para pagamento'
              )}
            </button>
          </article>
        );
      })}
    </div>
  );
}
