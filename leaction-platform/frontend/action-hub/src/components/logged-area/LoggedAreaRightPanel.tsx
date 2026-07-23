'use client';

import Link from 'next/link';
import { Bell, BookOpen, LogOut } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import { MOCK_PLAN, MOCK_QUICK_TIPS } from '@/components/logged-area/mock-data';

type LoggedAreaRightPanelProps = {
  userName: string;
  userEmail?: string | null;
};

export function LoggedAreaRightPanel({ userName, userEmail }: LoggedAreaRightPanelProps) {
  const { logout } = useHubSession();
  const initials = userName
    .split(/\s+|@/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() || '')
    .join('');

  const progressPct = Math.min(100, Math.round((MOCK_PLAN.used / MOCK_PLAN.total) * 100));

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col gap-6 overflow-y-auto border-l border-stone-200 bg-white p-6">
      <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-3">
          <span className="flex size-11 items-center justify-center rounded-full bg-orange-50 text-sm font-bold text-orange-600 ring-1 ring-orange-100">
            {initials || '?'}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-stone-900">{userName}</p>
            {userEmail ? (
              <p className="truncate text-xs text-stone-500">{userEmail}</p>
            ) : null}
          </div>
          <button
            type="button"
            className="inline-flex size-9 items-center justify-center rounded-lg text-stone-500 transition hover:bg-stone-50 hover:text-stone-800"
            aria-label="Notificações"
            title="Notificações (mock)"
          >
            <Bell className="size-4" aria-hidden />
          </button>
        </div>
        <button
          type="button"
          onClick={() => logout()}
          className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-stone-200 px-3 py-2 text-xs font-semibold text-stone-500 transition hover:bg-stone-50 hover:text-stone-800"
        >
          <LogOut className="size-3.5" aria-hidden />
          Sair
        </button>
      </div>

      <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-sm font-bold text-stone-900">Meu Plano</h2>
        <p className="mt-1 text-sm text-stone-500">{MOCK_PLAN.name}</p>
        <div className="mt-4">
          <div className="mb-1.5 flex items-center justify-between text-xs font-medium text-stone-500">
            <span>
              {MOCK_PLAN.used} de {MOCK_PLAN.total} {MOCK_PLAN.unitLabel}
            </span>
            <span className="text-orange-600">{progressPct}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-stone-100">
            <div
              className="h-full rounded-full bg-orange-500 transition-all"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
        <Link
          href="/checkout/inove4us"
          className="mt-4 inline-flex text-xs font-semibold text-orange-600 transition hover:text-orange-700"
        >
          Ver opções de upgrade →
        </Link>
      </div>

      <div>
        <h2 className="mb-3 flex items-center gap-2 text-sm font-bold text-stone-900">
          <BookOpen className="size-4 text-orange-600" aria-hidden />
          Dicas Rápidas
        </h2>
        <ul className="space-y-2">
          {MOCK_QUICK_TIPS.map((tip) => (
            <li key={tip.id}>
              <a
                href={tip.href}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-xl border border-stone-200 bg-white p-3 text-sm font-medium text-stone-900 shadow-sm transition hover:border-orange-200 hover:bg-orange-50"
              >
                {tip.title}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
