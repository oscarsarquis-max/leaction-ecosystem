import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { filterNavByZonas, ZONA_LABEL } from '../lib/rbac'

/**
 * Shell B2B — header horizontal (sem sidebar).
 * Menu filtrado pelas zonas do gestor (school_gestor_perfis) via rbac.js.
 * Em telas estreitas (< md), links colapsam em menu hambúrguer.
 */

function iniciais(nome) {
  const parts = String(nome || '')
    .replace(/·.*/g, '')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
  if (!parts.length) return 'G'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase()
}

function navLinkClass({ isActive }) {
  return [
    'whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold transition',
    isActive
      ? 'bg-school-700 text-white'
      : 'text-muted hover:bg-slate-50 hover:text-ink',
  ].join(' ')
}

export default function AdminLayout({
  escolaNome = 'Colégio Horizonte Inovador',
  gestorNome = 'Gestor',
  zonas = [],
  onSair,
  children,
}) {
  const nav = filterNavByZonas(zonas)
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const zonaChips = (Array.isArray(zonas) ? zonas : [])
    .map((z) => ZONA_LABEL[z] || z)
    .filter(Boolean)

  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  return (
    <div className="flex min-h-screen flex-col bg-panel text-ink">
      <header className="sticky top-0 z-50 overflow-visible border-b border-slate-200 bg-white/95 backdrop-blur-md">
        <div className="mx-auto flex max-w-[90rem] items-center gap-3 px-4 py-2.5 sm:px-6">
          {/* Esquerda: logo grande sem inflar a altura do header */}
          <div className="relative flex min-w-0 shrink-0 items-center gap-2.5">
            <img
              src="/images/logo-inove4us-school.png"
              alt="inove4us School"
              className="relative z-10 -my-10 h-40 w-auto max-w-[min(340px,48vw)] object-contain object-left sm:-my-12 sm:h-48 sm:max-w-[380px]"
            />
            <div className="min-w-0 hidden sm:block">
              <p className="truncate text-sm font-semibold text-ink">{escolaNome}</p>
              {zonaChips.length > 0 ? (
                <div className="mt-0.5 flex flex-wrap gap-1">
                  {zonaChips.map((label) => (
                    <span
                      key={label}
                      className="inline-flex rounded-md bg-school-50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-school-700"
                    >
                      {label}
                    </span>
                  ))}
                </div>
              ) : null}
            </div>
          </div>

          {/* Centro: nav desktop */}
          <nav
            className="hidden min-w-0 flex-1 items-center justify-center gap-1 md:flex"
            aria-label="Principal"
          >
            {nav.length === 0 ? (
              <p className="text-xs text-muted">Nenhuma zona ativa neste perfil.</p>
            ) : (
              nav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={navLinkClass}
                >
                  {item.label}
                </NavLink>
              ))
            )}
          </nav>

          {/* Direita: avatar + sair (+ hambúrguer no mobile) */}
          <div className="ml-auto flex shrink-0 items-center gap-2">
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-lg border border-slate-200 p-2 text-ink hover:bg-slate-50 md:hidden"
              aria-label={menuOpen ? 'Fechar menu' : 'Abrir menu'}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              {menuOpen ? (
                <span className="block text-lg leading-none" aria-hidden>
                  ×
                </span>
              ) : (
                <span className="flex flex-col gap-1" aria-hidden>
                  <span className="block h-0.5 w-4 rounded bg-ink" />
                  <span className="block h-0.5 w-4 rounded bg-ink" />
                  <span className="block h-0.5 w-4 rounded bg-ink" />
                </span>
              )}
            </button>

            <div
              className="flex h-9 w-9 items-center justify-center rounded-full bg-school-100 text-xs font-bold text-school-700"
              title={gestorNome}
              aria-hidden
            >
              {iniciais(gestorNome)}
            </div>
            <div className="hidden min-w-0 max-w-[10rem] lg:block">
              <p className="truncate text-xs font-semibold text-ink">{gestorNome}</p>
            </div>
            <button
              type="button"
              onClick={onSair}
              className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-ink transition hover:border-slate-300 hover:bg-slate-50"
            >
              Sair
            </button>
          </div>
        </div>

        {/* Menu mobile */}
        {menuOpen ? (
          <nav
            className="border-t border-slate-100 px-3 py-2 md:hidden"
            aria-label="Menu principal"
          >
            <p className="mb-2 truncate px-2 text-xs font-semibold text-ink sm:hidden">
              {escolaNome}
            </p>
            {nav.length === 0 ? (
              <p className="px-2 py-2 text-sm text-muted">
                Nenhuma zona ativa neste perfil.
              </p>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {nav.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      end={item.end}
                      className={({ isActive }) =>
                        [
                          'block rounded-lg px-3 py-2.5 text-sm font-semibold',
                          isActive
                            ? 'bg-school-700 text-white'
                            : 'text-muted hover:bg-slate-50 hover:text-ink',
                        ].join(' ')
                      }
                    >
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            )}
          </nav>
        ) : null}
      </header>

      <main className="mx-auto w-full max-w-[90rem] flex-1 overflow-auto p-4 sm:p-6 md:p-8">
        {children ?? <Outlet />}
      </main>
    </div>
  )
}
