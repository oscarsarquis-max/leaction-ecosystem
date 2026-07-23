'use client';

import { ArrowRight, Clock3, Sparkles } from 'lucide-react';
import {
  MOCK_RECENT_ACTIVITIES,
  resolveInove4usUrl,
} from '@/components/logged-area/mock-data';

type LoggedAreaMainProps = {
  userName: string;
};

export function LoggedAreaMain({ userName }: LoggedAreaMainProps) {
  const inoveUrl = resolveInove4usUrl();

  return (
    <div className="mx-auto w-full max-w-3xl space-y-8">
      <header>
        <h1 className="text-2xl font-bold tracking-tight text-stone-900 md:text-3xl">
          Bem-vindo de volta, {userName}
        </h1>
        <p className="mt-1.5 text-base text-stone-500">O que vamos transformar hoje?</p>
      </header>

      <section className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
        <div className="flex flex-col md:flex-row">
          <div className="flex flex-1 flex-col justify-center p-6 md:p-8">
            <p className="mb-2 inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-orange-600">
              <Sparkles className="size-3.5" aria-hidden />
              Ferramenta principal
            </p>
            <h2 className="text-xl font-bold tracking-tight text-stone-900 md:text-2xl">
              Acelere suas iniciativas com o Inove4us
            </h2>
            <p className="mt-2 max-w-md text-sm leading-relaxed text-stone-500">
              Diagnóstico, metodologias e execução em um só lugar — do insight à ação, com a Mesa
              do Inovador.
            </p>
            <a
              href={inoveUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-5 inline-flex w-fit items-center gap-2 rounded-xl bg-orange-500 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-orange-600"
            >
              Acessar Inove4us
              <ArrowRight className="size-4" aria-hidden />
            </a>
          </div>
          <div
            className="relative flex min-h-[160px] items-center justify-center md:w-56 lg:w-64"
            aria-hidden
          >
            <div className="absolute inset-0 bg-gradient-to-br from-orange-50 via-orange-100/80 to-stone-100" />
            <div className="relative flex size-24 items-center justify-center rounded-2xl bg-white/80 shadow-sm ring-1 ring-orange-200/60 backdrop-blur-sm">
              <img
                src="/brands/inove4us.png"
                alt=""
                className="h-14 w-14 rounded-xl object-cover"
              />
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-stone-500">
          Atividades Recentes
        </h2>
        <ul className="space-y-2">
          {MOCK_RECENT_ACTIVITIES.map((item) => (
            <li
              key={item.id}
              className="flex items-start gap-3 rounded-xl border border-stone-200 bg-white px-4 py-3 shadow-sm"
            >
              <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg bg-orange-50 text-orange-600">
                <Clock3 className="size-3.5" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-stone-900">{item.title}</p>
                <p className="text-xs text-stone-500">{item.detail}</p>
              </div>
              <span className="shrink-0 text-[11px] font-medium text-stone-500">{item.when}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
