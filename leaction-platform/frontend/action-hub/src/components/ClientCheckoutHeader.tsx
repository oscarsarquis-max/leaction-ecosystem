'use client';

import Image from 'next/image';
import type { ClientBrandTheme } from '@/lib/client-branding';

type ClientCheckoutHeaderProps = {
  brand: ClientBrandTheme;
  subtitle?: string;
};

const DEFAULT_LOGO_LAYOUT = { heightPx: 120, marginTopPx: 40, borderPx: 4 };

/**
 * Cabeçalho de checkout white-label — mesmo comportamento do PanelDX:
 * barra 60px (#1f2937) e logo à direita com margin-top 40px / height 120px,
 * invadindo a área útil abaixo (style.css `.header-logo`).
 */
export function ClientCheckoutHeader({ brand, subtitle }: ClientCheckoutHeaderProps) {
  const logoLayout = brand.logoLayout ?? DEFAULT_LOGO_LAYOUT;

  return (
    <header
      className="fixed left-0 top-0 z-[60] h-[60px] w-full overflow-visible border-b border-black/20 shadow-md"
      style={{ backgroundColor: brand.colors.headerBg, color: brand.colors.textOnHeader }}
    >
      <div className="mx-auto flex w-full max-w-6xl justify-between gap-4 px-4 md:px-5">
        <div className="flex h-[60px] min-w-0 flex-1 items-center">
          <div className="min-w-0">
            <p
              className="truncate text-[11px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: brand.colors.textMutedOnHeader }}
            >
              {brand.id === 'paneldx' ? 'Pagamento seguro · PanelDX' : 'Pagamento seguro · ActionHub'}
            </p>
            <h1 className="truncate text-base font-bold tracking-tight md:text-lg">
              {brand.checkoutTitle}
            </h1>
            {(subtitle || brand.productLabel) && (
              <p
                className="hidden truncate text-xs sm:block"
                style={{ color: brand.colors.textMutedOnHeader }}
              >
                {subtitle || brand.productLabel}
              </p>
            )}
          </div>
        </div>

        <div className="relative z-[61] flex shrink-0 items-start">
          <Image
            src={brand.logo}
            alt={brand.logoAlt}
            width={brand.logo.width}
            height={brand.logo.height}
            priority
            className="box-border w-auto shrink-0 rounded bg-white object-contain p-px"
            style={{
              height: `${logoLayout.heightPx}px`,
              marginTop: `${logoLayout.marginTopPx}px`,
              borderWidth: `${logoLayout.borderPx}px`,
              borderStyle: 'solid',
              borderColor: '#bdc3c7',
              maxWidth: 'min(220px, 42vw)',
            }}
          />
        </div>
      </div>
    </header>
  );
}
