'use client';

import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import {
  Activity,
  AppWindow,
  ChevronDown,
  ChevronRight,
  CreditCard,
  ExternalLink,
  Lock,
  Package,
  Rocket,
  Settings2,
  Shield,
  Store,
} from 'lucide-react';
import { Suspense, useState, type MouseEvent } from 'react';
import { useAuthGate } from '@/lib/require-hub-login';
import { useAdminGate } from '@/lib/require-admin';

type NavChild = {
  label: string;
  description: string;
  href: string;
  iconSrc: string;
  requiresAuth?: boolean;
};

type NavItem = {
  id: string;
  label: string;
  href?: string;
  icon: typeof Store;
  requiresAuth?: boolean;
  children?: NavChild[];
};

const SERVICES_NAV: NavItem[] = [
  {
    id: 'action-pay',
    label: 'Action-Pay',
    href: '/dashboard',
    icon: CreditCard,
    requiresAuth: true,
  },
  {
    id: 'marketplace',
    label: 'Marketplace B2B',
    href: '/dashboard?view=cart',
    icon: Store,
    requiresAuth: true,
  },
  {
    id: 'transformacao',
    label: 'Transformação Digital',
    icon: Rocket,
    children: [
      {
        label: 'mudaedu',
        description: 'Transformação Digital Educacional',
        href: 'https://mudaedu.com.br',
        iconSrc: '/brands/mudaedu.png',
      },
      {
        label: 'inove4us',
        description: 'Inovação Educacional',
        href: 'https://inove4us.com.br',
        iconSrc: '/brands/inove4us.png',
      },
      {
        label: 'Chamelleon',
        description: 'Transformação Digital Setorial',
        href: 'https://chamelleon.com.br',
        iconSrc: '/brands/chamelleon.png',
      },
    ],
  },
  {
    id: 'analytics',
    label: 'Action-Sponge Analytics',
    href: '/dashboard/crm/tracking',
    icon: Activity,
    requiresAuth: true,
  },
];

const ADMIN_NAV: NavItem[] = [
  {
    id: 'admin-payments',
    label: 'Pagamentos & Ops',
    href: '/dashboard/admin/payments',
    icon: CreditCard,
    requiresAuth: true,
  },
  {
    id: 'admin-apps',
    label: 'Aplicações Integradas',
    href: '/dashboard/admin/apps',
    icon: AppWindow,
    requiresAuth: true,
  },
  {
    id: 'admin-plans',
    label: 'Construtor de Planos',
    href: '/dashboard/admin/plans',
    icon: Package,
    requiresAuth: true,
  },
  {
    id: 'admin-curadoria',
    label: 'Curadoria Marketplace',
    href: '/dashboard/marketplace/curadoria',
    icon: Settings2,
    requiresAuth: true,
  },
];

function navActive(pathname: string, href: string | undefined, view: string | null) {
  if (!href || href === '#') return false;
  if (href.startsWith('/#')) return pathname === '/';
  if (href.includes('view=cart')) {
    return pathname === '/dashboard' && view === 'cart';
  }
  if (href === '/dashboard') {
    return pathname === '/dashboard' && view !== 'cart';
  }
  return pathname === href || pathname.startsWith(`${href}/`);
}

function NavLink({
  item,
  pathname,
  view,
  locked,
  onAuthNav,
  tone = 'default',
}: {
  item: NavItem;
  pathname: string;
  view: string | null;
  locked: boolean;
  onAuthNav: (event: MouseEvent, href: string | undefined, requiresAuth?: boolean) => void;
  tone?: 'default' | 'admin';
}) {
  const Icon = item.icon;
  const active = navActive(pathname, item.href, view);
  const adminTone = tone === 'admin';

  return (
    <Link
      href={item.href || '#'}
      onClick={(event) => onAuthNav(event, item.href, item.requiresAuth)}
      title={locked ? 'Faça login para acessar' : item.label}
      className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
        active
          ? adminTone
            ? 'bg-stone-800 text-white'
            : 'bg-orange-50 text-orange-900'
          : locked
            ? 'text-stone-400 hover:bg-stone-50'
            : adminTone
              ? 'text-stone-700 hover:bg-stone-100'
              : 'text-stone-700 hover:bg-orange-50 hover:text-orange-900'
      }`}
    >
      <span
        className={`flex size-8 items-center justify-center rounded-lg ${
          active
            ? adminTone
              ? 'bg-stone-700 text-orange-300'
              : 'bg-orange-100 text-orange-700'
            : locked
              ? 'bg-stone-50 text-stone-400'
              : adminTone
                ? 'bg-stone-100 text-stone-700'
                : 'bg-stone-50 text-orange-800'
        }`}
      >
        <Icon className="size-4" aria-hidden />
      </span>
      <span className="flex-1">{item.label}</span>
      {item.id === 'action-pay' ? (
        <span className="rounded-full bg-orange-50 px-1.5 py-0.5 text-[10px] font-semibold text-orange-700">
          Pagamentos
        </span>
      ) : null}
      {locked ? <Lock className="size-3.5 shrink-0 text-stone-400" aria-hidden /> : null}
    </Link>
  );
}

function ServicesSidebarInner() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const view = searchParams.get('view');
  const [openTransform, setOpenTransform] = useState(true);
  const { isAuthenticated, hydrated, requireLogin } = useAuthGate();
  const { isAdmin } = useAdminGate();

  function handleAuthNav(
    event: MouseEvent,
    href: string | undefined,
    requiresAuth?: boolean
  ) {
    if (!requiresAuth || !href) return;
    if (!hydrated) {
      event.preventDefault();
      return;
    }
    if (!isAuthenticated) {
      event.preventDefault();
      requireLogin(href, 'Faça login para acessar este serviço.');
    }
  }

  return (
    <aside className="flex h-full flex-col rounded-2xl border border-stone-200 bg-white shadow-sm">
      <div className="border-b border-stone-100 px-5 py-5">
        <Link href="/" className="group flex items-center gap-3">
          <img
            src="/logo.png"
            alt="ActionHub"
            className="h-11 w-11 rounded-xl object-cover shadow-sm ring-1 ring-stone-200"
          />
          <div>
            <p className="text-2xl font-bold leading-none tracking-tight text-orange-950">
              ActionHub
            </p>
            <p className="mt-1 text-[11px] font-medium uppercase tracking-wider text-stone-400">
              Contextual Platform
            </p>
          </div>
        </Link>
      </div>

      <nav className="flex-1 space-y-4 overflow-y-auto p-3" aria-label="Serviços ActionHub">
        <div className="space-y-1">
          <p className="px-3 pb-1 text-[10px] font-bold uppercase tracking-[0.14em] text-stone-400">
            Serviços
          </p>
          {SERVICES_NAV.map((item) => {
            const Icon = item.icon;
            const hasChildren = Boolean(item.children?.length);
            const locked = Boolean(item.requiresAuth) && hydrated && !isAuthenticated;

            if (hasChildren) {
              return (
                <div key={item.id} className="space-y-1">
                  <button
                    type="button"
                    onClick={() => setOpenTransform((v) => !v)}
                    className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-stone-700 transition hover:bg-orange-50 hover:text-orange-900"
                  >
                    <span className="flex size-8 items-center justify-center rounded-lg bg-stone-50 text-orange-800">
                      <Icon className="size-4" aria-hidden />
                    </span>
                    <span className="flex-1">{item.label}</span>
                    {openTransform ? (
                      <ChevronDown className="size-4 text-stone-400" aria-hidden />
                    ) : (
                      <ChevronRight className="size-4 text-stone-400" aria-hidden />
                    )}
                  </button>
                  {openTransform ? (
                    <ul className="ml-2 space-y-1.5 border-l border-stone-100 pl-2">
                      {item.children!.map((child) => {
                        const external = /^https?:\/\//i.test(child.href);
                        return (
                          <li key={child.label}>
                            <Link
                              href={child.href}
                              {...(external
                                ? { target: '_blank', rel: 'noopener noreferrer' }
                                : {})}
                              className="group flex items-start gap-2.5 rounded-xl px-2.5 py-2.5 transition hover:bg-orange-50"
                            >
                              <img
                                src={child.iconSrc}
                                alt=""
                                className="mt-0.5 h-9 w-9 shrink-0 rounded-lg object-cover shadow-sm ring-1 ring-orange-200/80"
                              />
                              <span className="min-w-0 flex-1">
                                <span className="flex items-center gap-1 text-sm font-semibold text-stone-800 group-hover:text-orange-900">
                                  {child.label}
                                  {external ? (
                                    <ExternalLink
                                      className="size-3 shrink-0 text-stone-400 opacity-0 transition group-hover:opacity-100"
                                      aria-hidden
                                    />
                                  ) : null}
                                </span>
                                <span className="mt-0.5 block text-[11px] leading-snug text-stone-500">
                                  {child.description}
                                </span>
                              </span>
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  ) : null}
                </div>
              );
            }

            return (
              <NavLink
                key={item.id}
                item={item}
                pathname={pathname}
                view={view}
                locked={locked}
                onAuthNav={handleAuthNav}
              />
            );
          })}
        </div>

        {isAdmin ? (
          <div className="rounded-2xl border border-stone-800/10 bg-stone-50/80 p-2">
            <div className="mb-1 flex items-center gap-2 px-2 py-1.5">
              <span className="flex size-7 items-center justify-center rounded-lg bg-stone-900 text-orange-300">
                <Shield className="size-3.5" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-stone-800">
                  Subsistema Admin
                </p>
                <p className="text-[10px] leading-snug text-stone-500">
                  Operação do Hub — separado dos serviços
                </p>
              </div>
              <span className="rounded-full bg-stone-900 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-orange-200">
                Admin
              </span>
            </div>
            <div className="space-y-0.5" aria-label="Subsistema administrativo">
              {ADMIN_NAV.map((item) => (
                <NavLink
                  key={item.id}
                  item={item}
                  pathname={pathname}
                  view={view}
                  locked={Boolean(item.requiresAuth) && hydrated && !isAuthenticated}
                  onAuthNav={handleAuthNav}
                  tone="admin"
                />
              ))}
            </div>
          </div>
        ) : null}
      </nav>

      <div className="border-t border-stone-100 p-4">
        <div className="rounded-xl bg-orange-50 px-3 py-2.5 text-xs leading-relaxed text-orange-800">
          Serviços (Action-Pay, Marketplace, Analytics) são o Hub do usuário. O bloco Admin
          só aparece para administradores e abre um painel separado.
        </div>
      </div>
    </aside>
  );
}

export function ServicesSidebar() {
  return (
    <Suspense
      fallback={
        <aside className="flex h-full flex-col rounded-2xl border border-stone-200 bg-white shadow-sm" />
      }
    >
      <ServicesSidebarInner />
    </Suspense>
  );
}
