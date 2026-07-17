'use client';

import { useMemo } from 'react';
import { useHubSession } from '@/context/HubSessionContext';
import { useAuthGate } from '@/lib/require-hub-login';

const DEFAULT_ADMIN_EMAILS = 'admin@actionhub.com.br,sysadmin@inove4us.com.br';

function parseAdminEmails(): string[] {
  const raw =
    process.env.NEXT_PUBLIC_HUB_ADMIN_EMAILS ||
    process.env.NEXT_PUBLIC_HUB_SYSADMIN_EMAIL ||
    DEFAULT_ADMIN_EMAILS;
  return String(raw)
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
}

/**
 * Guardião de rotas administrativas — exige login + e-mail na allowlist
 * (alinhada a HUB_ADMIN_EMAILS do gateway) e JWT na sessão.
 */
export function useAdminGate() {
  const { user, token, hydrated } = useHubSession();
  const { requireLogin } = useAuthGate();

  const adminEmails = useMemo(() => parseAdminEmails(), []);
  const email = String(user?.email || '')
    .trim()
    .toLowerCase();
  const isAdmin = Boolean(email && adminEmails.includes(email));
  const hasToken = Boolean(token && String(token).trim());

  return {
    user,
    token,
    hydrated,
    isAuthenticated: Boolean(user),
    isAdmin,
    hasToken,
    canAccessAdmin: hydrated && Boolean(user) && isAdmin && hasToken,
    adminEmails,
    requireLogin,
  };
}
