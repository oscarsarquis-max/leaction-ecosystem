'use client';

import { LoggedAreaShell } from '@/components/logged-area/LoggedAreaShell';
import { PublicPortalShell } from '@/components/public-portal/PublicPortalShell';
import { useHubSession } from '@/context/HubSessionContext';

/**
 * Home pública (Portal B2B Executivo) ou Área Logada.
 * Rotas /dashboard, admin, checkout e analytics não são alteradas.
 */
export default function ActionHubPage() {
  const { user, hydrated } = useHubSession();

  if (!hydrated) {
    return (
      <div className="flex h-screen items-center justify-center bg-stone-50 text-sm text-stone-500">
        Carregando…
      </div>
    );
  }

  if (user) {
    return <LoggedAreaShell />;
  }

  return <PublicPortalShell />;
}
