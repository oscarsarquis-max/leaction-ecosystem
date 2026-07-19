'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { AppWindow, CreditCard, LayoutDashboard, Package, Shield } from 'lucide-react';
import { useHubSession } from '@/context/HubSessionContext';
import type { ReactNode } from 'react';

const ADMIN_NAV = [
  {
    href: '/dashboard/admin/payments',
    label: 'Pagamentos & Ops',
    icon: CreditCard,
  },
  {
    href: '/dashboard/admin/apps',
    label: 'Aplicações Integradas',
    icon: AppWindow,
  },
  {
    href: '/dashboard/admin/plans',
    label: 'Construtor de Planos',
    icon: Package,
  },
] as const;

function navActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function AdminShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { user } = useHubSession();

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-stone-50 text-stone-800">
      <div className="mx-auto flex max-w-[1400px] flex-col gap-4 p-4 md:flex-row md:gap-6 md:p-6">
        <aside className="w-full shrink-0 md:w-64">
          <div className="rounded-2xl border border-stone-200 bg-white shadow-sm">
            <div className="border-b border-stone-100 px-4 py-4">
              <div className="flex items-center gap-2.5">
                <span className="flex size-9 items-center justify-center rounded-xl bg-orange-50 text-orange-700 ring-1 ring-orange-100">
                  <Shield className="size-4" aria-hidden />
                </span>
                <div>
                  <p className="text-sm font-bold text-stone-900">Admin Hub</p>
                  <p className="text-[11px] text-stone-500">Contratos & catálogo</p>
                </div>
              </div>
            </div>
            <nav className="space-y-1 p-2" aria-label="Administração">
              {ADMIN_NAV.map((item) => {
                const Icon = item.icon;
                const active = navActive(pathname, item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
                      active
                        ? 'bg-orange-50 text-orange-900'
                        : 'text-stone-700 hover:bg-orange-50 hover:text-orange-900'
                    }`}
                  >
                    <Icon className="size-4 shrink-0" aria-hidden />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <div className="border-t border-stone-100 p-3">
              <Link
                href={
                  user?.email
                    ? `/dashboard?email=${encodeURIComponent(user.email)}`
                    : '/dashboard'
                }
                className="flex items-center gap-2 rounded-xl px-3 py-2 text-xs font-medium text-stone-500 transition hover:bg-stone-50 hover:text-stone-800"
              >
                <LayoutDashboard className="size-3.5" aria-hidden />
                Área do LeActioner
              </Link>
            </div>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-stone-200 bg-white px-4 py-3 shadow-sm md:px-5">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-stone-400">
                Painel administrativo
              </p>
              <p className="text-sm font-semibold text-stone-800">
                Pagamentos, aplicações e planos
              </p>
            </div>
            {user ? (
              <div className="rounded-full bg-stone-50 px-3 py-1.5 text-xs font-medium text-stone-600 ring-1 ring-stone-200">
                {user.email}
              </div>
            ) : null}
          </header>
          <main className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm md:p-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
