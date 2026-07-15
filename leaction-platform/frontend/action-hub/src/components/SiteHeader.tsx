'use client';

import { Suspense } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { Header } from '@/components/Header';
import { parseClientId } from '@/lib/client-branding';
import { parseCheckoutOrderId } from '@/lib/hub-api';

function SiteHeaderInner() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const checkoutId = parseCheckoutOrderId(searchParams.get('checkout'));
  const clientId = parseClientId(searchParams.get('client'));

  // Home SaaS tem shell próprio (sidebar + action center) — sem barra global.
  if (pathname === '/') {
    return null;
  }

  // Checkout white-label: chrome do parceiro assume o header.
  if (pathname === '/dashboard' && (checkoutId.length > 0 || clientId.length > 0)) {
    return null;
  }

  if (pathname.startsWith('/checkout/')) {
    return null;
  }

  return <Header />;
}

/** Oculta o header padrão do ActionHub durante checkout white-label do parceiro. */
export function SiteHeader() {
  return (
    <Suspense fallback={null}>
      <SiteHeaderInner />
    </Suspense>
  );
}
