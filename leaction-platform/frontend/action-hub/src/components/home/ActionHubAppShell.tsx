'use client';

import { ServicesSidebar } from '@/components/home/ServicesSidebar';
import { OffersVitrine } from '@/components/home/OffersVitrine';
import { ActionCenter } from '@/components/home/ActionCenter';

/**
 * Shell SaaS ActionHub — 3 colunas (sidebar · vitrine · action center).
 * Desktop: 100dvh, overflow interno. Mobile: colunas empilhadas.
 */
export function ActionHubAppShell() {
  return (
    <div className="bg-stone-50 text-stone-800 md:h-[100dvh] md:overflow-hidden">
      <div className="mx-auto flex h-full max-w-[1600px] flex-col gap-4 p-4 md:grid md:grid-cols-12 md:gap-6 md:p-6">
        {/* Sidebar — serviços */}
        <div className="md:col-span-3 md:min-h-0 md:overflow-hidden">
          <div className="md:h-full">
            <ServicesSidebar />
          </div>
        </div>

        {/* Centro — vitrine (scroll independente) */}
        <main className="min-h-0 flex-1 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm md:col-span-6 md:overflow-hidden md:p-6">
          <div className="flex h-full min-h-[60vh] flex-col md:min-h-0">
            <OffersVitrine />
          </div>
        </main>

        {/* Direita — Action Center */}
        <div className="md:col-span-3 md:min-h-0 md:overflow-hidden">
          <div className="md:h-full">
            <ActionCenter />
          </div>
        </div>
      </div>
    </div>
  );
}
