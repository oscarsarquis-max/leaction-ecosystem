import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import BrandLogo from '../components/BrandLogo'
import { useAuth } from '../lib/auth'
import {
  excluirAula,
  isSchemaPendingError,
  listarAulas,
} from '../services/dailyService'

const STATUS_LABEL = {
  draft: 'Rascunho',
  planejado: 'Planejado',
  realizado: 'Realizado',
}

const STATUS_TONE = {
  draft: 'bg-stone-100 text-stone-700',
  planejado: 'bg-emerald-50 text-emerald-800',
  realizado: 'bg-brand-50 text-bordo',
}

function formatDate(iso) {
  if (!iso) return '—'
  const d = String(iso).slice(0, 10)
  const [y, m, day] = d.split('-')
  if (!y || !m || !day) return d
  return `${day}/${m}/${y}`
}

/**
 * Dashboard do vetor Dia a Dia — listagem de aulas simples.
 */
export default function DailyDashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [aulas, setAulas] = useState([])
  const [loading, setLoading] = useState(true)
  const [schemaPending, setSchemaPending] = useState(false)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    setSchemaPending(false)
    try {
      const data = await listarAulas({ page: 1, pageSize: 50 })
      setAulas(Array.isArray(data?.aulas) ? data.aulas : [])
    } catch (err) {
      if (isSchemaPendingError(err)) {
        setSchemaPending(true)
        setAulas([])
      } else {
        setError(err?.message || 'Não foi possível carregar as aulas.')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function handleDelete(aula) {
    if (!aula?.id) return
    if (aula.status === 'realizado') return
    const ok = window.confirm(`Excluir a aula “${aula.tema_aula || 'sem tema'}”?`)
    if (!ok) return
    setBusyId(aula.id)
    try {
      await excluirAula(aula.id)
      setAulas((prev) => prev.filter((a) => a.id !== aula.id))
    } catch (err) {
      if (isSchemaPendingError(err)) setSchemaPending(true)
      else window.alert(err?.message || 'Falha ao excluir')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-brand-200/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link to="/mesa-do-inovador" className="flex items-center gap-3" aria-label="Voltar à mesa">
            <BrandLogo
              variant="internal"
              className="h-20 w-auto max-w-[240px] object-contain sm:max-w-[280px]"
            />
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            <Link
              to="/mesa-do-inovador"
              className="btn-ghost min-h-11 !px-4 !py-2.5 text-sm"
            >
              ← Mesa
            </Link>
            {!schemaPending ? (
              <Link
                to="/dia-a-dia/nova"
                className="btn-primary min-h-11 !px-4 !py-2.5 text-sm"
              >
                Planejar Nova Aula
              </Link>
            ) : null}
            <button
              type="button"
              onClick={logout}
              className="btn-ghost min-h-11 !px-4 !py-2.5 text-sm"
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 pb-16 pt-6 sm:px-6">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-600">
          Vetor Dia a Dia
        </p>
        <h1 className="font-display text-3xl font-bold text-bordo-deep sm:text-4xl">
          Sprint de uma aula
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-bordo-soft">
          Ciclo rápido de ~50 min na agenda: alinhamento → entrega do dia → atividade em campo →
          retro. Aparece na Mesa junto com os demais compromissos.
        </p>
        {user?.nome_clie ? (
          <p className="mt-1 text-xs text-bordo-soft">
            Professor(a): <span className="font-semibold text-bordo">{user.nome_clie}</span>
          </p>
        ) : null}

        {schemaPending ? (
          <div className="mt-10 rounded-2xl border border-brand-200 bg-white/90 px-6 py-12 text-center shadow-soft">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
              Em atualização
            </p>
            <h2 className="mt-2 font-display text-2xl font-bold text-bordo-deep">
              Em breve na sua mesa
            </h2>
            <p className="mx-auto mt-3 max-w-lg text-sm leading-relaxed text-bordo-soft">
              O planejamento diário rápido estará disponível em breve! Estamos em fase final de
              atualização da plataforma.
            </p>
            <Link
              to="/mesa-do-inovador"
              className="btn-primary mt-6 inline-flex min-h-11 items-center !px-5 !py-3 text-sm"
            >
              Voltar à Mesa do Inovador
            </Link>
          </div>
        ) : null}

        {!schemaPending && loading ? (
          <p className="mt-10 text-sm text-bordo-soft">Carregando suas aulas…</p>
        ) : null}

        {!schemaPending && error ? (
          <div className="mt-8 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
            {error}
            <button
              type="button"
              onClick={() => void load()}
              className="ml-3 font-semibold underline-offset-2 hover:underline"
            >
              Tentar de novo
            </button>
          </div>
        ) : null}

        {!schemaPending && !loading && !error && aulas.length === 0 ? (
          <div className="mt-10 rounded-2xl border border-dashed border-brand-300 bg-white/70 px-6 py-12 text-center">
            <p className="font-display text-xl font-bold text-bordo-deep">Nenhuma aula ainda</p>
            <p className="mt-2 text-sm text-bordo-soft">
              Planeje a primeira aula do dia em poucos minutos.
            </p>
            <button
              type="button"
              onClick={() => navigate('/dia-a-dia/nova')}
              className="btn-primary mt-6 min-h-11 !px-5 !py-3 text-sm"
            >
              Planejar Nova Aula
            </button>
          </div>
        ) : null}

        {!schemaPending && aulas.length > 0 ? (
          <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {aulas.map((aula) => {
              const status = String(aula.status || 'draft')
              return (
                <article
                  key={aula.id}
                  className="flex flex-col rounded-2xl border border-brand-200 bg-white/90 p-5 shadow-soft sm:p-6"
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-bold uppercase tracking-wide text-bordo-soft">
                      {formatDate(aula.data_planejada)}
                    </p>
                    <span
                      className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${
                        STATUS_TONE[status] || STATUS_TONE.draft
                      }`}
                    >
                      {STATUS_LABEL[status] || status}
                    </span>
                  </div>
                  <h2 className="mt-2 font-display text-lg font-bold leading-snug text-bordo-deep sm:text-xl">
                    {aula.tema_aula || 'Sem tema'}
                  </h2>
                  {aula.turma_nome ? (
                    <p className="mt-1 text-sm text-bordo-soft">Turma: {aula.turma_nome}</p>
                  ) : null}
                  <div className="mt-auto flex flex-wrap gap-2 pt-5">
                    <Link
                      to={`/dia-a-dia/${aula.id}`}
                      className="btn-primary inline-flex min-h-11 min-w-[5.5rem] items-center justify-center !px-4 !py-2.5 text-sm"
                    >
                      Abrir
                    </Link>
                    {status !== 'realizado' ? (
                      <button
                        type="button"
                        disabled={busyId === aula.id}
                        onClick={() => void handleDelete(aula)}
                        className="btn-ghost inline-flex min-h-11 min-w-[5.5rem] items-center justify-center !px-4 !py-2.5 text-sm"
                      >
                        Excluir
                      </button>
                    ) : null}
                  </div>
                </article>
              )
            })}
          </div>
        ) : null}
      </main>
    </div>
  )
}
