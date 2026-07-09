'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { ContextualVitrineSection } from '@/components/Marketplace/ContextualVitrineSection';
import { HeroCurationShortcut } from '@/components/Marketplace/HeroCurationShortcut';
import { MultivendorSearchBox } from '@/components/Marketplace/MultivendorSearchBox';

export default function ActionHubPage() {
  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-orange-50/40 text-slate-800">
      {/* Hero leve — logo no centro (estilo Chamelleon, branding ActionHub) */}
      <section className="px-4 pb-10 pt-8 md:px-6 md:pb-14 md:pt-12">
        <div className="mx-auto max-w-2xl text-center">
          <img
            src="/logo.png"
            alt="ActionHub"
            className="mx-auto mb-5 h-20 w-20 rounded-2xl object-cover shadow-sm ring-1 ring-slate-200/80 md:h-24 md:w-24"
          />
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-orange-600">
            LeAction · Action Hub
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Soluções para a transformação digital da sua empresa
          </h1>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-slate-500 md:text-base">
            Formação, infraestrutura e software — curados para acelerar a maturidade digital.
            Navegue sem login; identifique-se só no checkout ou no histórico.
          </p>
          <div className="mt-7 flex flex-col items-center gap-3">
            <button
              type="button"
              onClick={() => scrollToSection('vitrine-prateleiras')}
              className="inline-flex items-center gap-2 rounded-lg bg-orange-500 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-orange-400"
            >
              Explorar soluções
              <ArrowRight className="size-4" aria-hidden />
            </button>
            <HeroCurationShortcut />
          </div>
        </div>
      </section>

      <section
        id="vitrine-prateleiras"
        className="scroll-mt-6 px-4 pb-12 md:px-6 md:pb-16"
        aria-labelledby="vitrine-prateleiras-titulo"
      >
        <div className="mx-auto mb-10 max-w-5xl">
          <MultivendorSearchBox />
        </div>
        <ContextualVitrineSection />
      </section>

      <section
        className="border-t border-slate-200/80 bg-white/70 px-4 py-12 md:px-6 md:py-14"
        aria-labelledby="hub-cta"
      >
        <div className="mx-auto max-w-lg text-center">
          <h2 id="hub-cta" className="text-xl font-bold tracking-tight text-slate-900 md:text-2xl">
            Precisa do histórico ou do checkout?
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-slate-500">
            Entre com e-mail e senha no topo da página para ver pedidos e concluir compras.
          </p>
          <Link
            href="/dashboard"
            className="mt-6 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-orange-300 hover:text-orange-700"
          >
            Ir para meus pedidos
            <ArrowRight className="size-4" aria-hidden />
          </Link>
        </div>
      </section>
    </div>
  );
}
