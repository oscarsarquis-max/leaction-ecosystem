'use client';

import Link from 'next/link';
import { ArrowLeft, Home } from 'lucide-react';

type BackToHubHomeProps = {
  label?: string;
  className?: string;
  /** `link` = texto com seta; `chip` = botão compacto; `icon` = só ícone (header). */
  variant?: 'link' | 'chip' | 'icon';
};

/** Volta à home do Action Hub sem encerrar a sessão (`actionhub_session`). */
export function BackToHubHome({
  label = 'Voltar ao Action Hub',
  className = '',
  variant = 'link',
}: BackToHubHomeProps) {
  if (variant === 'icon') {
    return (
      <Link
        href="/"
        className={
          className ||
          'inline-flex items-center justify-center rounded-lg p-2 text-slate-600 transition hover:bg-slate-100 hover:text-orange-800'
        }
        aria-label="Início — Action Hub"
        title="Início"
      >
        <Home className="size-5" aria-hidden />
      </Link>
    );
  }

  if (variant === 'chip') {
    return (
      <Link
        href="/"
        className={
          className ||
          'inline-flex items-center gap-1.5 rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-xs font-semibold text-stone-600 transition hover:border-orange-300 hover:text-orange-800'
        }
      >
        <Home className="size-3.5" aria-hidden />
        {label}
      </Link>
    );
  }

  return (
    <Link
      href="/"
      className={
        className ||
        'mb-3 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 transition hover:text-orange-800'
      }
    >
      <ArrowLeft className="size-4" aria-hidden />
      {label}
    </Link>
  );
}
