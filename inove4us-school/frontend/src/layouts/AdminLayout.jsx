import { NavLink, Outlet } from 'react-router-dom'

const NAV = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/equipe', label: 'Minha Equipe' },
  { to: '/editor-pedagogico', label: 'Editor Pedagógico' },
]

/**
 * Shell B2B — sidebar + header.
 * Escola e gestor vêm mockados até a auth Flask.
 */
export default function AdminLayout({
  escolaNome = 'Colégio Horizonte Inovador',
  gestorNome = 'Ana Coordenadora',
  onSair,
}) {
  return (
    <div className="flex min-h-screen bg-panel text-ink">
      <aside className="flex w-80 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-3 pb-1 pt-0">
          <img
            src="/images/logo-inove4us-school.png"
            alt="inove4us School"
            className="-mb-3 -mt-4 h-56 w-auto max-w-full object-contain object-top"
          />
        </div>

        <nav className="flex flex-1 flex-col gap-1 p-3 pt-2" aria-label="Principal">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                [
                  'rounded-lg px-3 py-2.5 text-sm font-medium transition',
                  isActive
                    ? 'bg-school-50 text-school-700'
                    : 'text-muted hover:bg-slate-50 hover:text-ink',
                ].join(' ')
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-200 px-4 py-3 text-xs text-muted">
          B2B · gestores institucionais
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between gap-4 border-b border-slate-200 bg-white px-6">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-ink">{escolaNome}</p>
            <p className="truncate text-xs text-muted">{gestorNome}</p>
          </div>
          <button
            type="button"
            onClick={onSair}
            className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-ink transition hover:border-slate-300 hover:bg-slate-50"
          >
            Sair
          </button>
        </header>

        <main className="flex-1 overflow-auto p-6 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
