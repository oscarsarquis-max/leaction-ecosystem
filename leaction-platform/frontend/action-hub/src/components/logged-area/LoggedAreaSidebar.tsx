'use client';

import Link from 'next/link';
import {
  Activity,
  AppWindow,
  ChevronDown,
  ChevronRight,
  CreditCard,
  ExternalLink,
  HelpCircle,
  Home,
  Package,
  Rocket,
  Settings,
  Settings2,
  Shield,
  Store,
  Zap,
} from 'lucide-react';
import { useState } from 'react';
import { useAdminGate } from '@/lib/require-admin';
import { MOCK_WORKSPACE, resolveInove4usUrl } from '@/components/logged-area/mock-data';

export type LoggedAreaNavId = 'inicio' | 'marketplace';

type LoggedAreaSidebarProps = {
  active: LoggedAreaNavId;
  onNavigate: (id: LoggedAreaNavId) => void;
};

export function LoggedAreaSidebar({ active, onNavigate }: LoggedAreaSidebarProps) {
  const { isAdmin } = useAdminGate();
  const [moreOpen, setMoreOpen] = useState(false);
  const inoveUrl = resolveInove4usUrl();

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-stone-200 bg-white md:w-72">
      <div className="border-b border-stone-200 px-5 py-5">
        <Link href="/" className="flex items-center gap-3" onClick={() => onNavigate('inicio')}>
          <img
            src="/logo.png"
            alt="ActionHub"
            className="h-10 w-10 rounded-xl object-cover shadow-sm ring-1 ring-stone-200"
          />
          <div className="min-w-0">
            <p className="truncate text-lg font-bold leading-none tracking-tight text-stone-900">
              ActionHub
            </p>
            <p className="mt-1 text-[10px] font-semibold uppercase tracking-wider text-stone-500">
              MudaEdu · Contextual
            </p>
          </div>
        </Link>
        <div className="mt-4 rounded-xl border border-stone-200 bg-stone-50 px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-stone-500">
            Workspace
          </p>
          <p className="mt-0.5 truncate text-sm font-semibold text-stone-900">{MOCK_WORKSPACE}</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-2 overflow-y-auto p-4" aria-label="Área logada">
        <button
          type="button"
          onClick={() => onNavigate('inicio')}
          className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-semibold transition ${
            active === 'inicio'
              ? 'bg-stone-100 text-stone-900'
              : 'text-stone-500 hover:bg-stone-50 hover:text-stone-900'
          }`}
        >
          <Home className="size-4 shrink-0" aria-hidden />
          Início
        </button>

        <a
          href={inoveUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 rounded-xl bg-orange-50 px-3 py-2.5 text-sm font-bold text-orange-600 transition hover:bg-orange-100"
        >
          <Zap className="size-4 shrink-0" aria-hidden />
          <span className="flex-1">Inove4us</span>
          <ExternalLink className="size-3.5 shrink-0 opacity-70" aria-hidden />
        </a>

        <button
          type="button"
          onClick={() => onNavigate('marketplace')}
          className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-semibold transition ${
            active === 'marketplace'
              ? 'bg-stone-100 text-stone-900'
              : 'text-stone-500 hover:bg-stone-50 hover:text-stone-900'
          }`}
        >
          <Store className="size-4 shrink-0" aria-hidden />
          Marketplace
        </button>

        {/* Serviços existentes — não remover acesso */}
        <div className="mt-3 border-t border-stone-100 pt-3">
          <button
            type="button"
            onClick={() => setMoreOpen((v) => !v)}
            className="flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-bold uppercase tracking-wider text-stone-500 transition hover:bg-stone-50 hover:text-stone-800"
          >
            <span className="flex-1">Mais serviços</span>
            {moreOpen ? (
              <ChevronDown className="size-3.5" aria-hidden />
            ) : (
              <ChevronRight className="size-3.5" aria-hidden />
            )}
          </button>
          {moreOpen ? (
            <ul className="mt-1 space-y-0.5">
              <li>
                <Link
                  href="/dashboard"
                  className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-stone-600 transition hover:bg-stone-50 hover:text-stone-900"
                >
                  <CreditCard className="size-3.5 shrink-0" aria-hidden />
                  Action-Pay
                </Link>
              </li>
              <li>
                <Link
                  href="/dashboard/crm/tracking"
                  className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-stone-600 transition hover:bg-stone-50 hover:text-stone-900"
                >
                  <Activity className="size-3.5 shrink-0" aria-hidden />
                  Analytics
                </Link>
              </li>
              <li>
                <a
                  href="https://mudaedu.com.br"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-stone-600 transition hover:bg-stone-50 hover:text-stone-900"
                >
                  <Rocket className="size-3.5 shrink-0" aria-hidden />
                  mudaedu
                </a>
              </li>
              <li>
                <a
                  href="https://chamelleon.com.br"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-stone-600 transition hover:bg-stone-50 hover:text-stone-900"
                >
                  <Rocket className="size-3.5 shrink-0" aria-hidden />
                  Chamelleon
                </a>
              </li>
              {isAdmin ? (
                <>
                  <li className="px-3 pt-2 pb-1 text-[10px] font-bold uppercase tracking-wider text-stone-400">
                    Admin
                  </li>
                  <li>
                    <Link
                      href="/dashboard/admin/payments"
                      className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-stone-600 transition hover:bg-stone-50 hover:text-stone-900"
                    >
                      <Shield className="size-3.5 shrink-0" aria-hidden />
                      Pagamentos & Ops
                    </Link>
                  </li>
                  <li>
                    <Link
                      href="/dashboard/admin/apps"
                      className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-stone-600 transition hover:bg-stone-50 hover:text-stone-900"
                    >
                      <AppWindow className="size-3.5 shrink-0" aria-hidden />
                      Aplicações
                    </Link>
                  </li>
                  <li>
                    <Link
                      href="/dashboard/admin/plans"
                      className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-stone-600 transition hover:bg-stone-50 hover:text-stone-900"
                    >
                      <Package className="size-3.5 shrink-0" aria-hidden />
                      Planos
                    </Link>
                  </li>
                  <li>
                    <Link
                      href="/dashboard/marketplace/curadoria"
                      className="flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium text-stone-600 transition hover:bg-stone-50 hover:text-stone-900"
                    >
                      <Settings2 className="size-3.5 shrink-0" aria-hidden />
                      Curadoria
                    </Link>
                  </li>
                </>
              ) : null}
            </ul>
          ) : null}
        </div>
      </nav>

      <div className="mt-auto space-y-1 border-t border-stone-200 p-4">
        <button
          type="button"
          className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm font-medium text-stone-500 transition hover:bg-stone-50 hover:text-stone-800"
          title="Em breve"
        >
          <Settings className="size-4 shrink-0" aria-hidden />
          Configurações
        </button>
        <button
          type="button"
          className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm font-medium text-stone-500 transition hover:bg-stone-50 hover:text-stone-800"
          title="Em breve"
        >
          <HelpCircle className="size-4 shrink-0" aria-hidden />
          Suporte / Ajuda
        </button>
      </div>
    </aside>
  );
}
