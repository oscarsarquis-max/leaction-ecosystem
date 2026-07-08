'use client';

import { CheckCircle2, Loader2 } from 'lucide-react';
import {
  formatPanelDxCurrency,
  formatPanelDxSeatLabel,
  type PanelDxPlanoVitrine,
} from '@/lib/paneldx-api';
import type { ClientBrandTheme } from '@/lib/client-branding';

type PanelDxPricingCardsProps = {
  planos: PanelDxPlanoVitrine[];
  brand: ClientBrandTheme;
  clientId?: string;
  selectedPlanId?: number | null;
  loadingPlanId?: number | null;
  onAssinar: (plano: PanelDxPlanoVitrine) => void;
  highlightMiddle?: boolean;
};

export function PanelDxPricingCards({
  planos,
  brand,
  clientId,
  selectedPlanId,
  loadingPlanId,
  onAssinar,
  highlightMiddle = true,
}: PanelDxPricingCardsProps) {
  if (!planos.length) {
    return (
      <p className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-600">
        Nenhum plano ativo disponível no momento. Tente novamente em instantes.
      </p>
    );
  }

  const middleIndex = Math.floor(planos.length / 2);

  return (
    <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
      {planos.map((plano, index) => {
        const isHighlight = highlightMiddle && planos.length > 1 && index === middleIndex;
        const isSelected = selectedPlanId === plano.id;
        const isLoading = loadingPlanId === plano.id;

        return (
          <article
            key={plano.id}
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
            {isHighlight && (
              <span
                className="mb-4 inline-flex w-fit rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide text-white"
                style={{ backgroundColor: brand.colors.accent }}
              >
                Recomendado
              </span>
            )}

            <h3 className="text-2xl font-bold" style={{ color: brand.colors.accentHover }}>
              {plano.nome}
            </h3>

            <div className="mt-4">
              <p className="text-3xl font-black text-slate-900">
                {formatPanelDxCurrency(plano.valor_mensal)}
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-500">
                / {plano.periodicidade || 'Mensal'}
              </p>
              <p
                className="mt-3 inline-flex rounded-lg px-3 py-1.5 text-sm font-bold"
                style={{
                  color: brand.colors.accentHover,
                  backgroundColor: `${brand.colors.accent}14`,
                }}
              >
                {formatPanelDxSeatLabel(plano.max_usuarios)}
              </p>
            </div>

            <ul className="mt-6 flex-1 space-y-3">
              {(plano.descricao_beneficios || []).map((beneficio) => (
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
              onClick={() => onAssinar(plano)}
              disabled={!!loadingPlanId}
              className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-xl px-6 py-3.5 text-sm font-bold text-white transition disabled:cursor-not-allowed disabled:opacity-70"
              style={{ backgroundColor: brand.colors.accent }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = brand.colors.accentHover;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = brand.colors.accent;
              }}
            >
              {isLoading ? (
                <>
                  <Loader2 className="size-5 animate-spin" aria-hidden />
                  Processando...
                </>
              ) : (
                'Assinar'
              )}
            </button>

            {clientId ? (
              <p className="mt-3 text-center text-xs text-slate-400">
                Cliente PanelDX #{clientId} · Plano #{plano.id}
              </p>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
