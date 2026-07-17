import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import BrandLogo from '../BrandLogo'
import RelatoAulaModal from '../RelatoAulaModal'
import { api } from '../../lib/api'
import { debounce } from '../../lib/debounce'
import KanbanMoveModal from './KanbanMoveModal'

const COLUNAS = [
  { id: 'para_fazer', label: 'Para Fazer', tone: 'border-brand-200 bg-brand-50/60' },
  { id: 'fazendo', label: 'Fazendo', tone: 'border-amber-200 bg-amber-50/50' },
  { id: 'pronto', label: 'Pronto', tone: 'border-emerald-200 bg-emerald-50/50' },
]

function formatMmSs(totalSeconds) {
  const m = Math.floor(totalSeconds / 60)
  const s = totalSeconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function colunaLabel(id) {
  return COLUNAS.find((c) => c.id === id)?.label || id
}

function pad2(n) {
  return n < 10 ? `0${n}` : String(n)
}

function hojeISO() {
  const d = new Date()
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function diaEvento(iso) {
  return String(iso || '').slice(0, 10)
}

function formatarDataBR(iso) {
  const p = String(iso || '').slice(0, 10).split('-')
  if (p.length !== 3) return iso || '—'
  return `${p[2]}/${p[1]}/${p[0]}`
}

const STATUS_LABEL = {
  planejado: 'Planejada',
  em_execucao: 'Em execução',
  concluido: 'Concluída',
}

function tasksFromKanbanState(kanbanState, fallback) {
  if (Array.isArray(kanbanState?.tarefas) && kanbanState.tarefas.length) {
    return kanbanState.tarefas
  }
  if (Array.isArray(kanbanState) && kanbanState.length) return kanbanState
  return fallback || []
}

function buildPlanData({ plano, hipotese, problema, planoSession }) {
  return {
    problema: problema || '',
    hipotese: hipotese || '',
    plano_session: planoSession || null,
    plano: plano || null,
  }
}

export default function StepEduScrum({
  plano,
  hipotese,
  problema,
  user,
  planoSession,
  onVoltar,
  onAgendaChanged,
  initialEventoId = null,
  initialKanbanState = null,
  resumeMode = false,
}) {
  const timebox = plano?.timebox || []
  const totalSeconds = useMemo(
    () => timebox.reduce((acc, t) => acc + (Number(t.minutos) || 0) * 60, 0),
    [timebox],
  )

  const [tasks, setTasks] = useState(() =>
    tasksFromKanbanState(initialKanbanState, plano?.tarefas_kanban || []),
  )
  const [running, setRunning] = useState(false)
  const [mode, setMode] = useState('regressivo')
  const [elapsed, setElapsed] = useState(0)
  const [draggingId, setDraggingId] = useState(null)
  const [dropTarget, setDropTarget] = useState(null)
  const [pendingMove, setPendingMove] = useState(null)

  const [aulas, setAulas] = useState([])
  const [aulaAtivaId, setAulaAtivaId] = useState(initialEventoId || null)
  const [showRegistro, setShowRegistro] = useState(false)
  const [slotsRegistro, setSlotsRegistro] = useState(() => [
    {
      key: `s-${Date.now()}`,
      data: hojeISO(),
      turma: '',
      turno: 'manha',
      modo_execucao: 'reinicio',
    },
  ])
  const [registroBusy, setRegistroBusy] = useState(false)
  const [registroErro, setRegistroErro] = useState('')

  const TURNO_OPTS = [
    { id: 'manha', label: 'Manhã' },
    { id: 'tarde', label: 'Tarde' },
    { id: 'noite', label: 'Noite' },
  ]
  const MODO_OPTS = [
    {
      id: 'continuidade',
      label: 'Prosseguimento',
      hint: 'Mesma turma / mesmo problema — retoma o Kanban de onde parou',
    },
    {
      id: 'reinicio',
      label: 'Começar do início',
      hint: 'Outra turma (ou reset) — mesmo problema, Kanban zerado',
    },
  ]

  function updateSlot(key, patch) {
    setSlotsRegistro((prev) => prev.map((s) => (s.key === key ? { ...s, ...patch } : s)))
  }

  function addSlot() {
    setSlotsRegistro((prev) => [
      ...prev,
      {
        key: `s-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        data: hojeISO(),
        turma: prev[prev.length - 1]?.turma || '',
        turno: 'tarde',
        modo_execucao: 'reinicio',
      },
    ])
  }

  function removeSlot(key) {
    setSlotsRegistro((prev) => (prev.length <= 1 ? prev : prev.filter((s) => s.key !== key)))
  }
  const [acaoErro, setAcaoErro] = useState('')
  const [showRelato, setShowRelato] = useState(false)
  const [relatoBusy, setRelatoBusy] = useState(false)
  const [saveStatus, setSaveStatus] = useState('idle') // idle | saving | saved | error
  const [novaTarefaTitulo, setNovaTarefaTitulo] = useState('')

  const eventoIdRef = useRef(null)
  eventoIdRef.current = aulaAtivaId || initialEventoId

  const planMetaRef = useRef({ plano, hipotese, problema, planoSession })
  planMetaRef.current = { plano, hipotese, problema, planoSession }

  const loadAulas = useCallback(async () => {
    try {
      let lista = []
      if (planoSession) {
        const data = await api.listAgendaEventos('', planoSession)
        lista = (data.eventos || []).filter((e) => e.tipo === 'aula_eduscrum')
      }
      if (initialEventoId && !lista.some((a) => a.id_evento === initialEventoId)) {
        const one = await api.getAgendaEvento(initialEventoId)
        if (one?.evento) lista = [one.evento, ...lista]
      }
      setAulas(lista)
      setAulaAtivaId((prev) => {
        if (initialEventoId && lista.some((a) => a.id_evento === initialEventoId)) {
          return initialEventoId
        }
        if (prev && lista.some((a) => a.id_evento === prev)) return prev
        const prefer =
          lista.find((a) => a.status === 'em_execucao') ||
          lista.find((a) => a.status === 'planejado' && diaEvento(a.data_evento) === hojeISO()) ||
          lista.find((a) => a.status === 'planejado') ||
          lista[0]
        return prefer?.id_evento ?? null
      })
    } catch {
      setAulas([])
    }
  }, [planoSession, initialEventoId])

  useEffect(() => {
    setTasks(tasksFromKanbanState(initialKanbanState, plano?.tarefas_kanban || []))
    setElapsed(0)
    setRunning(false)
    setPendingMove(null)
    setShowRegistro(false)
    setAcaoErro('')
    if (initialEventoId) setAulaAtivaId(initialEventoId)
  }, [plano, initialKanbanState, initialEventoId])

  useEffect(() => {
    loadAulas()
  }, [loadAulas])

  /**
   * Auto-save do quadro — PUT /api/agenda-eventos/:id/estado
   * @param {{ tarefas: any[] }} newState
   * @param {object|null} newPlanData — se o plano estrutural mudou (add/edit/delete)
   */
  const saveBoardState = useCallback(async (newState, newPlanData = null) => {
    const id = eventoIdRef.current
    if (!id) return null
    setSaveStatus('saving')
    try {
      const payload = { kanban_state: newState }
      if (newPlanData != null) payload.plan_data = newPlanData
      const data = await api.updateAgendaEstado(id, payload)
      setSaveStatus('saved')
      return data
    } catch (err) {
      console.warn('Falha ao auto-salvar kanban:', err)
      setSaveStatus('error')
      return null
    }
  }, [])

  const saveBoardStateDebounced = useMemo(
    () =>
      debounce((newState, newPlanData = null) => {
        saveBoardState(newState, newPlanData)
      }, 700),
    [saveBoardState],
  )

  useEffect(() => () => saveBoardStateDebounced.cancel(), [saveBoardStateDebounced])

  function queueBoardSave(nextTasks, { syncPlan = false } = {}) {
    const kanbanState = { tarefas: nextTasks }
    if (!eventoIdRef.current) return
    if (syncPlan) {
      const meta = planMetaRef.current
      const newPlanData = buildPlanData({
        ...meta,
        plano: { ...(meta.plano || {}), tarefas_kanban: nextTasks },
      })
      saveBoardStateDebounced(kanbanState, newPlanData)
    } else {
      saveBoardStateDebounced(kanbanState)
    }
  }

  useEffect(() => {
    if (!running || totalSeconds <= 0) return undefined
    const id = setInterval(() => {
      setElapsed((prev) => {
        if (mode === 'regressivo' && prev >= totalSeconds) {
          setRunning(false)
          return totalSeconds
        }
        return prev + 1
      })
    }, 1000)
    return () => clearInterval(id)
  }, [running, mode, totalSeconds])

  const displaySeconds =
    mode === 'regressivo'
      ? Math.max(totalSeconds - elapsed, 0)
      : Math.min(elapsed, totalSeconds)

  const phase = useMemo(() => {
    let cursor = 0
    const consumed = mode === 'regressivo' ? totalSeconds - displaySeconds : displaySeconds
    for (const t of timebox) {
      const secs = (Number(t.minutos) || 0) * 60
      if (consumed < cursor + secs) {
        return { ...t, remainingInPhase: cursor + secs - consumed }
      }
      cursor += secs
    }
    return timebox[timebox.length - 1] || { fase: 'Encerrado', minutos: 0 }
  }, [timebox, displaySeconds, mode, totalSeconds])

  const aulaAtiva = useMemo(
    () => aulas.find((a) => a.id_evento === aulaAtivaId) || null,
    [aulas, aulaAtivaId],
  )

  const temPlanejamento = aulas.some((a) => a.status === 'planejado' || a.status === 'em_execucao')
  const podeExecutar =
    Boolean(aulaAtiva) &&
    (aulaAtiva.status === 'planejado' || aulaAtiva.status === 'em_execucao')
  const aulaConcluida = aulaAtiva?.status === 'concluido'
  const timeboxEncerrado =
    totalSeconds > 0 &&
    ((mode === 'regressivo' && displaySeconds === 0) ||
      (mode === 'progressivo' && elapsed >= totalSeconds))

  const tituloAula = useMemo(() => {
    const missao = (plano?.missao || 'Aula EduScrum').trim()
    return missao.length > 180 ? `${missao.slice(0, 177)}…` : missao
  }, [plano])

  function requestMove(taskId, toColuna) {
    if (!podeExecutar) {
      setAcaoErro('Registre e selecione o dia da aula no calendário antes de mover cards.')
      return
    }
    const task = tasks.find((t) => t.id === taskId)
    if (!task) return
    const fromColuna = task.coluna || 'para_fazer'
    if (fromColuna === toColuna) return
    setPendingMove({
      task,
      fromColuna,
      toColuna,
      fromLabel: colunaLabel(fromColuna),
      toLabel: colunaLabel(toColuna),
    })
  }

  function confirmMove(nota) {
    if (!pendingMove) return
    const { task, fromColuna, toColuna } = pendingMove
    const entrada = {
      de: fromColuna,
      para: toColuna,
      nota: nota.trim(),
      em: new Date().toISOString(),
    }
    setTasks((prev) => {
      const next = prev.map((t) => {
        if (t.id !== task.id) return t
        const historico = Array.isArray(t.historico) ? [...t.historico, entrada] : [entrada]
        return { ...t, coluna: toColuna, historico, ultima_observacao: nota.trim() }
      })
      queueBoardSave(next)
      return next
    })
    setPendingMove(null)
  }

  function handleAddTask(e) {
    e?.preventDefault?.()
    if (!podeExecutar) {
      setAcaoErro('Registre a aula na agenda antes de editar o Kanban.')
      return
    }
    const titulo = novaTarefaTitulo.trim()
    if (!titulo) return
    const id =
      typeof crypto !== 'undefined' && crypto.randomUUID
        ? crypto.randomUUID()
        : `t-${Date.now()}`
    setTasks((prev) => {
      const next = [
        ...prev,
        {
          id,
          titulo,
          coluna: 'para_fazer',
          cor: '#FDE68A',
          historico: [],
        },
      ]
      queueBoardSave(next, { syncPlan: true })
      return next
    })
    setNovaTarefaTitulo('')
  }

  function handleEditTask(task) {
    if (!podeExecutar || !task) return
    const titulo = window.prompt('Editar título do card:', task.titulo || '')
    if (titulo == null) return
    const nextTitle = titulo.trim()
    if (!nextTitle) return
    setTasks((prev) => {
      const next = prev.map((t) => (t.id === task.id ? { ...t, titulo: nextTitle } : t))
      queueBoardSave(next, { syncPlan: true })
      return next
    })
  }

  function handleDeleteTask(task) {
    if (!podeExecutar || !task) return
    if (!window.confirm(`Excluir o card “${task.titulo}”?`)) return
    setTasks((prev) => {
      const next = prev.filter((t) => t.id !== task.id)
      queueBoardSave(next, { syncPlan: true })
      return next
    })
  }

  async function handleRegistrarAulas(e) {
    e?.preventDefault?.()
    setRegistroErro('')
    const aulas = slotsRegistro.map((s) => ({
      data: s.data,
      turma: (s.turma || '').trim(),
      turno: s.turno,
      modo_execucao: s.modo_execucao,
    }))
    if (!aulas.length) {
      setRegistroErro('Inclua ao menos uma aula.')
      return
    }
    for (const a of aulas) {
      if (!a.data) {
        setRegistroErro('Cada aula precisa de uma data.')
        return
      }
      if (!a.turma) {
        setRegistroErro('Informe a turma de cada aula.')
        return
      }
    }
    const dupKey = new Set()
    for (const a of aulas) {
      const k = `${a.data}|${a.turma.toLowerCase()}|${a.turno}`
      if (dupKey.has(k)) {
        setRegistroErro(`Duplicado: ${formatarDataBR(a.data)} · ${a.turma} · ${a.turno}. No mesmo dia, mude a turma ou o turno.`)
        return
      }
      dupKey.add(k)
    }
    setRegistroBusy(true)
    try {
      const planData = buildPlanData({ plano, hipotese, problema, planoSession })
      const data = await api.registrarAulas({
        aulas,
        titulo: `EduScrum · ${tituloAula}`,
        nota_texto: [
          hipotese ? `Hipótese: ${hipotese}` : null,
          problema ? `Problema: ${problema}` : null,
        ]
          .filter(Boolean)
          .join('\n'),
        plano_session: planoSession,
        meta_json: {
          missao: plano?.missao || '',
          hipotese: hipotese || '',
          problema: (problema || '').slice(0, 500),
          timebox_min: totalSeconds / 60,
        },
        plan_data: planData,
        kanban_state: { tarefas: tasks },
      })
      setShowRegistro(false)
      setSlotsRegistro([
        {
          key: `s-${Date.now()}`,
          data: hojeISO(),
          turma: '',
          turno: 'manha',
          modo_execucao: 'reinicio',
        },
      ])
      await loadAulas()
      onAgendaChanged?.()
      const criados = data.eventos || []
      if (criados[0]?.id_evento) setAulaAtivaId(criados[0].id_evento)
    } catch (err) {
      setRegistroErro(err.message || 'Falha ao registrar aulas')
    } finally {
      setRegistroBusy(false)
    }
  }

  async function handleIniciar() {
    setAcaoErro('')
    if (!podeExecutar) {
      setAcaoErro('É necessário registrar o dia da aula na agenda antes de executar o plano.')
      setShowRegistro(true)
      return
    }
    if (aulaAtiva.status === 'planejado') {
      try {
        await api.updateAgendaEvento(aulaAtiva.id_evento, {
          titulo: aulaAtiva.titulo,
          status: 'em_execucao',
        })
        await loadAulas()
        onAgendaChanged?.()
      } catch (err) {
        setAcaoErro(err.message || 'Não foi possível iniciar a aula na agenda.')
        return
      }
    }
    setRunning(true)
  }

  function openRelato() {
    setAcaoErro('')
    if (!aulaAtiva || aulaAtiva.status === 'concluido') return
    setRunning(false)
    setShowRelato(true)
  }

  async function handleSubmitRelato(payload) {
    if (!aulaAtiva) return
    setRelatoBusy(true)
    setAcaoErro('')
    try {
      // garante último estado do board antes de concluir
      saveBoardStateDebounced.cancel()
      await saveBoardState({ tarefas: tasks })
      await api.concluirAula(aulaAtiva.id_evento, payload)
      setShowRelato(false)
      await loadAulas()
      onAgendaChanged?.()
    } catch (err) {
      setAcaoErro(err.message || 'Falha ao concluir a aula na agenda.')
    } finally {
      setRelatoBusy(false)
    }
  }

  function handlePrint() {
    window.print()
  }

  const papeis = plano?.papeis || {}

  return (
    <section className="mx-auto max-w-6xl animate-fade-in print:max-w-none">
      <div className="mb-6 text-center print:mb-4">
        <div className="mb-4 flex justify-center print:mb-3">
          <BrandLogo
            variant="internal"
            className="h-24 w-auto max-w-[360px] object-contain sm:h-28"
          />
        </div>
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-brand-600 print:hidden">
          Etapa 4
        </p>
        <h1 className="font-display text-3xl font-bold text-bordo-deep sm:text-4xl">
          Aula EduScrum
        </h1>
        <p className="mt-2 text-sm text-bordo-soft print:hidden">
          {resumeMode
            ? 'Retomada da aula — o Kanban e o plano foram restaurados da agenda.'
            : 'Plano de aula interativo — registre o dia na agenda para executar.'}
        </p>
      </div>

      {/* Registro / planejamento do dia */}
      <div className="mb-5 rounded-2xl border border-brand-200 bg-white/95 p-4 shadow-soft print:hidden sm:p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
              Planejamento no calendário
            </p>
            <h2 className="mt-1 font-display text-lg font-bold text-bordo-deep">
              Registro da aula / aulas
            </h2>
            <p className="mt-1 text-xs text-bordo-soft">
              O plano só pode ser executado depois de agendar o dia no calendário.
            </p>
          </div>
          <button
            type="button"
            className="btn-primary !px-4 !py-2 text-sm"
            onClick={() => {
              setShowRegistro(true)
              setRegistroErro('')
            }}
          >
            Registrar aula(s)
          </button>
        </div>

        {!temPlanejamento ? (
          <p className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-900">
            Nenhuma aula registrada ainda. Use o botão acima para criar o evento correspondente na
            agenda.
          </p>
        ) : (
          <div className="mt-3 space-y-2">
            <label className="block text-[10px] font-bold uppercase tracking-wide text-bordo">
              Aula em execução / foco
            </label>
            <select
              className="field-input"
              value={aulaAtivaId || ''}
              onChange={(e) => setAulaAtivaId(Number(e.target.value) || null)}
              disabled={running}
            >
              {aulas.map((a) => (
                <option key={a.id_evento} value={a.id_evento}>
                  {formatarDataBR(a.data_evento)}
                  {a.turma ? ` · ${a.turma}` : ''}
                  {a.turno ? ` · ${TURNO_OPTS.find((t) => t.id === a.turno)?.label || a.turno}` : ''}
                  {' · '}
                  {a.modo_execucao === 'continuidade' ? 'Prosseguimento' : a.modo_execucao === 'reinicio' ? 'Início' : ''}
                  {' · '}
                  {STATUS_LABEL[a.status] || a.status}
                </option>
              ))}
            </select>
            <ul className="flex flex-wrap gap-2 pt-1">
              {aulas.map((a) => (
                <li
                  key={a.id_evento}
                  className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${
                    a.status === 'concluido'
                      ? 'bg-emerald-100 text-emerald-800'
                      : a.status === 'em_execucao'
                        ? 'bg-amber-100 text-amber-900'
                        : 'bg-brand-100 text-bordo'
                  }`}
                >
                  {formatarDataBR(a.data_evento)}
                  {a.turma ? ` · ${a.turma}` : ''}
                  {a.turno ? ` · ${TURNO_OPTS.find((t) => t.id === a.turno)?.label || a.turno}` : ''}
                  {' · '}
                  {STATUS_LABEL[a.status] || a.status}
                </li>
              ))}
            </ul>
          </div>
        )}
        {acaoErro ? (
          <p className="mt-2 text-xs font-semibold text-brand-700">{acaoErro}</p>
        ) : null}
      </div>

      <div
        className={`grid gap-5 lg:grid-cols-[1fr_240px] ${
          !podeExecutar ? 'relative' : ''
        }`}
      >
        {!podeExecutar ? (
          <div className="pointer-events-none absolute inset-0 z-10 rounded-2xl bg-white/55 backdrop-blur-[1px] print:hidden" />
        ) : null}

        <div className="space-y-5">
          <div className="rounded-2xl border border-brand-200 bg-white/95 p-5 shadow-soft sm:p-6">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-600">
              Missão da Aula
            </p>
            <h2 className="mt-2 font-display text-xl font-bold leading-snug text-bordo-deep sm:text-2xl">
              {plano?.missao || 'Missão a definir'}
            </h2>
            {hipotese && (
              <p className="mt-3 rounded-xl bg-brand-50 px-3 py-2 text-sm text-bordo-soft">
                <span className="font-semibold text-bordo">Hipótese:</span> {hipotese}
              </p>
            )}

            <div className="mt-5">
              <p className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-bordo">
                Regra dos Times
              </p>
              <div className="grid gap-3 sm:grid-cols-3">
                {[
                  { key: 'lider', icon: 'fa-flag', label: 'Líder' },
                  { key: 'guardiao', icon: 'fa-hourglass-half', label: 'Guardião' },
                  { key: 'apresentador', icon: 'fa-bullhorn', label: 'Apresentador' },
                ].map((role) => (
                  <div
                    key={role.key}
                    className="rounded-xl border border-brand-100 bg-brand-50/70 p-3"
                  >
                    <p className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-bordo">
                      <i className={`fa-solid ${role.icon} text-brand-600`} />
                      {role.label}
                    </p>
                    <p className="text-xs leading-relaxed text-bordo-soft">
                      {papeis[role.key] || '—'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-brand-200 bg-white/80 p-4 shadow-soft sm:p-5">
            <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-bordo">
                  Quadro Kanban
                </p>
                <p className="mt-0.5 text-[11px] text-bordo-soft print:hidden">
                  Arraste o card. Observação de implementação é obrigatória. Auto-save ativo.
                </p>
              </div>
              <p
                className={`text-[10px] font-bold uppercase tracking-wide print:hidden ${
                  saveStatus === 'saving'
                    ? 'text-amber-700'
                    : saveStatus === 'saved'
                      ? 'text-emerald-700'
                      : saveStatus === 'error'
                        ? 'text-rose-600'
                        : 'text-bordo-soft'
                }`}
                aria-live="polite"
              >
                {saveStatus === 'saving'
                  ? 'Salvando…'
                  : saveStatus === 'saved'
                    ? 'Salvo'
                    : saveStatus === 'error'
                      ? 'Erro ao salvar'
                      : aulaAtivaId || initialEventoId
                        ? 'Auto-save'
                        : 'Salva ao registrar aula'}
              </p>
            </div>

            {podeExecutar && !aulaConcluida ? (
              <form
                onSubmit={handleAddTask}
                className="mb-3 flex flex-wrap gap-2 print:hidden"
              >
                <input
                  className="field-input min-w-[180px] flex-1 !py-2 text-sm"
                  value={novaTarefaTitulo}
                  onChange={(e) => setNovaTarefaTitulo(e.target.value)}
                  placeholder="Novo card / passo…"
                />
                <button type="submit" className="btn-ghost !px-3 !py-2 text-xs">
                  + Card
                </button>
              </form>
            ) : null}

            <div className="grid gap-3 md:grid-cols-3">
              {COLUNAS.map((col) => {
                const cards = tasks.filter((t) => (t.coluna || 'para_fazer') === col.id)
                const isTarget = dropTarget === col.id
                return (
                  <div
                    key={col.id}
                    className={`min-h-[220px] rounded-xl border p-3 transition ${col.tone} ${
                      isTarget ? 'ring-2 ring-brand-500 ring-offset-2' : ''
                    }`}
                    onDragOver={(e) => {
                      if (!podeExecutar) return
                      e.preventDefault()
                      e.dataTransfer.dropEffect = 'move'
                      if (dropTarget !== col.id) setDropTarget(col.id)
                    }}
                    onDragLeave={() => {
                      if (dropTarget === col.id) setDropTarget(null)
                    }}
                    onDrop={(e) => {
                      e.preventDefault()
                      setDropTarget(null)
                      const taskId = e.dataTransfer.getData('text/plain')
                      setDraggingId(null)
                      if (taskId) requestMove(taskId, col.id)
                    }}
                  >
                    <div className="mb-3 flex items-center justify-between">
                      <h3 className="text-sm font-bold text-bordo-deep">{col.label}</h3>
                      <span className="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-bold text-bordo-soft">
                        {cards.length}
                      </span>
                    </div>
                    <ul className="space-y-2">
                      {cards.map((task) => (
                        <li
                          key={task.id}
                          draggable={podeExecutar}
                          onDragStart={(e) => {
                            if (!podeExecutar) {
                              e.preventDefault()
                              return
                            }
                            e.dataTransfer.setData('text/plain', String(task.id))
                            e.dataTransfer.effectAllowed = 'move'
                            setDraggingId(task.id)
                          }}
                          onDragEnd={() => {
                            setDraggingId(null)
                            setDropTarget(null)
                          }}
                          className={`rounded-lg border border-black/5 p-3 text-sm font-medium text-bordo-deep shadow-sm print:cursor-default ${
                            podeExecutar ? 'cursor-grab active:cursor-grabbing' : 'cursor-not-allowed opacity-80'
                          } ${draggingId === task.id ? 'opacity-50' : ''}`}
                          style={{
                            backgroundColor: task.cor || '#FDE68A',
                            transform: `rotate(${(String(task.id).charCodeAt(1) % 3) - 1}deg)`,
                          }}
                        >
                          <p>{task.titulo}</p>
                          {task.ultima_observacao ? (
                            <p className="mt-2 line-clamp-2 text-[10px] font-normal leading-snug text-bordo/80">
                              <i className="fa-solid fa-comment-dots mr-1 opacity-70" />
                              {task.ultima_observacao}
                            </p>
                          ) : null}
                          {podeExecutar && !aulaConcluida ? (
                            <div className="mt-2 flex gap-2 print:hidden">
                              <button
                                type="button"
                                className="text-[10px] font-bold text-bordo/70 hover:text-bordo"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleEditTask(task)
                                }}
                              >
                                Editar
                              </button>
                              <button
                                type="button"
                                className="text-[10px] font-bold text-rose-600/80 hover:text-rose-700"
                                onClick={(e) => {
                                  e.stopPropagation()
                                  handleDeleteTask(task)
                                }}
                              >
                                Excluir
                              </button>
                            </div>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        <aside className="rounded-2xl border border-brand-200 bg-white/95 p-4 shadow-soft print:border print:shadow-none">
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-bordo">
            Timebox
          </p>
          <div className="mb-4 rounded-xl bg-gradient-to-b from-brand-600 to-bordo p-4 text-center text-white">
            <p className="text-[10px] font-semibold uppercase tracking-widest opacity-80">
              {phase?.fase || '—'}
            </p>
            <p className="mt-1 font-display text-4xl font-bold tabular-nums tracking-tight">
              {formatMmSs(displaySeconds)}
            </p>
            <p className="mt-1 text-[11px] opacity-80">
              {mode === 'regressivo' ? 'Regressivo' : 'Progressivo'} · {totalSeconds / 60} min
            </p>
          </div>

          <div className="mb-3 flex gap-2 print:hidden">
            <button
              type="button"
              className="btn-primary flex-1 !px-2 !py-2 text-xs disabled:cursor-not-allowed disabled:opacity-50"
              disabled={aulaConcluida || (!podeExecutar && !running)}
              onClick={() => {
                if (running) setRunning(false)
                else handleIniciar()
              }}
            >
              {running ? 'Pausar' : 'Iniciar'}
            </button>
            <button
              type="button"
              className="btn-ghost flex-1 !px-2 !py-2 text-xs"
              onClick={() => {
                setElapsed(0)
                setRunning(false)
              }}
            >
              Reset
            </button>
          </div>

          <div className="mb-4 flex gap-2 print:hidden">
            <button
              type="button"
              onClick={() => setMode('regressivo')}
              className={`flex-1 rounded-lg px-2 py-1.5 text-[11px] font-semibold ${
                mode === 'regressivo' ? 'bg-bordo text-white' : 'bg-brand-50 text-bordo-soft'
              }`}
            >
              Regressivo
            </button>
            <button
              type="button"
              onClick={() => setMode('progressivo')}
              className={`flex-1 rounded-lg px-2 py-1.5 text-[11px] font-semibold ${
                mode === 'progressivo' ? 'bg-bordo text-white' : 'bg-brand-50 text-bordo-soft'
              }`}
            >
              Progressivo
            </button>
          </div>

          <ul className="space-y-2">
            {timebox.map((t) => (
              <li
                key={t.fase}
                className={`rounded-lg border px-3 py-2 text-xs ${
                  phase?.fase === t.fase
                    ? 'border-brand-500 bg-brand-50'
                    : 'border-brand-100 bg-white'
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-bold text-bordo-deep">{t.fase}</span>
                  <span className="tabular-nums text-bordo-soft">{t.minutos} min</span>
                </div>
                {t.descricao && (
                  <p className="mt-1 text-[11px] text-bordo-soft">{t.descricao}</p>
                )}
              </li>
            ))}
          </ul>

          {podeExecutar && !aulaConcluida ? (
            <button
              type="button"
              className="btn-primary mt-4 w-full !py-2.5 text-xs print:hidden"
              onClick={openRelato}
              disabled={running && !timeboxEncerrado}
              title={
                running && !timeboxEncerrado
                  ? 'Pause ou aguarde o fim do timebox para concluir'
                  : 'Registrar o que houve e concluir a realização'
              }
            >
              Registrar e concluir aula
            </button>
          ) : null}
          {aulaConcluida ? (
            <p className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-center text-[11px] font-bold text-emerald-800 print:hidden">
              Realização registrada — aparece no mapa do início.
            </p>
          ) : null}
        </aside>
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-brand-100 pt-5 print:hidden">
        <button type="button" className="btn-ghost" onClick={onVoltar}>
          ← Voltar
        </button>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setShowRegistro(true)}
            className="rounded-xl border border-brand-300 bg-brand-50 px-4 py-2 text-xs font-bold text-bordo transition hover:bg-brand-100"
          >
            Registrar aula(s)
          </button>
          <button
            type="button"
            onClick={handlePrint}
            className="rounded-xl border border-transparent px-4 py-2 text-xs font-semibold text-bordo-soft transition hover:border-brand-200 hover:bg-white hover:text-bordo"
          >
            Imprimir Guia do Professor
          </button>
        </div>
      </div>

      <div className="hidden print:mt-6 print:block">
        <BrandLogo
          variant="internal"
          className="mb-2 h-20 w-auto max-w-[280px] object-contain"
        />
        <p className="text-xs text-bordo-soft">
          Guia gerado por inove4us · {user?.nome_clie || 'Professor'} ·{' '}
          {new Date().toLocaleDateString('pt-BR')}
        </p>
      </div>

      <KanbanMoveModal
        pending={pendingMove}
        onCancel={() => setPendingMove(null)}
        onConfirm={confirmMove}
      />

      {showRelato ? (
        <RelatoAulaModal
          aula={aulaAtiva}
          missao={tituloAula}
          busy={relatoBusy}
          onCancel={() => {
            if (!relatoBusy) setShowRelato(false)
          }}
          onSubmit={handleSubmitRelato}
        />
      ) : null}

      {showRegistro ? (
        <div
          className="fixed inset-0 z-[85] flex items-end justify-center bg-bordo-deep/45 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowRegistro(false)
          }}
        >
          <form
            onSubmit={handleRegistrarAulas}
            className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-brand-200 bg-white p-5 shadow-soft"
          >
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
              Agenda executiva
            </p>
            <h3 className="mt-1 font-display text-xl font-bold text-bordo-deep">
              Registrar aula(s)
            </h3>
            <p className="mt-2 text-sm text-bordo-soft">
              Para cada data, informe turma, turno e o caminho: prosseguimento (mesma turma) ou
              começar do início (outra turma / reset). No mesmo dia pode haver mais de uma aula se
              turma ou turno forem diferentes.
            </p>
            <p className="mt-2 rounded-lg bg-brand-50 px-3 py-2 text-xs text-bordo">
              <strong>Missão:</strong> {tituloAula}
            </p>

            <ul className="mt-4 space-y-3">
              {slotsRegistro.map((slot, idx) => (
                <li
                  key={slot.key}
                  className="rounded-xl border border-brand-100 bg-brand-50/40 p-3"
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-bordo">
                      Aula {idx + 1}
                    </p>
                    {slotsRegistro.length > 1 ? (
                      <button
                        type="button"
                        className="text-xs font-bold text-rose-600 hover:underline"
                        onClick={() => removeSlot(slot.key)}
                      >
                        Remover
                      </button>
                    ) : null}
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div>
                      <label className="text-[10px] font-bold uppercase text-bordo-soft">Data</label>
                      <input
                        type="date"
                        className="field-input mt-1 !py-2"
                        value={slot.data}
                        onChange={(e) => updateSlot(slot.key, { data: e.target.value })}
                        required
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase text-bordo-soft">
                        Turma
                      </label>
                      <input
                        className="field-input mt-1 !py-2"
                        value={slot.turma}
                        onChange={(e) => updateSlot(slot.key, { turma: e.target.value })}
                        placeholder="Ex.: 8º A"
                        required
                      />
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase text-bordo-soft">
                        Turno
                      </label>
                      <select
                        className="field-input mt-1 !py-2"
                        value={slot.turno}
                        onChange={(e) => updateSlot(slot.key, { turno: e.target.value })}
                      >
                        {TURNO_OPTS.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] font-bold uppercase text-bordo-soft">
                        Caminho
                      </label>
                      <select
                        className="field-input mt-1 !py-2"
                        value={slot.modo_execucao}
                        onChange={(e) => updateSlot(slot.key, { modo_execucao: e.target.value })}
                      >
                        {MODO_OPTS.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <p className="mt-2 text-[11px] leading-snug text-bordo-soft">
                    {MODO_OPTS.find((m) => m.id === slot.modo_execucao)?.hint}
                  </p>
                </li>
              ))}
            </ul>

            <button
              type="button"
              className="btn-ghost mt-3 w-full !py-2 text-xs"
              onClick={addSlot}
            >
              + Outra aula (outra data, turno ou turma)
            </button>

            {registroErro ? (
              <p className="mt-2 text-xs font-semibold text-brand-700">{registroErro}</p>
            ) : null}

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                className="btn-ghost !px-4 !py-2 text-sm"
                onClick={() => setShowRegistro(false)}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primary !px-4 !py-2 text-sm"
                disabled={registroBusy}
              >
                {registroBusy ? 'Salvando…' : 'Salvar na agenda'}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </section>
  )
}
