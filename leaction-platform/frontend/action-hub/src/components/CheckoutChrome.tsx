'use client';

import type { ReactNode } from 'react';
import type { ClientBrandTheme } from '@/lib/client-branding';
import { getCheckoutContentOffset } from '@/lib/client-branding';
import { ClientCheckoutHeader } from '@/components/ClientCheckoutHeader';

type CheckoutChromeProps = {
  brand: ClientBrandTheme;
  subtitle?: string;
  children: ReactNode;
  className?: string;
};

/** Layout de checkout com header do cliente e fundo alinhado ao produto de origem. */
export function CheckoutChrome({ brand, subtitle, children, className = '' }: CheckoutChromeProps) {
  const contentOffset = getCheckoutContentOffset(brand);

  return (
    <>
      <ClientCheckoutHeader brand={brand} subtitle={subtitle} />
      <div
        className={`min-h-screen pb-12 ${className}`}
        style={{
          backgroundColor: brand.colors.pageBg,
          paddingTop: `${contentOffset}px`,
        }}
      >
        {children}
      </div>
    </>
  );
}
