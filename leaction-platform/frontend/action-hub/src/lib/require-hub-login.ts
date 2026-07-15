'use client';

import { useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useHubSession } from '@/context/HubSessionContext';

export const REQUIRE_LOGIN_EVENT = 'actionhub:require-login';

type RequireLoginDetail = { next?: string; reason?: string };

/** Dispara foco no formulário de login (home Action Center). */
export function emitRequireLogin(detail?: RequireLoginDetail) {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(REQUIRE_LOGIN_EVENT, { detail: detail || {} }));
  const el = document.getElementById('actionhub-login');
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

/**
 * Gate de autenticação ActionHub — Action-Pay, Carrinho e Analytics
 * só avançam com sessão.
 */
export function useAuthGate() {
  const { user, hydrated } = useHubSession();
  const router = useRouter();

  const requireLogin = useCallback(
    (nextPath?: string, reason?: string): boolean => {
      if (user) return true;

      emitRequireLogin({ next: nextPath, reason });

      if (typeof window !== 'undefined' && window.location.pathname !== '/') {
        const qs = new URLSearchParams();
        if (nextPath) qs.set('next', nextPath);
        if (reason) qs.set('login_reason', reason);
        const suffix = qs.toString() ? `?${qs.toString()}` : '';
        router.push(`/${suffix}#actionhub-login`);
      }
      return false;
    },
    [user, router]
  );

  return {
    user,
    hydrated,
    isAuthenticated: Boolean(user),
    requireLogin,
  };
}
