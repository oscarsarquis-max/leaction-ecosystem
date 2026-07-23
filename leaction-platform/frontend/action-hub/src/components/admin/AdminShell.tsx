'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  AppWindow,
  ArrowLeft,
  CreditCard,
  Package,
  Shield,
} from 'lucide-react';
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
    <div className="min-h-[calc(100vh-4rem)] bg-stone-100 text-stone-800">
      {/* Faixa de contexto: deixa claro que isto NÃO é a home do Hub */}
      <div className="border-b border-stone-800 bg-stone-900 text-stone-100">
        <div className="mx-auto flex max-w-[1400px] flex-wrap items-center justify-between gap-3 px-4 py-2.5 md:px-6">
          <div className="flex min-w-0 items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-orange-500/20 text-orange-300 ring-1 ring-orange-400/30">
              <Shield className="size-4" aria-hidden />
            </span>
            <div className="min-w-0">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-orange-300/90">
                Subsistema administrativo
              </p>
              <p className="truncate text-sm font-semibold text-white">
                Você saiu da home do Action Hub
              </p>
            </div>
          </div>
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-xl bg-orange-500 px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-orange-400"
          >
            <ArrowLeft className="size-4" aria-hidden />
            Sair do Admin · ir à home
          </Link>
        </div>
      </div>

      <div className="mx-auto flex max-w-[1400px] flex-col gap-4 p-4 md:flex-row md:gap-6 md:p-6">
        <aside className="w-full shrink-0 md:w-64">
          <div className="rounded-2xl border border-stone-300 bg-white shadow-sm">
            <div className="border-b border-stone-100 px-4 py-4">
              <div className="flex items-center gap-2.5">
                <span className="flex size-9 items-center justify-center rounded-xl bg-stone-900 text-orange-300 ring-1 ring-stone-800">
                  <Shield className="size-4" aria-hidden />
                </span>
                <div>
                  <p className="text-sm font-bold text-stone-900">Admin Hub</p>
                  <p className="text-[11px] text-stone-500">Ops · apps · planos</p>
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
                        ? 'bg-stone-900 text-white'
                        : 'text-stone-700 hover:bg-stone-100'
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
                href="/"
                className="flex items-center gap-2 rounded-xl bg-orange-500 px-3 py-2.5 text-xs font-bold text-white transition hover:bg-orange-600"
              >
                <ArrowLeft className="size-3.5" aria-hidden />
                Sair · Action Hub (home)
              </Link>
            </div>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-stone-300 bg-white px-4 py-3 shadow-sm md:px-5">
            <div className="min-w-0">
              <p className="text-[11px] font-bold uppercase tracking-wider text-orange-600">
                Painel administrativo · subsistema
              </p>
              <p className="text-sm font-semibold text-stone-800">
                Pagamentos, aplicações e planos
              </p>
              <p className="mt-0.5 text-xs text-stone-500">
                Ambiente separado da home e dos serviços do usuário.
              </p>
            </div>
            {user ? (
              <div className="rounded-full bg-stone-50 px-3 py-1.5 text-xs font-medium text-stone-600 ring-1 ring-stone-200">
                {user.email}
              </div>
            ) : null}
          </header>
          <main className="rounded-2xl border border-stone-300 bg-white p-4 shadow-sm md:p-6">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
