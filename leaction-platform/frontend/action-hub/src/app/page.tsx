'use client';

import Link from 'next/link';
import { ArrowRight, Headphones, Sparkles } from 'lucide-react';
import { ActionHubBrandHeader } from '@/components/ActionHubBrandHeader';
import { MarketplaceShelf } from '@/components/Marketplace/MarketplaceShelf';
import { MultivendorSearchBox } from '@/components/Marketplace/MultivendorSearchBox';

export default function ActionHubPage() {
  const scrollToSection = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <ActionHubBrandHeader
        left={
          <Link
            href="/dashboard"
            className="inline-flex shrink-0 items-center rounded-xl border-2 border-orange-500 bg-white/95 px-5 py-2 text-sm font-bold text-orange-500 transition hover:bg-orange-500 hover:text-white md:px-6 md:py-2.5 md:text-base"
          >
            Entrar no Hub
          </Link>
        }
      />

      {/* Hero corporativo */}
      <section className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-red-950 px-4 py-20 text-white md:px-6 md:py-28">
        <div
          className="pointer-events-none absolute inset-0 opacity-25"
          aria-hidden
          style={{
            backgroundImage:
              'radial-gradient(circle at 15% 25%, rgba(249,115,22,0.4) 0%, transparent 50%), radial-gradient(circle at 85% 70%, rgba(148,163,184,0.2) 0%, transparent 45%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl text-center">
          <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-sm font-semibold text-orange-300">
            <Sparkles className="size-4" aria-hidden />
            LeAction · Action Hub
          </p>
          <h1 className="text-4xl font-extrabold leading-tight tracking-tight md:text-5xl lg:text-6xl">
            Soluções de Transformação Digital{' '}
            <span className="bg-gradient-to-r from-orange-400 to-amber-200 bg-clip-text text-transparent">
              para sua Empresa
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-3xl text-lg leading-relaxed text-slate-300 md:text-xl">
            Vitrine curada por categoria de necessidade — formação executiva, infraestrutura de TI e
            software corporativo — com ofertas selecionadas para acelerar a maturidade digital da sua
            organização.
          </p>
          <button
            type="button"
            onClick={() => scrollToSection('vitrine-prateleiras')}
            className="mt-10 inline-flex items-center gap-2 rounded-xl bg-orange-500 px-8 py-3.5 text-base font-bold text-white shadow-lg shadow-orange-500/20 transition hover:bg-orange-400"
          >
            Explorar prateleiras
            <ArrowRight className="size-5" aria-hidden />
          </button>
        </div>
      </section>

      {/* Prateleiras temáticas B2B */}
      <section
        id="vitrine-prateleiras"
        className="scroll-mt-6 px-4 py-16 md:px-6 md:py-24"
        aria-labelledby="vitrine-prateleiras-titulo"
      >
        <div className="mx-auto max-w-6xl space-y-12 md:space-y-16">
          <div className="max-w-3xl">
            <p className="mb-2 text-sm font-semibold uppercase tracking-wide text-orange-600">
              Curadoria B2B
            </p>
            <h2
              id="vitrine-prateleiras-titulo"
              className="text-3xl font-extrabold tracking-tight text-slate-900 md:text-4xl"
            >
              Prateleiras temáticas
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-slate-600">
              Conteúdo organizado pela dor do cliente, com filtros de relevância corporativa aplicados
              pelo motor de curadoria do Action Hub.
            </p>
          </div>

          <div
            id="buscador-solucoes"
            className="scroll-mt-6 rounded-3xl border border-rose-100 bg-gradient-to-b from-rose-50 via-rose-50/90 to-rose-50/60 px-4 py-10 md:px-8 md:py-12"
            aria-labelledby="buscador-solucoes-titulo"
          >
            <h2 id="buscador-solucoes-titulo" className="sr-only">
              Buscador de soluções por categoria
            </h2>
            <MultivendorSearchBox />
          </div>

          <MarketplaceShelf
            title="Biblioteca da Transformação"
            description="Conteúdo executivo e metodologias"
            category="formacao"
            limit={4}
          />

          <MarketplaceShelf
            title="Infraestrutura Inteligente"
            description="Equipamentos corporativos de rede e automação"
            category="equipamentos"
            limit={4}
          />

          <MarketplaceShelf
            title="Sistemas Core"
            description="Licenças e softwares de gestão e segurança"
            category="software"
            limit={4}
          />
        </div>
      </section>

      {/* CTA Hub */}
      <section className="border-t border-slate-200 bg-white px-4 py-16 md:px-6 md:py-20" aria-labelledby="hub-cta">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mb-4 inline-flex items-center justify-center rounded-full bg-orange-50 p-3">
            <Headphones className="size-6 text-orange-500" aria-hidden />
          </div>
          <h2 id="hub-cta" className="text-3xl font-extrabold tracking-tight text-slate-900 md:text-4xl">
            Pronto para ir além da vitrine?
          </h2>
          <p className="mt-4 text-lg leading-relaxed text-slate-600">
            Acesse o Hub para diagnósticos, serviços LeAction e gestão da sua jornada digital.
          </p>
          <Link
            href="/dashboard"
            className="mt-8 inline-flex items-center gap-2 rounded-xl bg-orange-500 px-8 py-3.5 text-base font-bold text-white transition hover:bg-orange-400"
          >
            Acessar Dashboard
            <ArrowRight className="size-5" aria-hidden />
          </Link>
        </div>
      </section>
    </div>
  );
}
