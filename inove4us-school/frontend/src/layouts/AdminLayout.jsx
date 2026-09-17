import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { filterNavByZonas, ZONA_LABEL } from '../lib/rbac'
import { useAuth } from '../lib/auth'
import { CrmEvents, trackEvent } from '../lib/tracking'

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
    'whitespace-nowrap rounded-lg px-2 py-1.5 text-xs font-semibold transition lg:px-3 lg:py-2 lg:text-sm',
    isActive
      ? 'bg-school-700 text-white'
      : 'text-muted hover:bg-slate-50 hover:text-ink',
  ].join(' ')
}

export default function AdminLayout({
  escolaNome = 'Instituição',
  gestorNome = 'Gestor',
  zonas = [],
  onSair,
  children,
}) {
  const { user } = useAuth()
  const nav = filterNavByZonas(zonas)
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [senhaOpen, setSenhaOpen] = useState(false)
  const [senhaAtual, setSenhaAtual] = useState('')
  const [senhaNova, setSenhaNova] = useState('')
  const [senhaMsg, setSenhaMsg] = useState('')
  const [senhaBusy, setSenhaBusy] = useState(false)
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
            <div className="min-w-0 max-w-[9.5rem] hidden sm:block lg:max-w-[12rem]">
              <p className="truncate text-sm font-semibold text-ink">{escolaNome}</p>
              {zonaChips.length > 0 ? (
                <div className="mt-0.5 flex flex-col items-start gap-0.5">
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
            className="hidden min-w-0 flex-1 flex-wrap items-center justify-center gap-0.5 lg:gap-1 md:flex"
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
              onClick={() => {
                setSenhaMsg('')
                setSenhaAtual('')
                setSenhaNova('')
                setSenhaOpen(true)
              }}
              className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-ink transition hover:border-slate-300 hover:bg-slate-50"
            >
              Alterar senha
            </button>
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

      {senhaOpen ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-900/40 p-4">
          <form
            className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-5 shadow-lg"
            onSubmit={async (ev) => {
              ev.preventDefault()
              setSenhaMsg('')
              setSenhaBusy(true)
              try {
                const res = await fetch('/api/auth/alterar-senha', {
                  method: 'POST',
                  credentials: 'include',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    senha_atual: senhaAtual,
                    senha_nova: senhaNova,
                  }),
                })
                const body = await res.json().catch(() => ({}))
                if (!res.ok) throw new Error(body.error || 'Não foi possível alterar a senha')
                const dados = {}
                if (typeof body.primeira === 'boolean') dados.primeira = body.primeira
                void trackEvent(CrmEvents.SENHA_ALTERAR, {
                  idUsuario: user?.id ?? null,
                  dados: Object.keys(dados).length ? dados : undefined,
                })
                setSenhaOpen(false)
              } catch (err) {
                setSenhaMsg(err.message || 'Erro ao alterar senha')
              } finally {
                setSenhaBusy(false)
              }
            }}
          >
            <h2 className="text-base font-semibold text-ink">Alterar senha</h2>
            <label className="mt-3 block text-xs font-semibold text-muted">
              Senha atual
              <input
                type="password"
                autoComplete="current-password"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={senhaAtual}
                onChange={(e) => setSenhaAtual(e.target.value)}
                required
              />
            </label>
            <label className="mt-3 block text-xs font-semibold text-muted">
              Nova senha
              <input
                type="password"
                autoComplete="new-password"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                value={senhaNova}
                onChange={(e) => setSenhaNova(e.target.value)}
                minLength={8}
                required
              />
            </label>
            {senhaMsg ? <p className="mt-2 text-sm text-red-700">{senhaMsg}</p> : null}
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg px-3 py-1.5 text-sm text-muted"
                onClick={() => setSenhaOpen(false)}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={senhaBusy}
                className="rounded-lg bg-school-700 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-60"
              >
                {senhaBusy ? 'Salvando…' : 'Salvar'}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      <main className="mx-auto w-full max-w-[90rem] flex-1 overflow-auto p-4 sm:p-6 md:p-8">
        {children ?? <Outlet />}
      </main>
    </div>
  )
}
