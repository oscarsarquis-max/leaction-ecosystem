'use client';

import { Suspense, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useHubSession } from '@/context/HubSessionContext';
import { OffersVitrine } from '@/components/home/OffersVitrine';
import {
  LoggedAreaSidebar,
  type LoggedAreaNavId,
} from '@/components/logged-area/LoggedAreaSidebar';
import { LoggedAreaMain } from '@/components/logged-area/LoggedAreaMain';
import { LoggedAreaRightPanel } from '@/components/logged-area/LoggedAreaRightPanel';

function LoggedAreaShellInner() {
  const { user } = useHubSession();
  const searchParams = useSearchParams();
  const [active, setActive] = useState<LoggedAreaNavId>('inicio');

  useEffect(() => {
    if (searchParams.get('nav') === 'marketplace') {
      setActive('marketplace');
    }
  }, [searchParams]);

  const userName = useMemo(() => {
    const name = String(user?.name || '').trim();
    if (name) return name;
    const email = String(user?.email || '').trim();
    if (email.includes('@')) return email.split('@')[0];
    return 'LeActioner';
  }, [user?.name, user?.email]);

  return (
    <div className="flex h-screen overflow-hidden bg-stone-50 text-stone-900">
      <LoggedAreaSidebar active={active} onNavigate={setActive} />

      <main className="min-w-0 flex-1 overflow-y-auto bg-stone-50 p-6 md:p-8">
        {active === 'inicio' ? (
          <LoggedAreaMain userName={userName} />
        ) : (
          <div className="mx-auto w-full max-w-4xl">
            <header className="mb-6">
              <h1 className="text-2xl font-bold tracking-tight text-stone-900">Marketplace B2B</h1>
              <p className="mt-1 text-sm text-stone-500">
                Curadoria e ofertas — o mesmo fluxo de carrinho e checkout de sempre.
              </p>
            </header>
            <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm md:p-6">
              <OffersVitrine />
            </div>
          </div>
        )}
      </main>

      <div className="hidden lg:block">
        <LoggedAreaRightPanel userName={userName} userEmail={user?.email} />
      </div>
    </div>
  );
}

export function LoggedAreaShell() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen items-center justify-center bg-stone-50 text-sm text-stone-500">
          Carregando…
        </div>
      }
    >
      <LoggedAreaShellInner />
    </Suspense>
  );
}
