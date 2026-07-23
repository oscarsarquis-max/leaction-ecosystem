'use client';

import { PortalAccessColumn } from '@/components/public-portal/PortalAccessColumn';
import { PortalEcosystemColumn } from '@/components/public-portal/PortalEcosystemColumn';
import { PortalHeroColumn } from '@/components/public-portal/PortalHeroColumn';

function focusLogin() {
  const el = document.getElementById('actionhub-login');
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const input = el.querySelector<HTMLInputElement>('input[type="email"]');
    input?.focus();
  }
}

/**
 * Home pública — Portal B2B Executivo.
 * Mobile: Login → Centro → Ecossistema. Desktop: 3 colunas.
 */
export function PublicPortalShell() {
  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      <header className="border-b border-stone-200 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-4 md:px-6">
          <img
            src="/logo.png"
            alt="ActionHub"
            className="h-10 w-10 rounded-xl object-cover shadow-sm ring-1 ring-stone-200"
          />
          <div>
            <p className="text-lg font-bold leading-none tracking-tight text-stone-900">
              ActionHub
            </p>
            <p className="mt-0.5 text-[10px] font-semibold uppercase tracking-wider text-stone-500">
              MudaEdu · Portal B2B Executivo
            </p>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl p-4 md:p-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          {/* Esquerda — no mobile vai por último */}
          <div className="order-3 lg:order-1 lg:col-span-3">
            <PortalEcosystemColumn />
          </div>

          {/* Centro */}
          <div className="order-2 lg:order-2 lg:col-span-6">
            <PortalHeroColumn onDiscover={focusLogin} />
          </div>

          {/* Direita / Login — no mobile primeiro */}
          <div className="order-1 lg:order-3 lg:col-span-3">
            <PortalAccessColumn />
          </div>
        </div>
      </div>
    </div>
  );
}
