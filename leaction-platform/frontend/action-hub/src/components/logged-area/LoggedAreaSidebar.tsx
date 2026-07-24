'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  AppWindow,
  CreditCard,
  ExternalLink,
  HelpCircle,
  Home,
  Newspaper,
  Package,
  Rocket,
  Settings,
  Settings2,
  Store,
  Zap,
} from 'lucide-react';
import { useAdminGate } from '@/lib/require-admin';
import { resolveInove4usUrl } from '@/components/logged-area/mock-data';

export type LoggedAreaNavId = 'inicio' | 'marketplace';

type LoggedAreaSidebarProps = {
  /** null = nenhum item principal ativo (ex.: telas admin) */
  active: LoggedAreaNavId | null;
  onNavigate: (id: LoggedAreaNavId) => void;
};

function userServiceClass(active: boolean) {
  return `flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition ${
    active
      ? 'bg-stone-100 text-stone-900'
      : 'text-stone-600 hover:bg-stone-50 hover:text-stone-900'
  }`;
}

function adminLinkClass(active: boolean) {
  return `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition ${
    active
      ? 'bg-orange-500 text-white'
      : 'text-white/90 hover:bg-white/10 hover:text-orange-300'
  }`;
}

function adminIconClass(active: boolean) {
  return `size-3.5 shrink-0 ${active ? 'text-white' : 'text-orange-400'}`;
}

function resolvePanelDxUrl() {
  const fromEnv = (process.env.NEXT_PUBLIC_PANELDX_URL || '').trim().replace(/\/$/, '');
  if (fromEnv) return fromEnv;
  return 'https://paneldx.com.br';
}

export function LoggedAreaSidebar({ active, onNavigate }: LoggedAreaSidebarProps) {
  const pathname = usePathname();
  const { isAdmin } = useAdminGate();
  const inoveUrl = resolveInove4usUrl();
  const paneldxUrl = resolvePanelDxUrl();

  const pathActive = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`);

  const actionPayActive =
    pathActive('/dashboard') &&
    !pathname.startsWith('/dashboard/admin') &&
    !pathname.startsWith('/dashboard/cms') &&
    !pathname.startsWith('/dashboard/crm') &&
    !pathname.startsWith('/dashboard/marketplace');

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
              Contextual Platform
            </p>
          </div>
        </Link>
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

        {/* Apps satélite — bloco superior */}
        <div className="space-y-1 rounded-2xl border border-orange-100 bg-orange-50/60 p-2">
          <p className="px-2 pb-0.5 text-[10px] font-bold uppercase tracking-[0.14em] text-orange-600/80">
            Aplicações
          </p>
          <a
            href={inoveUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 rounded-xl bg-orange-500 px-3 py-2.5 text-sm font-bold text-white transition hover:bg-orange-400"
          >
            <Zap className="size-4 shrink-0" aria-hidden />
            <span className="flex-1">Inove4us</span>
            <ExternalLink className="size-3.5 shrink-0 opacity-80" aria-hidden />
          </a>
          <a
            href={paneldxUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold text-orange-800 transition hover:bg-orange-100"
          >
            <Rocket className="size-4 shrink-0" aria-hidden />
            <span className="flex-1">PanelDX</span>
            <ExternalLink className="size-3.5 shrink-0 opacity-60" aria-hidden />
          </a>
          <a
            href="https://chamelleon.com.br"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-bold text-orange-800 transition hover:bg-orange-100"
          >
            <Rocket className="size-4 shrink-0" aria-hidden />
            <span className="flex-1">Chamelleon</span>
            <ExternalLink className="size-3.5 shrink-0 opacity-60" aria-hidden />
          </a>
        </div>

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

        {/* Hub — serviços do usuário logado */}
        <div className="mt-3 border-t border-stone-100 pt-3">
          <p className="px-3 pb-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-stone-400">
            Mais serviços
          </p>
          <ul className="space-y-0.5">
            {!isAdmin ? (
              <li>
                <Link href="/dashboard" className={userServiceClass(actionPayActive)}>
                  <CreditCard className="size-3.5 shrink-0 text-orange-500" aria-hidden />
                  Action-Pay
                </Link>
              </li>
            ) : null}
            <li>
              <Link
                href="/dashboard/crm/tracking"
                className={userServiceClass(pathActive('/dashboard/crm/tracking'))}
              >
                <Activity className="size-3.5 shrink-0 text-orange-500" aria-hidden />
                Analytics
              </Link>
            </li>
          </ul>
        </div>

        {/* Só Administração no container preto */}
        {isAdmin ? (
          <div className="mt-3 rounded-2xl bg-stone-950 p-3 text-white shadow-sm ring-1 ring-stone-800">
            <p className="px-1 pb-2 text-[10px] font-bold uppercase tracking-[0.14em] text-orange-400">
              Administração
            </p>
            <ul className="space-y-0.5">
              <li>
                <Link
                  href="/dashboard/admin/payments"
                  className={adminLinkClass(pathActive('/dashboard/admin/payments'))}
                >
                  <CreditCard
                    className={adminIconClass(pathActive('/dashboard/admin/payments'))}
                    aria-hidden
                  />
                  Pagamentos & Ops
                </Link>
              </li>
              <li>
                <Link
                  href="/dashboard/admin/apps"
                  className={adminLinkClass(pathActive('/dashboard/admin/apps'))}
                >
                  <AppWindow
                    className={adminIconClass(pathActive('/dashboard/admin/apps'))}
                    aria-hidden
                  />
                  Aplicações
                </Link>
              </li>
              <li>
                <Link
                  href="/dashboard/admin/plans"
                  className={adminLinkClass(pathActive('/dashboard/admin/plans'))}
                >
                  <Package
                    className={adminIconClass(pathActive('/dashboard/admin/plans'))}
                    aria-hidden
                  />
                  Planos
                </Link>
              </li>
              <li>
                <Link
                  href="/dashboard/cms"
                  className={adminLinkClass(pathActive('/dashboard/cms'))}
                >
                  <Newspaper
                    className={adminIconClass(pathActive('/dashboard/cms'))}
                    aria-hidden
                  />
                  Conteúdo (CMS)
                </Link>
              </li>
              <li>
                <Link
                  href="/dashboard/marketplace/curadoria"
                  className={adminLinkClass(pathActive('/dashboard/marketplace/curadoria'))}
                >
                  <Settings2
                    className={adminIconClass(pathActive('/dashboard/marketplace/curadoria'))}
                    aria-hidden
                  />
                  Curadoria
                </Link>
              </li>
            </ul>
          </div>
        ) : null}
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
