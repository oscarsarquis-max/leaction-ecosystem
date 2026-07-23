'use client';

import { ArrowRight, Sparkles } from 'lucide-react';
import { INOVE_HERO } from '@/components/public-portal/mock-data';

type PortalHeroColumnProps = {
  onDiscover: () => void;
};

/** Coluna central — vitrine Inove4us. */
export function PortalHeroColumn({ onDiscover }: PortalHeroColumnProps) {
  return (
    <article className="flex h-full flex-col rounded-2xl border border-stone-200 bg-white p-6 shadow-sm md:p-8">
      <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-orange-50 px-3 py-1 text-xs font-bold text-orange-600">
        <Sparkles className="size-3.5" aria-hidden />
        {INOVE_HERO.badge}
      </span>

      <h1 className="mt-5 text-3xl font-bold tracking-tight text-stone-900 md:text-4xl lg:text-[2.5rem] lg:leading-tight">
        {INOVE_HERO.title}
      </h1>

      <p className="mt-4 max-w-xl text-base leading-relaxed text-stone-500 md:text-lg">
        {INOVE_HERO.subtitle}
      </p>

      <button
        type="button"
        onClick={onDiscover}
        className="mt-6 inline-flex w-fit items-center gap-2 rounded-xl bg-orange-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-orange-600"
      >
        {INOVE_HERO.cta}
        <ArrowRight className="size-4" aria-hidden />
      </button>

      <div
        className="mt-6 flex h-48 flex-1 items-center justify-center rounded-lg bg-stone-100"
        aria-hidden
      >
        <div className="flex flex-col items-center gap-3 text-center">
          <img
            src="/brands/inove4us.png"
            alt=""
            className="h-16 w-16 rounded-2xl object-cover shadow-sm ring-1 ring-stone-200"
          />
          <p className="text-xs font-medium text-stone-500">
            Ilustração da ferramenta · em breve
          </p>
        </div>
      </div>

      <p className="mt-4 text-center text-xs text-stone-500 md:text-left">
        ActionHub · MudaEdu — portal B2B para líderes que transformam.
      </p>
    </article>
  );
}
