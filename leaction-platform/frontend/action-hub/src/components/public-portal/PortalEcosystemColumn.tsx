'use client';

import { Award, Cloud } from 'lucide-react';
import { ECOSYSTEM_CARDS } from '@/components/public-portal/mock-data';

const ICONS = {
  cloud: Cloud,
  shield: Award,
} as const;

/** Coluna esquerda — ecossistema e parcerias (conceitual). */
export function PortalEcosystemColumn() {
  return (
    <div className="flex h-full flex-col gap-4">
      <div className="px-1">
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-stone-500">
          Ecossistema
        </p>
        <h2 className="mt-1 text-lg font-bold tracking-tight text-stone-900">
          Hub de valor MudaEdu
        </h2>
        <p className="mt-1 text-sm leading-relaxed text-stone-500">
          Você está entrando em uma rede executiva de transformação digital.
        </p>
      </div>

      {ECOSYSTEM_CARDS.map((card) => {
        const Icon = ICONS[card.icon];
        return (
          <article
            key={card.id}
            className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm"
          >
            <span className="flex size-10 items-center justify-center rounded-xl bg-orange-50 text-orange-600">
              <Icon className="size-5" aria-hidden />
            </span>
            <h3 className="mt-3 text-sm font-bold text-stone-900">{card.title}</h3>
            <p className="mt-1.5 text-sm leading-relaxed text-stone-500">{card.body}</p>
          </article>
        );
      })}
    </div>
  );
}
