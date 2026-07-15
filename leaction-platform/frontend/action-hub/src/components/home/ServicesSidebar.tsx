'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Activity,
  ChevronDown,
  ChevronRight,
  CreditCard,
  ExternalLink,
  Lock,
  Rocket,
  Store,
} from 'lucide-react';
import { useState, type MouseEvent } from 'react';
import { useAuthGate } from '@/lib/require-hub-login';

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

const NAV: NavItem[] = [
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
    href: '/#vitrine',
    icon: Store,
  },
  {
    id: 'transformacao',
    label: 'Transformação Digital',
    icon: Rocket,
    children: [
      {
        label: 'PanelDX',
        description: 'Transformação Digital Educacional',
        href: 'https://paneldx.com.br',
        iconSrc: '/brands/paneldx.jpg',
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

function navActive(pathname: string, href?: string) {
  if (!href || href === '#') return false;
  if (href.startsWith('/#')) return pathname === '/';
  if (href === '/dashboard') return pathname === '/dashboard';
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function ServicesSidebar() {
  const pathname = usePathname();
  const [openTransform, setOpenTransform] = useState(true);
  const { isAuthenticated, hydrated, requireLogin } = useAuthGate();

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

      <nav className="flex-1 space-y-1 overflow-y-auto p-3" aria-label="Serviços ActionHub">
        {NAV.map((item) => {
          const Icon = item.icon;
          const active = navActive(pathname, item.href);
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
                              className="mt-0.5 h-9 w-9 shrink-0 rounded-lg object-cover shadow-sm ring-1 ring-stone-200"
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
            <Link
              key={item.id}
              href={item.href || '#'}
              onClick={(event) => handleAuthNav(event, item.href, item.requiresAuth)}
              title={locked ? 'Faça login para acessar' : item.label}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${
                active
                  ? 'bg-orange-50 text-orange-900'
                  : locked
                    ? 'text-stone-400 hover:bg-stone-50'
                    : 'text-stone-700 hover:bg-orange-50 hover:text-orange-900'
              }`}
            >
              <span
                className={`flex size-8 items-center justify-center rounded-lg ${
                  active
                    ? 'bg-orange-100 text-orange-700'
                    : locked
                      ? 'bg-stone-50 text-stone-400'
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
        })}
      </nav>

      <div className="border-t border-stone-100 p-4">
        <div className="rounded-xl bg-orange-50 px-3 py-2.5 text-xs leading-relaxed text-orange-800">
          Action-Pay, Carrinho e Analytics exigem login. Marketplace (catálogo) é público.
        </div>
      </div>
    </aside>
  );
}
