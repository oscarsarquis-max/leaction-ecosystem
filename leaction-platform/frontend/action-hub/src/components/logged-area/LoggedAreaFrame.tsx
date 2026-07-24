'use client';

import { useMemo, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { useHubSession } from '@/context/HubSessionContext';
import {
  LoggedAreaSidebar,
  type LoggedAreaNavId,
} from '@/components/logged-area/LoggedAreaSidebar';
import { LoggedAreaRightPanel } from '@/components/logged-area/LoggedAreaRightPanel';

type LoggedAreaFrameProps = {
  children: ReactNode;
  /** Destaque no menu principal (Início / Marketplace). Null = nenhum. */
  activeNav?: LoggedAreaNavId | null;
  showRightPanel?: boolean;
};

/**
 * Frame compartilhado da área logada — sidebar completa permanece
 * em Início, admin, CMS etc.
 */
export function LoggedAreaFrame({
  children,
  activeNav = null,
  showRightPanel = false,
}: LoggedAreaFrameProps) {
  const router = useRouter();
  const { user } = useHubSession();

  const userName = useMemo(() => {
    const name = String(user?.name || '').trim();
    if (name) return name;
    const email = String(user?.email || '').trim();
    if (email.includes('@')) return email.split('@')[0];
    return 'LeActioner';
  }, [user?.name, user?.email]);

  function handleNavigate(id: LoggedAreaNavId) {
    if (id === 'marketplace') {
      router.push('/?nav=marketplace');
      return;
    }
    router.push('/');
  }

  return (
    <div className="flex h-screen overflow-hidden bg-stone-50 text-stone-900">
      <LoggedAreaSidebar active={activeNav} onNavigate={handleNavigate} />
      <main className="min-w-0 flex-1 overflow-y-auto bg-stone-50 p-6 md:p-8">
        {children}
      </main>
      {showRightPanel ? (
        <div className="hidden lg:block">
          <LoggedAreaRightPanel userName={userName} userEmail={user?.email} />
        </div>
      ) : null}
    </div>
  );
}
