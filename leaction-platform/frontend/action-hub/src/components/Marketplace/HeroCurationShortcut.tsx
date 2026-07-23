'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Settings2 } from 'lucide-react';
import { useAdminGate } from '@/lib/require-admin';

/**
 * Atalho discreto para curadoria — visível para admin Hub
 * ou quando a sessão legado (cookie mp_curation_auth) está autenticada.
 */
export function HeroCurationShortcut() {
  const { canAccessAdmin, hydrated } = useAdminGate();
  const [cookieAuthed, setCookieAuthed] = useState(false);

  useEffect(() => {
    if (!hydrated || canAccessAdmin) return;

    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/api/marketplace/curation-auth/session', {
          cache: 'no-store',
          credentials: 'same-origin',
        });
        const data = await res.json().catch(() => ({}));
        if (!cancelled && data?.authenticated === true) {
          setCookieAuthed(true);
        }
      } catch {
        /* silencioso — visitante comum não vê o atalho */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [hydrated, canAccessAdmin]);

  if (!hydrated) return null;
  if (!canAccessAdmin && !cookieAuthed) return null;

  return (
    <Link
      href="/dashboard/marketplace/curadoria"
      className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:border-orange-300 hover:text-orange-700"
    >
      <Settings2 className="size-3.5" aria-hidden />
      Curadoria de Categorias
    </Link>
  );
}
