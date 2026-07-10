import { useState } from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  filterNavItems,
  NAV_ITEMS,
  ROLE_LED,
  ROLE_CONSULTOR,
  ROLE_SYSADMIN,
} from '../config/rbac';
import { GearIcon } from './icons/GearIcon';
import { useAuth } from '../context/AuthContext';
import { buildLeadNavItems, resolveJourneyFlags } from '../utils/journeyState';

function NavItemLink({ item, classNameBuilder }) {
  return (
    <NavLink to={item.to} end={item.end} className={classNameBuilder}>
      <span className="flex items-center gap-2">
        {item.icon === 'gear' && <GearIcon className="h-4 w-4 shrink-0" />}
        {item.label}
      </span>
    </NavLink>
  );
}

function SidebarNav({ items }) {
  const location = useLocation();
  const [openGroups, setOpenGroups] = useState(() => ({
    'Área Operacional': true,
    'Transformação Digital (TD)': true,
  }));

  function toggleGroup(label) {
    setOpenGroups((prev) => ({ ...prev, [label]: !prev[label] }));
  }

  return (
    <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto">
      {items.map((item) => {
        if (item.children?.length) {
          const childActive = item.children.some((child) =>
            location.pathname.startsWith(child.to),
          );
          const isOpen = openGroups[item.label] ?? childActive;
          return (
            <div key={item.label} className="space-y-1">
              <button
                type="button"
                onClick={() => toggleGroup(item.label)}
                className={[
                  'flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors',
                  childActive
                    ? 'bg-chameleon/10 text-chameleon-dark'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-chameleon-dark',
                ].join(' ')}
              >
                <span>{item.label}</span>
                <span className="text-xs text-slate-400">{isOpen ? '▾' : '▸'}</span>
              </button>
              {isOpen && (
                <div className="ml-2 space-y-1 border-l border-slate-200 pl-2">
                  {item.children.map((child) => (
                    <NavItemLink
                      key={child.to}
                      item={child}
                      classNameBuilder={({ isActive }) =>
                        [
                          'block rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                          isActive
                            ? 'bg-chameleon/10 text-chameleon-dark'
                            : 'text-slate-600 hover:bg-slate-50 hover:text-chameleon-dark',
                        ].join(' ')
                      }
                    />
                  ))}
                </div>
              )}
            </div>
          );
        }

        return (
          <NavItemLink
            key={item.to}
            item={item}
            classNameBuilder={({ isActive }) =>
              [
                'block rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-chameleon/10 text-chameleon-dark'
                  : item.highlight
                    ? 'text-sky-700 hover:bg-sky-50'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-chameleon-dark',
              ].join(' ')
            }
          />
        );
      })}
    </nav>
  );
}

function MobileNav({ items }) {
  const flat = items.flatMap((item) =>
    item.children?.length
      ? item.children.map((child) => ({
          ...child,
          label: `${item.label}: ${child.label}`,
        }))
      : [item],
  );

  return (
    <nav
      className="sticky top-[52px] z-10 flex gap-1 overflow-x-auto border-b border-slate-200 bg-white px-2 py-2 lg:hidden"
      aria-label="Navegação principal"
    >
      {flat.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) =>
            [
              'shrink-0 rounded-lg px-3 py-2 text-xs font-semibold touch-manipulation',
              isActive
                ? 'bg-chameleon/15 text-chameleon-dark'
                : 'text-slate-600 active:bg-slate-100',
            ].join(' ')
          }
        >
          <span className="flex items-center gap-1.5">
            {item.icon === 'gear' && <GearIcon className="h-3.5 w-3.5 shrink-0" />}
            {item.label}
          </span>
        </NavLink>
      ))}
    </nav>
  );
}

export default function Layout() {
  const navigate = useNavigate();
  const { userName, roleLabel, tenantName, sector, systemRole, journey, logout } = useAuth();
  const journeyFlags = resolveJourneyFlags(journey);

  const isClientUser = systemRole === ROLE_LED || systemRole === ROLE_CONSULTOR;
  const visibleNav = isClientUser
    ? buildLeadNavItems(journeyFlags, journey)
    : filterNavItems(NAV_ITEMS, systemRole);

  const headerTitle = isClientUser ? 'Meu Diagnóstico' : 'Painel de Maturidade';
  const headerKicker = isClientUser ? 'Resultado e maturidade' : 'Visão executiva';
  const showSectorQualifier = Boolean(sector) && isClientUser;
  const showTenantContext = systemRole !== ROLE_SYSADMIN && Boolean(tenantName);

  function handleLogout() {
    logout();
    navigate('/acesso', { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 flex-col border-r border-slate-200 bg-white lg:flex">
        <div className="border-b border-slate-100 px-5 py-5">
          <div className="flex flex-col items-center">
            <img
              src="/images/camelleonlogo.png"
              alt="Chamelleon"
              className="h-28 w-28 rounded-xl object-cover shadow-sm"
            />
            {showSectorQualifier && (
              <span className="mt-2 text-xs font-semibold uppercase tracking-wider text-emerald-800">
                {sector}
              </span>
            )}
            <div className="mt-3 text-center">
              <p className="text-sm font-bold tracking-wide text-chameleon-dark">Chamelleon</p>
              <p className="text-xs text-slate-500">Maturity Intelligence</p>
            </div>
          </div>
        </div>

        <SidebarNav items={visibleNav} />
      </aside>

      <div className="flex min-h-screen w-full flex-1 flex-col lg:ml-64">
        <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-8 sm:py-4">
            <div className="min-w-0">
              <p className="text-xs font-medium uppercase tracking-wider text-chameleon">
                {headerKicker}
              </p>
              <h1 className="truncate text-base font-semibold text-slate-800 sm:text-lg">
                {headerTitle}
              </h1>
            </div>

            <div className="flex shrink-0 items-center gap-2 sm:gap-3">
              <div className="hidden text-right sm:block">
                <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
                  Sessão ativa
                </p>
                <p className="text-sm font-medium text-slate-800">{userName}</p>
                <p className="text-xs text-slate-500">
                  {showTenantContext ? `${roleLabel} · ${tenantName}` : roleLabel}
                </p>
              </div>
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-chameleon text-sm font-bold text-white">
                {userName
                  .split(' ')
                  .map((n) => n[0])
                  .join('')
                  .slice(0, 2)}
              </div>
              <button
                type="button"
                onClick={handleLogout}
                title="Sair"
                aria-label="Sair da sessão"
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-600 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600"
              >
                <svg
                  className="h-5 w-5"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
              </button>
            </div>
          </div>
        </header>

        <MobileNav items={visibleNav} />

        <main className="flex-1 bg-slate-50 p-4 sm:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
