'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';

type ActionHubBrandHeaderProps = {
  /** Conteúdo à direita (login / carrinho). */
  right?: ReactNode;
  /** @deprecated use `right` — mantido para chamadas antigas com `left`. */
  left?: ReactNode;
  /** Ignorado — padrão único alinhado à home SaaS. */
  variant?: 'classic' | 'light';
};

/**
 * Header global ActionHub — mesmo padrão da home:
 * barra clara, logo arredondada inline (sem logo suspensa).
 */
export function ActionHubBrandHeader({ right, left }: ActionHubBrandHeaderProps) {
  const controls = right ?? left;

  return (
    <header className="sticky top-0 z-[60] h-[60px] w-full border-b border-stone-200/80 bg-white/95 backdrop-blur-md">
      <div className="mx-auto flex h-[60px] max-w-7xl items-center justify-between gap-3 px-4 md:px-6">
        <Link
          href="/"
          className="flex min-w-0 items-center gap-2.5 transition hover:opacity-90"
          aria-label="Voltar ao início do Action Hub"
          title="Início"
        >
          <img
            src="/logo.png"
            alt="ActionHub"
            className="h-10 w-10 shrink-0 rounded-xl object-cover shadow-sm ring-1 ring-stone-200/80"
          />
          <div className="min-w-0">
            <p className="truncate text-lg font-bold leading-none tracking-tight text-orange-950">
              ActionHub
            </p>
            <p className="mt-0.5 hidden text-[10px] font-medium uppercase tracking-wider text-stone-400 sm:block">
              Início · Contextual Platform
            </p>
          </div>
        </Link>
        <div className="flex min-w-0 flex-1 items-center justify-end">{controls}</div>
      </div>
    </header>
  );
}
