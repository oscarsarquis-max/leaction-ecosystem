import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../lib/auth'
import ProgressStepper from '../components/wizard/ProgressStepper'
import StepEduScrum from '../components/wizard/StepEduScrum'

function hasPlanData(planData) {
  if (!planData || typeof planData !== 'object') return false
  return Object.keys(planData).length > 0
}

/**
 * Retomada da execução EduScrum a partir de um evento da agenda (plan_data / kanban_state).
 */
export default function ExecucaoPage() {
  const { idEvento } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [evento, setEvento] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const fromState = location.state?.evento
        const statePlan = location.state?.plan_data
        if (fromState?.id_evento && String(fromState.id_evento) === String(idEvento) && hasPlanData(statePlan || fromState.plan_data)) {
          if (!cancelled) {
            setEvento({
              ...fromState,
              plan_data: statePlan || fromState.plan_data,
              kanban_state: location.state?.kanban_state ?? fromState.kanban_state,
            })
          }
        }
        const data = await api.getAgendaEvento(idEvento)
        if (cancelled) return
        const ev = data.evento
        if (!ev) {
          setError('Evento não encontrado.')
          setEvento(null)
          return
        }
        if (ev.status === 'concluido') {
          setError('Esta aula já foi concluída. Veja o relato no mapa de realizações.')
          setEvento(ev)
          return
        }
        if (!hasPlanData(ev.plan_data)) {
          setError('Este evento ainda não tem plano EduScrum. Inicie um novo Desafio.')
          setEvento(null)
          return
        }
        setEvento(ev)
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Não foi possível carregar a aula.')
          setEvento(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [idEvento, location.state])

  const hydrated = useMemo(() => {
    if (!evento?.plan_data) return null
    const pd = evento.plan_data
    const plano = pd.plano || pd.plano_eduscrum || null
    if (!plano) return null
    const ks = evento.kanban_state
    const tarefas =
      (Array.isArray(ks?.tarefas) && ks.tarefas.length ? ks.tarefas : null) ||
      (Array.isArray(ks) && ks.length ? ks : null) ||
      plano.tarefas_kanban ||
      []
    return {
      plano: { ...plano, tarefas_kanban: tarefas },
      hipotese: pd.hipotese || pd.hipotese_teste || evento.meta_json?.hipotese || '',
      problema: pd.problema || evento.meta_json?.problema || '',
      planoSession: pd.plano_session || evento.plano_session || null,
      initialKanbanState: ks || { tarefas },
      initialEventoId: evento.id_evento,
    }
  }, [evento])

  return (
    <div className="min-h-screen">
      <ProgressStepper currentStep={4} />

      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6 print:hidden">
        <div className="flex min-w-0 items-center gap-3">
          <Link to="/mesa-do-inovador" className="btn-ghost !px-3 !py-1.5 text-xs">
            ← Início
          </Link>
          <p className="truncate text-sm text-bordo-soft">
            Execução · <span className="font-semibold text-bordo">{user?.nome_clie || 'professor'}</span>
          </p>
        </div>
        <button type="button" onClick={logout} className="btn-ghost !px-3 !py-1.5 text-xs">
          Sair
        </button>
      </div>

      <main className="px-4 pb-16 pt-2 sm:px-6">
        {loading ? (
          <p className="py-16 text-center text-sm text-bordo-soft">Carregando aula…</p>
        ) : error && !hydrated ? (
          <div className="mx-auto max-w-lg rounded-2xl border border-brand-200 bg-white p-6 text-center shadow-soft">
            <p className="font-display text-xl font-bold text-bordo-deep">Não foi possível retomar</p>
            <p className="mt-2 text-sm text-bordo-soft">{error}</p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              <Link to="/mesa-do-inovador" className="btn-ghost !px-4 !py-2 text-sm">
                Voltar ao início
              </Link>
              <button
                type="button"
                className="btn-primary !px-4 !py-2 text-sm"
                onClick={() => navigate('/desafio')}
              >
                + Desafio
              </button>
            </div>
          </div>
        ) : hydrated ? (
          <StepEduScrum
            plano={hydrated.plano}
            hipotese={hydrated.hipotese}
            problema={hydrated.problema}
            user={user}
            planoSession={hydrated.planoSession}
            initialEventoId={hydrated.initialEventoId}
            initialKanbanState={hydrated.initialKanbanState}
            resumeMode
            onVoltar={() => navigate('/mesa-do-inovador')}
            onAgendaChanged={() => navigate('/mesa-do-inovador')}
          />
        ) : null}
      </main>
    </div>
  )
}
