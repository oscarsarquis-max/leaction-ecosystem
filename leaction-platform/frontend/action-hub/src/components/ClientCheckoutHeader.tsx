'use client';

import Image from 'next/image';
import type { ClientBrandTheme } from '@/lib/client-branding';

type ClientCheckoutHeaderProps = {
  brand: ClientBrandTheme;
  subtitle?: string;
};

/**
 * Cabeçalho de checkout — padrão ActionHub (logo inline, sem suspensão).
 * White-label só nos textos/cores do parceiro.
 */
export function ClientCheckoutHeader({ brand, subtitle }: ClientCheckoutHeaderProps) {
  return (
    <header
      className="fixed left-0 top-0 z-[60] h-[60px] w-full border-b border-stone-200/80 bg-white/95 shadow-sm backdrop-blur-md"
    >
      <div className="mx-auto flex h-[60px] w-full max-w-6xl items-center justify-between gap-4 px-4 md:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <Image
            src={brand.logo}
            alt={brand.logoAlt}
            width={40}
            height={40}
            priority
            className="h-10 w-10 shrink-0 rounded-xl bg-white object-cover shadow-sm ring-1 ring-stone-200/80"
          />
          <div className="min-w-0">
            <p
              className="truncate text-[11px] font-semibold uppercase tracking-[0.14em] text-stone-400"
            >
              {brand.id === 'paneldx' ? 'Pagamento seguro · PanelDX' : 'Pagamento seguro · ActionHub'}
            </p>
            <h1 className="truncate text-base font-bold tracking-tight text-orange-950 md:text-lg">
              {brand.checkoutTitle}
            </h1>
            {(subtitle || brand.productLabel) && (
              <p className="hidden truncate text-xs text-stone-500 sm:block">
                {subtitle || brand.productLabel}
              </p>
            )}
          </div>
        </div>
        <span
          className="hidden rounded-full px-3 py-1 text-xs font-semibold sm:inline-flex"
          style={{
            backgroundColor: brand.colors.accentMuted || '#fff7ed',
            color: brand.colors.accent || '#c2410c',
          }}
        >
          {brand.displayName}
        </span>
      </div>
    </header>
  );
}
