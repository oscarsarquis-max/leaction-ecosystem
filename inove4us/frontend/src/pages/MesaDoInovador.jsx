import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { api } from '../lib/api'
import BrandLogo from '../components/BrandLogo'
import MapaRealizacoes from '../components/MapaRealizacoes'
import AgendaExecutiva from '../components/AgendaExecutiva'
import UpgradeCreditsModal from '../components/UpgradeCreditsModal'

/**
 * Página inicial — realizações + agenda. O fluxo de investigação fica em /desafio.
 */
export default function MesaDoInovador() {
  const { user, logout, refresh } = useAuth()
  const [searchParams] = useSearchParams()
  const [refreshKey, setRefreshKey] = useState(0)
  const [showUpgradeModal, setShowUpgradeModal] = useState(false)
  const [focusFromMap, setFocusFromMap] = useState(null)
  const paidReturn = searchParams.get('paid') === '1'
  const notices = Array.isArray(user?.hub_notices) ? user.hub_notices : []

  async function dismissNotice(id) {
    try {
      await api.dismissNotice(id)
      await refresh()
    } catch {
      /* ignore */
    }
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-brand-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <a href="/mesa-do-inovador" className="flex items-center gap-3" aria-label="inove4us — início">
            <BrandLogo
              variant="internal"
              className="h-24 w-auto max-w-[280px] object-contain sm:max-w-[320px]"
            />
          </a>
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
            <p className="hidden text-sm text-bordo-soft sm:block">
              Olá, <span className="font-semibold text-bordo">{user?.nome_clie || 'professor'}</span>
            </p>
            {user?.creditos_ia != null ? (
              <button
                type="button"
                onClick={() => setShowUpgradeModal(true)}
                className="rounded-full border border-brand-200 bg-brand-50 px-3 py-1 text-xs font-semibold text-bordo hover:bg-brand-100"
                title="Fazer upgrade de créditos"
              >
                {Number(user.creditos_ia)} créditos
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => setShowUpgradeModal(true)}
              className="btn-ghost !px-3 !py-1.5 text-xs font-semibold"
            >
              Upgrade
            </button>
            <Link to="/dia-a-dia" className="btn-ghost !px-4 !py-2 text-sm font-semibold">
              Dia a Dia
            </Link>
            <Link to="/desafio" className="btn-primary !px-4 !py-2 text-sm">
              + Desafio
            </Link>
            <button type="button" onClick={logout} className="btn-ghost !px-3 !py-1.5 text-xs">
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="px-4 pb-16 pt-5 sm:px-6">
        <div className="mx-auto mb-6 max-w-6xl">
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-600">
            Espaço do professor
          </p>
          <h1 className="font-display text-3xl font-bold text-bordo-deep sm:text-4xl">
            Sua prática inovadora
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-bordo-soft">
            Acompanhe realizações, agenda e desdobramentos. Para um ciclo rápido de ~50 min na
            agenda, use <strong>Dia a Dia</strong>. Para investigar um problema e montar um plano
            EduScrum completo, use <strong>+ Desafio</strong>.
          </p>
          {paidReturn ? (
            <p className="mt-3 text-sm font-medium text-bordo">
              Pagamento recebido — atualizando seu saldo…
            </p>
          ) : null}
          {notices.length > 0 ? (
            <div className="mt-4 space-y-2">
              {notices.map((n) => (
                <div
                  key={n.id}
                  className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
                >
                  <div>
                    {n.status_label ? (
                      <p className="text-[10px] font-bold uppercase tracking-wider text-amber-700">
                        {n.status_label}
                      </p>
                    ) : null}
                    <p className="mt-0.5 font-medium">{n.message}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void dismissNotice(n.id)}
                    className="shrink-0 text-xs font-semibold text-amber-800 underline-offset-2 hover:underline"
                  >
                    Entendi
                  </button>
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <MapaRealizacoes
          refreshKey={refreshKey}
          onSelectNode={(node) => {
            setFocusFromMap({
              id: node.id,
              data_evento: node.data_evento,
              ts: Date.now(),
            })
            requestAnimationFrame(() => {
              document
                .getElementById('agenda-executiva')
                ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            })
          }}
        />
        <AgendaExecutiva
          refreshKey={refreshKey}
          focusFromMap={focusFromMap}
          onChanged={() => setRefreshKey((n) => n + 1)}
        />
      </main>

      <UpgradeCreditsModal
        open={showUpgradeModal}
        onClose={() => setShowUpgradeModal(false)}
      />
    </div>
  )
}
