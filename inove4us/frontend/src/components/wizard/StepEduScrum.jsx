import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import BrandLogo from '../BrandLogo'
import RelatoAulaModal from '../RelatoAulaModal'
import ClassFeedbackModal from '../ClassFeedbackModal'
import { api } from '../../lib/api'
import { debounce } from '../../lib/debounce'
import { isSchemaPendingError, listarMinhasTurmas } from '../../services/instituicoesService'
import KanbanMoveModal from './KanbanMoveModal'
import KanbanPeiMenu, { isPeiSubcard, orderColumnCards } from './KanbanPeiMenu'

const COLUNAS = [
  { id: 'para_fazer', label: 'Para Fazer', tone: 'border-brand-200 bg-brand-50/60' },
  { id: 'fazendo', label: 'Fazendo', tone: 'border-amber-200 bg-amber-50/50' },
  { id: 'pronto', label: 'Pronto', tone: 'border-emerald-200 bg-emerald-50/50' },
]

function cardMinutes(task) {
  const n = Number(task?.duracao_minutos)
  return Number.isFinite(n) && n > 0 ? n : 10
}

function formatMinutos(min) {
  const m = Math.max(0, Math.round(Number(min) || 0))
  if (m < 60) return `${m} min`
  const h = Math.floor(m / 60)
  const rest = m % 60
  return rest ? `${h} h ${rest} min` : `${h} h`
}

const CONTEXTO_LABEL = {
  sala: 'Sala de aula',
  campo: 'Campo / externo',
  misto: 'Misto (sala + campo)',
}

function colunaLabel(id) {
  return COLUNAS.find((c) => c.id === id)?.label || id
}

/** Diário de bordo: notas das transições de cards na mesa (só leitura no fechamento). */
function buildDiarioBordo(tasks, aulaId, { multiAula = false } = {}) {
  const entries = []
  const list = Array.isArray(tasks) ? tasks : []
  for (const t of list) {
    if (multiAula && aulaId != null && t.aula_id != null) {
      if (Number(t.aula_id) !== Number(aulaId)) continue
    }
    const hist = Array.isArray(t.historico) ? t.historico : []
    for (const h of hist) {
      const nota = String(h?.nota || '').trim()
      if (!nota) continue
      entries.push({
        card: t.titulo || t.titulo_do_card || 'Card',
        de: h.de,
        para: h.para,
        deLabel: colunaLabel(h.de),
        paraLabel: colunaLabel(h.para),
        nota,
        em: h.em,
      })
    }
  }
  return entries
}

function metodologiaFromAula(aula, plano) {
  const meta = aula?.meta_json && typeof aula.meta_json === 'object' ? aula.meta_json : {}
  for (const src of [meta, plano, aula]) {
    if (!src || typeof src !== 'object') continue
    for (const key of ['metodologia_nome', 'metodologia', 'metodologia_usada', 'nome_metodologia']) {
      const val = String(src[key] || '').trim()
      if (val) return val
    }
  }
  const tipo = String(aula?.tipo || '').toLowerCase()
  if (tipo.includes('eduscrum')) return 'EduScrum'
  if (tipo.includes('pbl')) return 'PBL'
  return tipo || 'EduScrum'
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

/** Garante aula_id em cada card (legado → dono do board). */
function stampAulaId(tasks, aulaId) {
  const aid = aulaId == null ? null : Number(aulaId)
  return (tasks || []).map((t) => {
    const aula_id = t.aula_id != null ? Number(t.aula_id) : aid
    const fromList = Array.isArray(t.aula_ids)
      ? t.aula_ids.map(Number).filter((n) => Number.isFinite(n))
      : []
    const aula_ids =
      aula_id != null && !fromList.includes(aula_id) ? [aula_id, ...fromList] : fromList
    return { ...t, aula_id, aula_ids }
  })
}

function aulaIdsDoCard(task) {
  const fromList = Array.isArray(task?.aula_ids)
    ? task.aula_ids.map(Number).filter((n) => Number.isFinite(n))
    : []
  if (task?.aula_id != null) {
    const aid = Number(task.aula_id)
    if (Number.isFinite(aid) && !fromList.includes(aid)) fromList.unshift(aid)
  }
  return fromList
}

function labelCurtoAula(a) {
  if (!a) return 'Aula'
  const data = formatarDataBR(a.data_evento)
  const turma = a.turma ? ` · ${a.turma}` : ''
  return `${data}${turma}`
}

function aulaExecutavel(a) {
  return a && (a.status === 'planejado' || a.status === 'em_execucao')
}

function emptySlotRegistro(overrides = {}) {
  return {
    key: `s-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    data: hojeISO(),
    turma: '',
    turno: 'manha',
    modo_execucao: 'reinicio',
    card_ids: [],
    escopos: {},
    ...overrides,
  }
}

function buildPlanData({ plano, hipotese, problema, planoSession, causas }) {
  return {
    problema: problema || '',
    hipotese: hipotese || '',
    plano_session: planoSession || null,
    plano: plano || null,
    ...(causas != null ? { causas } : {}),
  }
}

export default function StepEduScrum({
  plano,
  hipotese,
  problema,
  causas = null,
  user,
  planoSession,
  disciplinaId = null,
  desafioId: desafioIdProp = null,
  onVoltar,
  onAgendaChanged,
  onAulasRegistradas,
  onReplicar,
  initialEventoId = null,
  initialKanbanState = null,
  resumeMode = false,
  readOnly = false,
  colaboradores = [],
}) {
  const [tasks, setTasks] = useState(() =>
    tasksFromKanbanState(initialKanbanState, plano?.tarefas_kanban || []),
  )
  const [duracaoMetaMin, setDuracaoMetaMin] = useState(() => {
    const fromPlano = Number(plano?.duracao_total_estimada_min)
    if (Number.isFinite(fromPlano) && fromPlano > 0) return fromPlano
    const cards = tasksFromKanbanState(initialKanbanState, plano?.tarefas_kanban || [])
    const soma = cards.reduce((acc, t) => acc + cardMinutes(t), 0)
    return soma || 50
  })
  const [draggingId, setDraggingId] = useState(null)

  useEffect(() => {
    const fromPlano = Number(plano?.duracao_total_estimada_min)
    const soma = tasks.reduce((acc, t) => acc + cardMinutes(t), 0)
    if (Number.isFinite(fromPlano) && fromPlano > 0) {
      setDuracaoMetaMin(Math.max(fromPlano, soma || 0))
    } else if (soma > 0) {
      setDuracaoMetaMin(soma)
    }
    // Só reage a novo plano gerado / retomado — não a cada drag.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plano?.duracao_total_estimada_min, plano?.missao, planoSession])
  const [dropTarget, setDropTarget] = useState(null)
  const [pendingMove, setPendingMove] = useState(null)

  const [aulas, setAulas] = useState([])
  const [aulaAtivaId, setAulaAtivaId] = useState(initialEventoId || null)
  /** Multi-aula: 'todas' | id_evento. Com 1 aula o seletor some. */
  const [visaoKanban, setVisaoKanban] = useState('todas')
  const [novaTarefaAulaId, setNovaTarefaAulaId] = useState(null)
  const [boardLoading, setBoardLoading] = useState(false)
  const [showRegistro, setShowRegistro] = useState(false)
  const [slotsRegistro, setSlotsRegistro] = useState(() => [emptySlotRegistro()])
  const [registroBusy, setRegistroBusy] = useState(false)
  const [registroErro, setRegistroErro] = useState('')
  const [turmasCadastro, setTurmasCadastro] = useState([])
  const [turmasLoading, setTurmasLoading] = useState(false)
  const [desafioIdLocal, setDesafioIdLocal] = useState(desafioIdProp || null)
  const [conviteEmail, setConviteEmail] = useState('')
  const [conviteCardId, setConviteCardId] = useState('')
  const [conviteBusy, setConviteBusy] = useState(false)
  const [conviteMsg, setConviteMsg] = useState('')
  const [conviteErro, setConviteErro] = useState('')
  const [peiBusyId, setPeiBusyId] = useState(null)

  useEffect(() => {
    if (!showRegistro) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [showRegistro])

  useEffect(() => {
    if (!showRegistro) return
    let cancelled = false
    setTurmasLoading(true)
    listarMinhasTurmas()
      .then((data) => {
        if (cancelled) return
        setTurmasCadastro(Array.isArray(data?.turmas) ? data.turmas : [])
      })
      .catch((err) => {
        if (cancelled) return
        if (!isSchemaPendingError(err)) {
          console.warn('[StepEduScrum] turmas:', err?.message)
        }
        setTurmasCadastro([])
      })
      .finally(() => {
        if (!cancelled) setTurmasLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [showRegistro])

  useEffect(() => {
    if (desafioIdProp) setDesafioIdLocal(desafioIdProp)
  }, [desafioIdProp])

  const desafioIdAtivo = desafioIdLocal || desafioIdProp || null

  const TURNO_OPTS = [
    { id: 'manha', label: 'Manhã' },
    { id: 'tarde', label: 'Tarde' },
    { id: 'noite', label: 'Noite' },
  ]
  const MODO_OPTS = [
    {
      id: 'continuidade',
      label: 'Prosseguimento',
      hint: 'Mesma turma / mesmo problema — retoma a mesa de onde parou',
    },
    {
      id: 'reinicio',
      label: 'Começar do início',
      hint: 'Outra turma (ou reset) — mesmo problema, mesa zerada',
    },
  ]

  const cardsCatalogo = useMemo(() => {
    const seen = new Set()
    const out = []
    const fontes = [
      ...(Array.isArray(plano?.tarefas_kanban) ? plano.tarefas_kanban : []),
      ...tasks,
    ]
    for (const t of fontes) {
      const id = String(t?.id || '').trim()
      if (!id || seen.has(id)) continue
      seen.add(id)
      out.push({
        id,
        titulo: (t.titulo || 'Card').trim() || 'Card',
        objetivo: (t.objetivo || '').trim(),
      })
    }
    return out
  }, [plano?.tarefas_kanban, tasks])

  function updateSlot(key, patch) {
    setSlotsRegistro((prev) => prev.map((s) => (s.key === key ? { ...s, ...patch } : s)))
  }

  function toggleSlotCard(key, cardId) {
    setSlotsRegistro((prev) =>
      prev.map((s) => {
        if (s.key !== key) return s
        const ids = Array.isArray(s.card_ids) ? [...s.card_ids] : []
        const escopos = { ...(s.escopos || {}) }
        const idx = ids.indexOf(cardId)
        if (idx >= 0) {
          ids.splice(idx, 1)
          delete escopos[cardId]
        } else {
          ids.push(cardId)
          if (!escopos[cardId]) escopos[cardId] = ''
        }
        return { ...s, card_ids: ids, escopos }
      }),
    )
  }

  function updateSlotEscopo(key, cardId, nota) {
    setSlotsRegistro((prev) =>
      prev.map((s) => {
        if (s.key !== key) return s
        return { ...s, escopos: { ...(s.escopos || {}), [cardId]: nota } }
      }),
    )
  }

  function addSlot() {
    setSlotsRegistro((prev) => [
      ...prev,
      emptySlotRegistro({
        turma: prev[prev.length - 1]?.turma || '',
        turno: 'tarde',
        modo_execucao: 'reinicio',
      }),
    ])
  }

  function removeSlot(key) {
    setSlotsRegistro((prev) => (prev.length <= 1 ? prev : prev.filter((s) => s.key !== key)))
  }
  const [acaoErro, setAcaoErro] = useState('')
  const [showRelato, setShowRelato] = useState(false)
  const [relatoBusy, setRelatoBusy] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [feedbackAula, setFeedbackAula] = useState(null)
  const [feedbackBusy, setFeedbackBusy] = useState(false)
  const [avisosMesa, setAvisosMesa] = useState([])
  const [saveStatus, setSaveStatus] = useState('idle') // idle | saving | saved | error
  const [novaTarefaTitulo, setNovaTarefaTitulo] = useState('')

  const eventoIdRef = useRef(null)
  eventoIdRef.current = aulaAtivaId || initialEventoId
  const aulasRef = useRef(aulas)
  aulasRef.current = aulas
  const visaoRef = useRef(visaoKanban)
  visaoRef.current = visaoKanban
  const initialEventoRef = useRef(initialEventoId)
  initialEventoRef.current = initialEventoId

  const planMetaRef = useRef({ plano, hipotese, problema, planoSession, causas })
  planMetaRef.current = { plano, hipotese, problema, planoSession, causas }

  const multiAula = aulas.length > 1

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const data = await api.getAvisosMesa()
        if (!cancelled) setAvisosMesa(Array.isArray(data?.avisos) ? data.avisos : [])
      } catch {
        if (!cancelled) setAvisosMesa([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const loadAulas = useCallback(async () => {
    try {
      let lista = []
      const anchorId = initialEventoId
      if (anchorId) {
        try {
          const kb = await api.getAgendaKanban(anchorId)
          if (Array.isArray(kb.aulas) && kb.aulas.length) {
            lista = kb.aulas.map((a) => ({
              ...a,
              tipo: 'aula_eduscrum',
            }))
          }
        } catch {
          /* fallback abaixo */
        }
      }
      if (!lista.length && planoSession) {
        const data = await api.listAgendaEventos('', planoSession)
        lista = (data.eventos || []).filter((e) => e.tipo === 'aula_eduscrum')
      }
      if (anchorId && !lista.some((a) => a.id_evento === anchorId)) {
        const one = await api.getAgendaEvento(anchorId)
        if (one?.evento) lista = [one.evento, ...lista]
      }
      setAulas(lista)
      setAulaAtivaId((prev) => {
        const prefer =
          lista.find((a) => a.status === 'em_execucao') ||
          lista.find((a) => a.status === 'planejado' && diaEvento(a.data_evento) === hojeISO()) ||
          lista.find((a) => a.status === 'planejado') ||
          (prev && lista.some((a) => a.id_evento === prev)
            ? lista.find((a) => a.id_evento === prev)
            : null) ||
          (initialEventoId && lista.some((a) => a.id_evento === initialEventoId)
            ? lista.find((a) => a.id_evento === initialEventoId)
            : null) ||
          lista[0]
        return prefer?.id_evento ?? null
      })
      setNovaTarefaAulaId((prev) => {
        const executaveis = lista.filter(aulaExecutavel)
        if (prev && executaveis.some((a) => a.id_evento === prev)) return prev
        return executaveis[0]?.id_evento ?? lista[0]?.id_evento ?? null
      })
      if (lista.length > 1) {
        setVisaoKanban((prev) => {
          if (prev === 'todas') return 'todas'
          if (prev && lista.some((a) => a.id_evento === Number(prev))) return prev
          return 'todas'
        })
      }
    } catch {
      setAulas([])
    }
  }, [planoSession, initialEventoId])

  // Só reseta a mesa quando muda a aula/plano de verdade — não a cada nova
  // referência de objeto (isso fechava o modal ao editar o escopo do card).
  const planoSyncKey = [
    initialEventoId ?? '',
    planoSession ?? '',
    plano?.missao ?? '',
    Array.isArray(plano?.tarefas_kanban) ? plano.tarefas_kanban.length : 0,
  ].join('|')
  const syncPayloadRef = useRef({ initialKanbanState, plano, initialEventoId })
  syncPayloadRef.current = { initialKanbanState, plano, initialEventoId }

  useEffect(() => {
    const {
      initialKanbanState: ks,
      plano: pl,
      initialEventoId: evId,
    } = syncPayloadRef.current
    if (!resumeMode) {
      setTasks(
        stampAulaId(tasksFromKanbanState(ks, pl?.tarefas_kanban || []), evId),
      )
    }
    setPendingMove(null)
    setAcaoErro('')
    if (evId) setAulaAtivaId(evId)
    // Modal de registro permanece aberto — não chamar setShowRegistro(false) aqui.
  }, [planoSyncKey, resumeMode])

  useEffect(() => {
    loadAulas()
  }, [loadAulas])

  /** Carrega board conforme visão (todas / aula). */
  useEffect(() => {
    if (!aulas.length) return
    if (!resumeMode && !initialEventoId && !eventoIdRef.current) return

    let cancelled = false
    async function loadBoard() {
      const anchor = initialEventoId || aulaAtivaId || aulas[0]?.id_evento
      if (!anchor) return
      setBoardLoading(true)
      try {
        if (multiAula && visaoKanban === 'todas') {
          const data = await api.getAgendaKanban(anchor)
          if (cancelled) return
          setTasks(data.tarefas || [])
        } else {
          const targetId = multiAula
            ? Number(visaoKanban)
            : Number(aulaAtivaId || anchor)
          const data = await api.getAgendaKanban(anchor, targetId)
          if (cancelled) return
          setTasks(data.tarefas || [])
        }
      } catch {
        if (cancelled) return
        try {
          const targetId =
            multiAula && visaoKanban !== 'todas'
              ? Number(visaoKanban)
              : Number(aulaAtivaId || anchor)
          const one = await api.getAgendaEvento(targetId)
          if (cancelled) return
          setTasks(
            stampAulaId(
              tasksFromKanbanState(one.evento?.kanban_state, plano?.tarefas_kanban || []),
              targetId,
            ),
          )
        } catch {
          /* mantém tasks atuais */
        }
      } finally {
        if (!cancelled) setBoardLoading(false)
      }
    }
    loadBoard()
    return () => {
      cancelled = true
    }
  }, [
    aulas.length,
    multiAula,
    visaoKanban,
    // Só recarrega por troca de foco quando visão é 1 aula (não multi/todas)
    multiAula && visaoKanban === 'todas' ? null : aulaAtivaId,
    initialEventoId,
    resumeMode,
  ])

  /**
   * Auto-save do quadro — PUT /api/agenda-eventos/:id/estado
   * @param {{ tarefas: any[] }} newState
   * @param {object|null} newPlanData — se o plano estrutural mudou (add/edit/delete)
   */
  const saveBoardState = useCallback(async (id, newState, newPlanData = null) => {
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
      debounce((id, newState, newPlanData = null) => {
        saveBoardState(id, newState, newPlanData)
      }, 700),
    [saveBoardState],
  )

  const saveMultiBoardDebounced = useMemo(
    () =>
      debounce(async (nextTasks, syncPlan = false) => {
        const lista = aulasRef.current || []
        if (!lista.length) return
        setSaveStatus('saving')
        const byAula = new Map()
        for (const a of lista) byAula.set(Number(a.id_evento), [])
        const gerais = []
        for (const t of nextTasks) {
          const aids = aulaIdsDoCard(t)
          if (!aids.length) {
            gerais.push(t)
            continue
          }
          for (const aid of aids) {
            if (!byAula.has(aid)) continue
            const escopos = Array.isArray(t.escopos_turma)
              ? t.escopos_turma.filter((e) => Number(e?.aula_id) === aid)
              : []
            byAula.get(aid).push({
              ...t,
              aula_id: aid,
              aula_ids: aids,
              escopos_turma: escopos.length
                ? escopos
                : (t.escopos_turma || []).filter((e) => Number(e?.aula_id) === aid),
            })
          }
        }
        const geralOwner =
          (initialEventoRef.current && byAula.has(Number(initialEventoRef.current))
            ? Number(initialEventoRef.current)
            : null) || lista[0]?.id_evento
        if (geralOwner != null && gerais.length) {
          byAula.set(Number(geralOwner), [
            ...(byAula.get(Number(geralOwner)) || []),
            ...gerais.map((t) => ({ ...t, aula_id: null })),
          ])
        }
        const meta = planMetaRef.current
        try {
          for (const [aid, subset] of byAula) {
            const forSave = subset.map((t) => {
              if (t.aula_id == null) return { ...t, aula_id: null }
              return { ...t, aula_id: aid }
            })
            const payload = { kanban_state: { tarefas: forSave } }
            if (syncPlan) {
              payload.plan_data = buildPlanData({
                ...meta,
                plano: { ...(meta.plano || {}), tarefas_kanban: forSave },
              })
            }
            await api.updateAgendaEstado(aid, payload)
          }
          setSaveStatus('saved')
        } catch (err) {
          console.warn('Falha ao auto-salvar kanban multi-aula:', err)
          setSaveStatus('error')
        }
      }, 700),
    [],
  )

  useEffect(
    () => () => {
      saveBoardStateDebounced.cancel()
      saveMultiBoardDebounced.cancel()
    },
    [saveBoardStateDebounced, saveMultiBoardDebounced],
  )

  function queueBoardSave(nextTasks, { syncPlan = false } = {}) {
    const lista = aulasRef.current || []
    const multi = lista.length > 1
    const visao = visaoRef.current

    if (multi && visao === 'todas') {
      saveBoardStateDebounced.cancel()
      saveMultiBoardDebounced(nextTasks, syncPlan)
      return
    }

    saveMultiBoardDebounced.cancel()
    const targetId =
      multi && visao !== 'todas'
        ? Number(visao)
        : Number(aulaAtivaId || initialEventoId || eventoIdRef.current)
    if (!targetId) return
    eventoIdRef.current = targetId
    const stamped = stampAulaId(nextTasks, targetId)
    const kanbanState = { tarefas: stamped }
    if (syncPlan) {
      const meta = planMetaRef.current
      const newPlanData = buildPlanData({
        ...meta,
        plano: { ...(meta.plano || {}), tarefas_kanban: stamped },
      })
      saveBoardStateDebounced(targetId, kanbanState, newPlanData)
    } else {
      saveBoardStateDebounced(targetId, kanbanState)
    }
  }

  const execucao = useMemo(() => {
    const somaCards = tasks.reduce((acc, t) => acc + cardMinutes(t), 0) || 50
    const total = Math.max(Number(duracaoMetaMin) || somaCards, somaCards)
    let feitos = 0
    let fazendoMin = 0
    let prontoCount = 0
    let fazendoCount = 0
    for (const t of tasks) {
      const m = cardMinutes(t)
      if (t.coluna === 'pronto') {
        feitos += m
        prontoCount += 1
      } else if (t.coluna === 'fazendo') {
        feitos += m * 0.5
        fazendoMin += m
        fazendoCount += 1
      }
    }
    const pct = total > 0 ? Math.min(100, Math.round((feitos / total) * 100)) : 0
    return {
      somaCards,
      total,
      feitos: Math.round(feitos),
      restantes: Math.max(0, Math.round(total - feitos)),
      pct,
      prontoCount,
      fazendoCount,
      pendentes: tasks.length - prontoCount - fazendoCount,
      fazendoMin,
    }
  }, [tasks, duracaoMetaMin])

  const contextoExecucao = plano?.contexto_execucao || (execucao.total > 60 ? 'campo' : 'sala')

  const aulaAtiva = useMemo(
    () => aulas.find((a) => a.id_evento === aulaAtivaId) || null,
    [aulas, aulaAtivaId],
  )

  const aulasExecutaveis = useMemo(() => aulas.filter(aulaExecutavel), [aulas])

  const temPlanejamento = aulas.some((a) => a.status === 'planejado' || a.status === 'em_execucao')
  const podeExecutar =
    !readOnly &&
    Boolean(aulaAtiva) &&
    (aulaAtiva.status === 'planejado' || aulaAtiva.status === 'em_execucao')
  const aulaConcluida = aulaAtiva?.status === 'concluido'

  const aulaAlvoCriacao = useMemo(() => {
    if (!multiAula) return aulaAtivaId
    if (visaoKanban === 'todas') return novaTarefaAulaId
    return Number(visaoKanban)
  }, [multiAula, aulaAtivaId, visaoKanban, novaTarefaAulaId])

  const podeCriarCard = useMemo(() => {
    if (readOnly) return false
    if (!aulasExecutaveis.length) return false
    if (!multiAula) return podeExecutar && !aulaConcluida
    return aulasExecutaveis.some((a) => a.id_evento === Number(aulaAlvoCriacao))
  }, [readOnly, aulasExecutaveis, multiAula, podeExecutar, aulaConcluida, aulaAlvoCriacao])

  /** Board editável na execução e também após relato — aí a mesa pode avançar. */
  const boardEditavel = useMemo(() => {
    if (readOnly) return false
    if (!aulas.length) return false
    if (!multiAula) return podeExecutar || aulaConcluida
    if (visaoKanban === 'todas') {
      return aulas.some((a) => aulaExecutavel(a) || a.status === 'concluido')
    }
    const a = aulas.find((x) => x.id_evento === Number(visaoKanban))
    return Boolean(a && (aulaExecutavel(a) || a.status === 'concluido'))
  }, [readOnly, aulas, multiAula, podeExecutar, aulaConcluida, visaoKanban])

  function taskEditavel(task) {
    if (readOnly) return false
    if (!boardEditavel) return false
    const aids = aulaIdsDoCard(task)
    if (!aids.length) {
      return aulasExecutaveis.length > 0
    }
    const linked = aids
      .map((aid) => aulas.find((x) => x.id_evento === aid))
      .filter(Boolean)
    if (!linked.length) return false
    // Execução OU pós-relato: card editável se aula está em andamento ou concluída
    if (linked.every((a) => a.status === 'concluido')) return true
    return linked.some(aulaExecutavel)
  }

  function labelAulaDoCard(task) {
    const aids = aulaIdsDoCard(task)
    if (!aids.length) return 'Geral do desafio'
    return aids
      .map((aid) => {
        const a = aulas.find((x) => x.id_evento === aid)
        return a ? labelCurtoAula(a) : `Aula #${aid}`
      })
      .join(' · ')
  }

  function colabDoCard(task) {
    const cardId = String(task?.id || '').trim()
    if (!cardId || !Array.isArray(colaboradores) || !colaboradores.length) return null
    return (
      colaboradores.find(
        (c) =>
          String(c.card_id || '').trim() === cardId &&
          ['pendente', 'aceito'].includes(String(c.status || '').toLowerCase()),
      ) || null
    )
  }

  function cardPodeMover(task, toColuna) {
    const aids = aulaIdsDoCard(task)
    if (!aids.length) {
      return {
        ok: false,
        msg: 'Card sem aula associada. Ao registrar a aula, vincule o card e declare o escopo da turma.',
      }
    }
    const dest = String(toColuna || '').trim()
    // Execução: Para Fazer ↔ Fazendo livre
    if (dest && dest !== 'pronto') {
      return { ok: true }
    }
    // Finalização (Pronto): DoD — aulas desta turma concluídas
    for (const aid of aids) {
      const a = aulas.find((x) => x.id_evento === aid)
      if (!a || a.status !== 'concluido') {
        return {
          ok: false,
          msg: 'Para mover para Pronto, conclua a(s) aula(s) desta turma com o relato. Na execução, mova livremente entre Para Fazer e Fazendo.',
        }
      }
    }
    return { ok: true }
  }

  const missaoCompleta = useMemo(() => {
    return (plano?.missao || 'Aula · método inove4us').trim()
  }, [plano])

  const metodologiaNome = useMemo(
    () => metodologiaFromAula(aulaAtiva, plano),
    [aulaAtiva, plano],
  )

  const escolaOverrideMsg = useMemo(() => {
    const ov = plano?.escola_override || aulaAtiva?.plan_data?.escola_override
    if (!ov?.ativa && !ov?.mensagem && !ov?.diretriz_customizada) return ''
    return (
      ov.mensagem ||
      (metodologiaNome
        ? `Sua escola definiu uma regra para ${metodologiaNome}: ${ov.diretriz_customizada || ''}`
        : ov.diretriz_customizada || '')
    ).trim()
  }, [plano, aulaAtiva, metodologiaNome])

  const aulaContextoLabel = useMemo(() => {
    const disc =
      aulaAtiva?.meta_json?.disciplina_nome ||
      plano?.disciplina_nome ||
      plano?.disciplina ||
      ''
    const etapa = aulaAtiva?.titulo || missaoCompleta || ''
    const parts = [metodologiaNome, disc, etapa].map((s) => String(s || '').trim()).filter(Boolean)
    return parts.join(' · ') || metodologiaNome || 'Aula'
  }, [aulaAtiva, plano, missaoCompleta, metodologiaNome])

  const diarioBordoFechamento = useMemo(
    () =>
      buildDiarioBordo(tasks, aulaAtiva?.id_evento, {
        multiAula: Boolean(multiAula),
      }),
    [tasks, aulaAtiva?.id_evento, multiAula],
  )

  /** Só para campos VARCHAR curtos da agenda — a UI mostra a missão completa. */
  const tituloAgendaCurto = useMemo(() => {
    const base = `Método inove4us · ${missaoCompleta}`
    return base.length > 200 ? `${base.slice(0, 197)}…` : base
  }, [missaoCompleta])

  function requestMove(taskId, toColuna) {
    const task = tasks.find((t) => t.id === taskId)
    if (!task) return
    if (!taskEditavel(task)) {
      setAcaoErro(
        'Este card não está editável agora. Registre/selecione a aula em execução ou conclua o relato para liberar a mesa.',
      )
      return
    }
    const gate = cardPodeMover(task, toColuna)
    if (!gate.ok) {
      setAcaoErro(gate.msg)
      return
    }
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
    if (toColuna === 'pronto') {
      // Card concluído: aulas já estão no passado (relato) — refresca o grafo
      onAgendaChanged?.()
    }
  }

  async function handleAdaptarPei(task, perfilSelecionado, alunoNomeOpt = '') {
    if (!task?.id || !perfilSelecionado || peiBusyId) return
    if (isPeiSubcard(task)) return
    const idEvento =
      Number(task.aula_id) ||
      aulaIdsDoCard(task)[0] ||
      (visaoKanban !== 'todas' ? Number(visaoKanban) : null) ||
      Number(aulaAtivaId) ||
      null
    setPeiBusyId(task.id)
    setAcaoErro('')
    try {
      const data = await api.adaptarPei({
        card_id: String(task.id),
        titulo_card: task.titulo || task.titulo_do_card || 'Card',
        descricao_card:
          task.como_executar_detalhado ||
          task.mecanica_passo_a_passo ||
          task.descricao ||
          task.objetivo ||
          '',
        perfil_selecionado: perfilSelecionado,
        aluno_nome: alunoNomeOpt || undefined,
        id_evento: idEvento || undefined,
        desafio_id: desafioIdLocal || undefined,
      })
      const kt = data?.kanban_task
      const sub = data?.subcard
      const escolaMsg =
        data?.escola_override?.mensagem || kt?.escola_override?.mensagem || ''
      if (escolaMsg) {
        setAcaoErro('') // limpa erro; banner dedicado abaixo no card
      }
      const newTask = {
        id: kt?.id || sub?.card_key,
        titulo: kt?.titulo || sub?.titulo || `Adaptação PEI: ${task.titulo || ''}`,
        descricao: kt?.descricao || sub?.descricao || '',
        como_executar_detalhado: kt?.descricao || sub?.descricao || '',
        coluna: kt?.coluna || sub?.coluna || task.coluna || 'para_fazer',
        parent_card_id: kt?.parent_card_id || String(task.id),
        perfil_inclusao: kt?.perfil_inclusao || perfilSelecionado,
        aluno_nome: alunoNomeOpt || kt?.aluno_nome || '',
        cor: kt?.cor || '#FDE68A',
        historico: [],
        ultima_observacao: `Adaptação PEI · ${perfilSelecionado}`,
        escola_override: data?.escola_override || kt?.escola_override || null,
        pei_override_versao_aplicada:
          data?.pei_override_versao_aplicada || kt?.pei_override_versao_aplicada || null,
        aula_id: task.aula_id ?? idEvento,
        aula_ids: Array.isArray(task.aula_ids) && task.aula_ids.length
          ? task.aula_ids
          : idEvento
            ? [idEvento]
            : [],
        pei_concluido: false,
        db_id: sub?.id,
      }
      if (!newTask.id) throw new Error('Subcard PEI sem id')
      setTasks((prev) => {
        if (prev.some((t) => String(t.id) === String(newTask.id))) return prev
        // Subcard nasce na mesma coluna do pai para aparecer aninhado
        const next = [
          ...prev,
          { ...newTask, coluna: task.coluna || 'para_fazer' },
        ]
        queueBoardSave(next, { syncPlan: true })
        return next
      })
      if (typeof data?.creditos_ia === 'number') {
        // saldo atualizado no backend; UI de créditos pode refrescar no hub
      }
    } catch (err) {
      setAcaoErro(err?.message || 'Falha ao gerar adaptação PEI.')
    } finally {
      setPeiBusyId(null)
    }
  }

  function togglePeiConcluido(task) {
    if (!isPeiSubcard(task) || !taskEditavel(task)) return
    const done = Boolean(task.pei_concluido)
    setTasks((prev) => {
      const next = prev.map((t) => {
        if (t.id !== task.id) return t
        return {
          ...t,
          pei_concluido: !done,
          ultima_observacao: !done
            ? 'Adaptação PEI concluída'
            : 'Adaptação PEI reaberta',
        }
      })
      queueBoardSave(next)
      return next
    })
  }

  function handleAddTask(e) {
    e?.preventDefault?.()
    if (!podeCriarCard) {
      setAcaoErro('Selecione uma aula em planejamento/execução para criar o card.')
      return
    }
    const titulo = novaTarefaTitulo.trim()
    if (!titulo) return
    const destAula = Number(aulaAlvoCriacao)
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
          duracao_minutos: 10,
          historico: [],
          aula_id: destAula,
        },
      ]
      queueBoardSave(next, { syncPlan: true })
      return next
    })
    setNovaTarefaTitulo('')
  }

  function handleEditTask(task) {
    if (!taskEditavel(task) || !task) return
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
    if (!taskEditavel(task) || !task) return
    if (!window.confirm(`Excluir o card “${task.titulo}”?`)) return
    setTasks((prev) => {
      const next = prev.filter((t) => t.id !== task.id)
      queueBoardSave(next, { syncPlan: true })
      return next
    })
  }

  function handleSelectFocoAula(id) {
    const num = Number(id) || null
    setAulaAtivaId(num)
    if (multiAula && num) {
      setVisaoKanban(num)
      if (aulasExecutaveis.some((a) => a.id_evento === num)) {
        setNovaTarefaAulaId(num)
      }
    }
  }

  function handleSelectVisao(value) {
    if (value === 'todas') {
      setVisaoKanban('todas')
      return
    }
    const num = Number(value)
    setVisaoKanban(num)
    setAulaAtivaId(num)
    if (aulasExecutaveis.some((a) => a.id_evento === num)) {
      setNovaTarefaAulaId(num)
    }
  }

  async function handleRegistrarAulas(e) {
    e?.preventDefault?.()
    setRegistroErro('')
    if (!cardsCatalogo.length) {
      setRegistroErro('Não há cards no plano para associar. Gere o plano do método inove4us antes.')
      return
    }
    const aulas = slotsRegistro.map((s) => ({
      data: s.data,
      turma: (s.turma || '').trim(),
      turno: s.turno,
      modo_execucao: s.modo_execucao,
      card_ids: Array.isArray(s.card_ids) ? s.card_ids.map(String) : [],
      escopos: s.escopos || {},
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
      if (!a.card_ids.length) {
        setRegistroErro(
          `Aula ${a.turma || '(sem turma)'}: associe ao menos um card — sem card a aula não tem o que realizar.`,
        )
        return
      }
      for (const cid of a.card_ids) {
        const nota = String(a.escopos[cid] || '').trim()
        if (!nota) {
          const titulo = cardsCatalogo.find((c) => c.id === cid)?.titulo || cid
          setRegistroErro(
            `Aula ${a.turma}: declare o que a turma vai realizar no card «${titulo}». O mesmo card em duas turmas exige escopo distinto para cada uma.`,
          )
          return
        }
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
      const planData = buildPlanData({ plano, hipotese, problema, planoSession, causas })
      const data = await api.registrarAulas({
        aulas,
        titulo: tituloAgendaCurto,
        desafio_id: desafioIdAtivo || undefined,
        nota_texto: [
          hipotese ? `Hipótese: ${hipotese}` : null,
          problema ? `Problema: ${problema}` : null,
        ]
          .filter(Boolean)
          .join('\n'),
        plano_session: planoSession,
        ...(disciplinaId != null ? { disciplina_id: disciplinaId } : {}),
        ...(causas != null ? { causas } : {}),
        meta_json: {
          missao: plano?.missao || '',
          hipotese: hipotese || '',
          problema: (problema || '').slice(0, 500),
          timebox_min: execucao.total,
          duracao_total_estimada_min: execucao.total,
          contexto_execucao: contextoExecucao,
          ...(disciplinaId != null ? { disciplina_id: disciplinaId } : {}),
          ...(causas != null ? { causas } : {}),
          ...(desafioIdAtivo ? { desafio_id: desafioIdAtivo } : {}),
        },
        plan_data: planData,
        kanban_state: { tarefas: tasks },
      })
      setShowRegistro(false)
      setSlotsRegistro([emptySlotRegistro()])
      if (data.desafio_id) setDesafioIdLocal(data.desafio_id)
      await loadAulas()
      onAgendaChanged?.()
      const criados = data.eventos || []
      if (criados[0]?.id_evento) setAulaAtivaId(criados[0].id_evento)
      onAulasRegistradas?.(data)

      // Convite opcional preenchido no mesmo formulário
      const emailConv = conviteEmail.trim().toLowerCase()
      const cardConv = conviteCardId.trim()
      if (data.desafio_id && emailConv && cardConv) {
        try {
          const inv = await api.convidarColaborador(data.desafio_id, {
            email: emailConv,
            card_id: cardConv,
          })
          setConviteMsg(
            inv.email?.channel === 'dev_log'
              ? `Convite criado para ${emailConv}. Em local o e-mail NÃO é enviado — use o link: ${inv.convite_url}`
              : `Convite enviado para ${emailConv}. Link: ${inv.convite_url}`,
          )
          setConviteEmail('')
          setConviteCardId('')
          setConviteErro('')
        } catch (invErr) {
          setConviteErro(invErr.message || 'Aulas salvas, mas o convite falhou.')
        }
      }
    } catch (err) {
      setRegistroErro(err.message || 'Falha ao registrar aulas')
    } finally {
      setRegistroBusy(false)
    }
  }

  async function handleEnviarConviteAvulso(e) {
    e?.preventDefault?.()
    setConviteErro('')
    setConviteMsg('')
    const email = conviteEmail.trim().toLowerCase()
    const cardId = conviteCardId.trim()
    if (!desafioIdAtivo) {
      setConviteErro(
        'Aguarde o desafio ser salvo (após gerar os cards) ou registre as aulas para convidar.',
      )
      return
    }
    if (!email || !email.includes('@')) {
      setConviteErro('Informe o e-mail do professor convidado.')
      return
    }
    if (!cardId) {
      setConviteErro('Escolha o card que o convidado vai realizar.')
      return
    }
    setConviteBusy(true)
    try {
      const inv = await api.convidarColaborador(desafioIdAtivo, {
        email,
        card_id: cardId,
      })
      setConviteMsg(
        inv.email?.channel === 'dev_log'
          ? `Convite criado para ${email}. Em local o e-mail NÃO é enviado — use o link: ${inv.convite_url}`
          : `Convite enviado para ${email}. Link: ${inv.convite_url}`,
      )
      setConviteEmail('')
      setConviteCardId('')
    } catch (err) {
      setConviteErro(err.message || 'Falha ao enviar convite.')
    } finally {
      setConviteBusy(false)
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
        // Execução: cards vinculados sobem para Fazendo
        const aid = Number(aulaAtiva.id_evento)
        setTasks((prev) => {
          let changed = false
          const next = prev.map((t) => {
            const linked = aulaIdsDoCard(t).some((id) => Number(id) === aid)
            if (!linked) return t
            if ((t.coluna || 'para_fazer') !== 'para_fazer') return t
            changed = true
            const entrada = {
              de: 'para_fazer',
              para: 'fazendo',
              nota: 'Aula em execução',
              em: new Date().toISOString(),
            }
            const historico = Array.isArray(t.historico) ? [...t.historico, entrada] : [entrada]
            return { ...t, coluna: 'fazendo', historico }
          })
          if (changed) queueBoardSave(next)
          return changed ? next : prev
        })
        await loadAulas()
        onAgendaChanged?.()
      } catch (err) {
        setAcaoErro(err.message || 'Não foi possível iniciar a aula na agenda.')
        return
      }
    }
  }

  function openRelato() {
    setAcaoErro('')
    if (!aulaAtiva || aulaAtiva.status === 'concluido') return
    setShowRelato(true)
  }

  async function handleSubmitRelato(payload) {
    if (!aulaAtiva) return
    setRelatoBusy(true)
    setAcaoErro('')
    const aulaParaFeedback = aulaAtiva
    try {
      // garante último estado do board antes de concluir
      saveBoardStateDebounced.cancel()
      saveMultiBoardDebounced.cancel()
      const targetId = aulaAtiva.id_evento
      const subset = multiAula
        ? tasks.filter((t) => Number(t.aula_id) === Number(targetId) || (t.aula_id == null && Number(targetId) === Number(initialEventoId)))
        : tasks
      await saveBoardState(targetId, { tarefas: stampAulaId(subset, targetId) })
      await api.concluirAula(aulaAtiva.id_evento, payload)
      setShowRelato(false)
      await loadAulas()
      onAgendaChanged?.()
      // Fase final: Feedback Loop
      setFeedbackAula(aulaParaFeedback)
      setShowFeedback(true)
    } catch (err) {
      setAcaoErro(err.message || 'Falha ao concluir a aula na agenda.')
    } finally {
      setRelatoBusy(false)
    }
  }

  async function handleSubmitFeedback(payload) {
    if (!feedbackAula?.id_evento) return
    setFeedbackBusy(true)
    setAcaoErro('')
    try {
      await api.enviarFeedbackAula(feedbackAula.id_evento, payload)
      setShowFeedback(false)
      setFeedbackAula(null)
    } catch (err) {
      setAcaoErro(err.message || 'Falha ao salvar o feedback da aula.')
    } finally {
      setFeedbackBusy(false)
    }
  }

  function closeFeedback() {
    if (feedbackBusy) return
    setShowFeedback(false)
    setFeedbackAula(null)
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
          Aula · método inove4us
        </h1>
        <p className="mt-2 text-sm text-bordo-soft print:hidden">
          {resumeMode
            ? 'Retomada da aula — a mesa e o plano foram restaurados da agenda.'
            : temPlanejamento
              ? 'Plano de aula interativo — arraste os cards e registre o progresso.'
              : 'Pré-visualização do plano completo. Leia os cards para planejar; registre a aula na agenda para executar na mesa.'}
        </p>
      </div>

      {avisosMesa.length ? (
        <div className="mb-4 rounded-2xl border border-brand-200 bg-brand-50/70 p-3 shadow-soft print:hidden sm:p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
            Avisos da coordenação
          </p>
          <ul className="mt-2 space-y-2">
            {avisosMesa.map((a) => (
              <li
                key={a.id}
                className="rounded-xl border border-brand-100 bg-white px-3 py-2 text-sm text-bordo"
              >
                {a.texto}
                {a.turma_nome || a.disciplina_nome ? (
                  <span className="mt-0.5 block text-[11px] text-bordo-soft">
                    {[a.disciplina_nome, a.turma_nome].filter(Boolean).join(' · ')}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {escolaOverrideMsg ? (
        <div className="mb-4 rounded-2xl border border-amber-200 bg-amber-50 p-3 shadow-soft print:hidden sm:p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-amber-900">
            Regra da escola em vigor
          </p>
          <p className="mt-1.5 text-sm leading-relaxed text-amber-950">
            {escolaOverrideMsg}
          </p>
        </div>
      ) : null}

      {/* Registro / planejamento do dia */}
      {!readOnly ? (
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
              Você já pode ler e usar este plano para preparar a aula. Para arrastar
              cards e registrar progresso na mesa, agende o dia no calendário.
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
              onChange={(e) => handleSelectFocoAula(e.target.value)}
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
      ) : null}

      <div className="grid gap-5 lg:grid-cols-[1fr_240px]">
        {!boardEditavel && !readOnly ? (
          <div className="col-span-full rounded-xl border border-brand-200 bg-brand-50/90 px-3 py-2 text-xs font-semibold text-bordo print:hidden">
            Pré-visualização do plano — os cards abaixo são o roteiro da aula.
            Registre a(s) aula(s) acima para liberar a execução na mesa.
          </div>
        ) : null}

        <div className={`space-y-5 ${!boardEditavel ? 'opacity-100' : ''}`}>
          <div className="rounded-2xl border border-brand-200 bg-white/95 p-5 shadow-soft sm:p-6">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-brand-600">
              Missão da Aula
            </p>
            <h2 className="mt-2 whitespace-pre-wrap font-display text-base font-semibold leading-relaxed text-bordo-deep sm:text-lg">
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
                  Mesa
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
                {boardLoading
                  ? 'Carregando…'
                  : saveStatus === 'saving'
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

            {multiAula ? (
              <div className="mb-3 flex flex-wrap gap-1.5 print:hidden" role="tablist" aria-label="Visão por aula">
                <button
                  type="button"
                  role="tab"
                  aria-selected={visaoKanban === 'todas'}
                  className={`rounded-lg px-3 py-1.5 text-[11px] font-bold transition ${
                    visaoKanban === 'todas'
                      ? 'bg-bordo text-white'
                      : 'bg-brand-50 text-bordo hover:bg-brand-100'
                  }`}
                  onClick={() => handleSelectVisao('todas')}
                >
                  Todas as aulas
                </button>
                {aulas.map((a) => (
                  <button
                    key={a.id_evento}
                    type="button"
                    role="tab"
                    aria-selected={Number(visaoKanban) === a.id_evento}
                    className={`rounded-lg px-3 py-1.5 text-[11px] font-bold transition ${
                      Number(visaoKanban) === a.id_evento
                        ? 'bg-bordo text-white'
                        : 'bg-brand-50 text-bordo hover:bg-brand-100'
                    }`}
                    onClick={() => handleSelectVisao(a.id_evento)}
                    title={STATUS_LABEL[a.status] || a.status}
                  >
                    {labelCurtoAula(a)}
                  </button>
                ))}
              </div>
            ) : null}

            {podeCriarCard ? (
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
                {multiAula ? (
                  <select
                    className="field-input !w-auto min-w-[140px] !py-2 text-sm"
                    value={
                      visaoKanban === 'todas'
                        ? novaTarefaAulaId || ''
                        : Number(visaoKanban) || ''
                    }
                    onChange={(e) => setNovaTarefaAulaId(Number(e.target.value) || null)}
                    disabled={visaoKanban !== 'todas'}
                    aria-label="Aula do card"
                  >
                    {aulas.map((a) => (
                      <option
                        key={a.id_evento}
                        value={a.id_evento}
                        disabled={!aulaExecutavel(a)}
                      >
                        {labelCurtoAula(a)}
                        {!aulaExecutavel(a) ? ' (concluída)' : ''}
                      </option>
                    ))}
                  </select>
                ) : null}
                <button type="submit" className="btn-ghost !px-3 !py-2 text-xs">
                  + Card
                </button>
              </form>
            ) : aulas.length && !aulasExecutaveis.length ? (
              <p className="mb-3 rounded-lg bg-emerald-50 px-3 py-2 text-[11px] font-semibold text-emerald-800 print:hidden">
                Aulas realizadas: agora você pode finalizar na mesa movendo cards para Pronto
                (DoD cumprido).
              </p>
            ) : null}

            <div className="grid gap-3 md:grid-cols-3">
              {COLUNAS.map((col) => {
                const cards = tasks.filter((t) => (t.coluna || 'para_fazer') === col.id)
                const ordered = orderColumnCards(cards)
                const isTarget = dropTarget === col.id
                return (
                  <div
                    key={col.id}
                    className={`min-h-[220px] rounded-xl border p-3 transition ${col.tone} ${
                      isTarget ? 'ring-2 ring-brand-500 ring-offset-2' : ''
                    }`}
                    onDragOver={(e) => {
                      if (!boardEditavel) return
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
                      {ordered.map(({ task, depth }) => {
                        const editavel = taskEditavel(task)
                        const hasAula = aulaIdsDoCard(task).length > 0
                        const podeArrastar = editavel && hasAula
                        const colabCard = colabDoCard(task)
                        const escopos = Array.isArray(task.escopos_turma)
                          ? task.escopos_turma.filter((e) => String(e?.nota || '').trim())
                          : []
                        const pei = isPeiSubcard(task)
                        const peiDone = Boolean(task.pei_concluido)
                        const peiLoading = peiBusyId === task.id
                        return (
                        <li
                          key={task.id}
                          draggable={podeArrastar}
                          onDragStart={(e) => {
                            if (!podeArrastar) {
                              e.preventDefault()
                              if (editavel && !hasAula) {
                                setAcaoErro(
                                  'Card sem aula associada. Ao registrar a aula, vincule o card e declare o escopo da turma.',
                                )
                              }
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
                          className={[
                            'rounded-lg border p-3 text-sm font-medium text-bordo-deep shadow-sm print:cursor-default',
                            pei
                              ? 'ml-4 border-l-4 border-l-yellow-400 border-amber-200/80 bg-amber-50 sm:ml-6'
                              : 'border-black/5',
                            podeArrastar
                              ? 'cursor-grab active:cursor-grabbing'
                              : 'cursor-default',
                            draggingId === task.id ? 'opacity-50' : '',
                            !pei && task.coluna === 'pronto'
                              ? 'ring-1 ring-emerald-400/70'
                              : '',
                            pei && peiDone ? 'opacity-80' : '',
                          ].join(' ')}
                          style={
                            pei
                              ? undefined
                              : {
                                  backgroundColor: task.cor || '#FDE68A',
                                  transform: `rotate(${(String(task.id).charCodeAt(1) % 3) - 1}deg)`,
                                }
                          }
                        >
                          {multiAula && visaoKanban === 'todas' ? (
                            <p className="mb-1.5 inline-block rounded bg-white/75 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-bordo/80">
                              {labelAulaDoCard(task)}
                            </p>
                          ) : null}
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex min-w-0 flex-1 items-start gap-2">
                              {pei ? (
                                <label
                                  className="mt-0.5 flex shrink-0 cursor-pointer items-center"
                                  title="Concluir adaptação (independente do card pai)"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <input
                                    type="checkbox"
                                    className="h-4 w-4 rounded border-amber-400 text-amber-700 focus:ring-amber-400"
                                    checked={peiDone}
                                    disabled={!editavel}
                                    onChange={() => togglePeiConcluido(task)}
                                  />
                                  <span className="sr-only">Concluir adaptação PEI</span>
                                </label>
                              ) : null}
                              <div className="min-w-0">
                                {pei ? (
                                  <p className="mb-0.5 text-[9px] font-bold uppercase tracking-wide text-amber-800">
                                    PEI · {task.perfil_inclusao || 'Adaptação'}
                                    {task.aluno_nome ? ` · ${task.aluno_nome}` : ''}
                                    {depth > 0 ? ' · subcard' : ''}
                                  </p>
                                ) : null}
                                <p
                                  className={`font-semibold leading-snug ${
                                    pei && peiDone ? 'line-through decoration-amber-700/50' : ''
                                  }`}
                                >
                                  {task.titulo}
                                </p>
                                {pei && task.escola_override?.mensagem ? (
                                  <p className="mt-1 rounded-md border border-amber-200 bg-amber-50/90 px-1.5 py-1 text-[10px] leading-snug text-amber-950">
                                    <span className="font-semibold">Regra da escola: </span>
                                    {task.escola_override.mensagem}
                                  </p>
                                ) : null}
                              </div>
                            </div>
                            <div className="flex shrink-0 items-start gap-1">
                              {!pei && !readOnly ? (
                                <KanbanPeiMenu
                                  disabled={Boolean(peiBusyId)}
                                  busy={peiLoading}
                                  onSelectPerfil={(perfil, alunoNome) =>
                                    void handleAdaptarPei(task, perfil, alunoNome)
                                  }
                                />
                              ) : null}
                              {!pei ? (
                                <span className="rounded-md bg-white/70 px-1.5 py-0.5 text-[10px] font-bold tabular-nums text-bordo">
                                  {cardMinutes(task)}′
                                </span>
                              ) : null}
                            </div>
                          </div>
                          {peiLoading ? (
                            <p className="mt-2 text-[11px] font-semibold text-amber-900">
                              Carregando adaptação inclusiva…
                            </p>
                          ) : null}
                          {escopos.length ? (
                            <ul className="mt-1.5 space-y-1">
                              {escopos.map((esc, i) => (
                                <li
                                  key={`${task.id}-esc-${esc.aula_id ?? i}`}
                                  className="rounded bg-white/70 px-1.5 py-1 text-[10px] font-normal leading-snug text-bordo/95"
                                >
                                  <span className="font-bold">
                                    {esc.turma ? `${esc.turma}: ` : 'Escopo: '}
                                  </span>
                                  {esc.nota}
                                </li>
                              ))}
                            </ul>
                          ) : null}
                          {editavel && hasAula && (task.coluna || 'para_fazer') !== 'pronto' && !cardPodeMover(task, 'pronto').ok ? (
                            <p className="mt-1.5 text-[10px] font-semibold leading-snug text-amber-900/90">
                              Pronto só após o relato da(s) aula(s) desta turma. Em execução:
                              mova livremente entre Para Fazer e Fazendo.
                            </p>
                          ) : null}
                          {colabCard ? (
                            <p className="mt-1 text-[9px] font-bold uppercase tracking-wide text-bordo/70">
                              Atribuição: {colabCard.email_convidado} · {colabCard.status}{' '}
                              (visão isolada)
                            </p>
                          ) : null}
                          {task.objetivo && !pei ? (
                            <p className="mt-1.5 text-[10px] font-normal leading-snug text-bordo/90">
                              <span className="font-bold">Objetivo: </span>
                              {task.objetivo}
                            </p>
                          ) : null}
                          {task.como_executar_detalhado
                          || task.mecanica_passo_a_passo
                          || task.descricao ? (
                            <p className="mt-1.5 text-[10px] font-normal leading-snug text-bordo/85">
                              <span className="font-bold">
                                {pei ? 'Adaptação: ' : 'Como fazer: '}
                              </span>
                              {task.como_executar_detalhado
                                || task.mecanica_passo_a_passo
                                || task.descricao}
                            </p>
                          ) : null}
                          {task.dica_de_facilitacao && !pei ? (
                            <p className="mt-1.5 text-[10px] font-normal leading-snug text-bordo/80">
                              <i className="fa-solid fa-lightbulb mr-1 opacity-70" />
                              <span className="font-bold">Dica: </span>
                              {task.dica_de_facilitacao}
                            </p>
                          ) : null}
                          {task.ultima_observacao ? (
                            <p className="mt-2 line-clamp-2 text-[10px] font-normal leading-snug text-bordo/80">
                              <i className="fa-solid fa-comment-dots mr-1 opacity-70" />
                              {task.ultima_observacao}
                            </p>
                          ) : null}
                          {editavel ? (
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
                        )
                      })}
                    </ul>
                  </div>
                )
              })}
            </div>
          </div>
        </div>

        <aside className="rounded-2xl border border-brand-200 bg-white/95 p-4 shadow-soft print:border print:shadow-none">
          <p className="mb-3 text-xs font-bold uppercase tracking-[0.18em] text-bordo">
            Execução do plano
          </p>

          <div className="mb-4 rounded-xl bg-gradient-to-b from-brand-600 to-bordo p-4 text-white">
            <div className="flex items-center justify-between gap-2 text-[10px] font-semibold uppercase tracking-widest opacity-85">
              <span>{CONTEXTO_LABEL[contextoExecucao] || 'Execução'}</span>
              <span>{execucao.pct}%</span>
            </div>
            <p className="mt-2 font-display text-3xl font-bold tabular-nums tracking-tight">
              {formatMinutos(execucao.feitos)}
              <span className="ml-1 text-base font-semibold opacity-80">
                / {formatMinutos(execucao.total)}
              </span>
            </p>
            <p className="mt-1 text-[11px] opacity-85">
              Progresso pela movimentação dos cards (Pronto = 100%, Fazendo = 50%).
            </p>
            <div className="mt-3 h-2.5 overflow-hidden rounded-full bg-white/25">
              <div
                className="h-full rounded-full bg-white transition-all duration-500 ease-out"
                style={{ width: `${execucao.pct}%` }}
              />
            </div>
            <p className="mt-2 text-[11px] opacity-85">
              Restam ~{formatMinutos(execucao.restantes)} · {execucao.prontoCount} prontos ·{' '}
              {execucao.fazendoCount} em andamento · {execucao.pendentes} a fazer
            </p>
          </div>

          <label className="mb-3 block print:hidden">
            <span className="text-[10px] font-bold uppercase tracking-wide text-bordo-soft">
              Duração prevista do projeto (min)
            </span>
            <input
              type="number"
              min={20}
              max={480}
              step={5}
              className="field-input mt-1 !py-2"
              value={duracaoMetaMin}
              onChange={(e) => {
                const n = Number(e.target.value)
                if (!Number.isFinite(n)) return
                setDuracaoMetaMin(Math.max(20, Math.min(480, n)))
              }}
            />
            <span className="mt-1 block text-[11px] text-bordo-soft">
              Padrão de sala: 50 min. Em campo/externo, aumente conforme a complexidade
              (soma dos cards: {formatMinutos(execucao.somaCards)}).
            </span>
          </label>

          <ul className="mb-3 max-h-56 space-y-1.5 overflow-y-auto">
            {tasks.map((t) => {
              const col = t.coluna || 'para_fazer'
              const tone =
                col === 'pronto'
                  ? 'border-emerald-200 bg-emerald-50'
                  : col === 'fazendo'
                    ? 'border-amber-200 bg-amber-50'
                    : 'border-brand-100 bg-white'
              return (
                <li
                  key={t.id}
                  className={`rounded-lg border px-2.5 py-1.5 text-[11px] ${tone}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-semibold text-bordo-deep">{t.titulo}</span>
                    <span className="shrink-0 tabular-nums text-bordo-soft">
                      {cardMinutes(t)}′
                    </span>
                  </div>
                  <p className="text-[10px] text-bordo-soft">{colunaLabel(col)}</p>
                </li>
              )
            })}
          </ul>

          {podeExecutar && !aulaConcluida && aulaAtiva?.status === 'planejado' ? (
            <button
              type="button"
              className="btn-primary mb-2 w-full !py-2.5 text-xs print:hidden"
              onClick={handleIniciar}
            >
              Marcar aula em execução
            </button>
          ) : null}

          {podeExecutar && !aulaConcluida ? (
            <button
              type="button"
              className="btn-primary mt-1 w-full !py-2.5 text-xs print:hidden"
              onClick={openRelato}
              title="Registrar o que houve e concluir a realização"
            >
              Registrar e concluir aula
            </button>
          ) : null}
          {podeExecutar && !aulaConcluida ? (
            <p className="mt-2 text-[10px] leading-snug text-bordo-soft print:hidden">
              Na execução os cards já estão em <strong className="text-bordo">Fazendo</strong> e
              você move livremente entre Para Fazer e Fazendo. O relato conclui a aula e libera a
              finalização para <strong className="text-bordo">Pronto</strong>. Depois vem o
              Feedback Loop. Cada professor tem visão isolada.
            </p>
          ) : null}
          {aulaConcluida ? (
            <p className="mt-4 rounded-lg bg-emerald-50 px-3 py-2 text-center text-[11px] font-bold text-emerald-800 print:hidden">
              Realização registrada — cards desta turma liberados para Pronto. Em seguida, o
              feedback pós-aula.
            </p>
          ) : null}
        </aside>
      </div>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-brand-100 pt-5 print:hidden">
        <button type="button" className="btn-ghost" onClick={onVoltar}>
          ← Voltar
        </button>
        <div className="flex flex-wrap gap-2">
          {typeof onReplicar === 'function' && !readOnly ? (
            <button
              type="button"
              onClick={onReplicar}
              className="rounded-xl border border-brand-300 bg-white px-4 py-2 text-xs font-bold text-bordo transition hover:bg-brand-50"
            >
              Replicar para outra turma
            </button>
          ) : null}
          {!readOnly ? (
            <button
              type="button"
              onClick={() => setShowRegistro(true)}
              className="rounded-xl border border-brand-300 bg-brand-50 px-4 py-2 text-xs font-bold text-bordo transition hover:bg-brand-100"
            >
              Registrar aula(s)
            </button>
          ) : null}
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
          aula={{
            ...aulaAtiva,
            aluno_nome:
              tasks.find((t) => t?.aluno_nome)?.aluno_nome ||
              aulaAtiva?.meta_json?.aluno_nome ||
              '',
          }}
          missao={missaoCompleta}
          busy={relatoBusy}
          diarioBordo={diarioBordoFechamento}
          metodologiaNome={metodologiaNome}
          aulaContexto={aulaContextoLabel}
          temAlunosPei={tasks.some(
            (t) =>
              t?.perfil_inclusao ||
              (Array.isArray(t?.subcards) &&
                t.subcards.some((s) => s?.perfil_inclusao)),
          )}
          onCancel={() => {
            if (!relatoBusy) setShowRelato(false)
          }}
          onSubmit={handleSubmitRelato}
        />
      ) : null}

      {showFeedback && feedbackAula ? (
        <ClassFeedbackModal
          aula={feedbackAula}
          busy={feedbackBusy}
          onCancel={closeFeedback}
          onSkip={closeFeedback}
          onSubmit={handleSubmitFeedback}
        />
      ) : null}

      {showRegistro
        ? createPortal(
            <div
              className="fixed inset-0 z-[200] flex items-start justify-center overflow-y-auto bg-bordo-deep/55 p-3 sm:p-6"
              role="dialog"
              aria-modal="true"
              onMouseDown={(e) => {
                if (e.target === e.currentTarget) {
                  e.currentTarget.dataset.closeOnClick = '1'
                }
              }}
              onClick={(e) => {
                if (
                  e.target === e.currentTarget &&
                  e.currentTarget.dataset.closeOnClick === '1' &&
                  !registroBusy
                ) {
                  setShowRegistro(false)
                }
                delete e.currentTarget.dataset.closeOnClick
              }}
            >
              <form
                onSubmit={handleRegistrarAulas}
                onMouseDown={(e) => e.stopPropagation()}
                onClick={(e) => e.stopPropagation()}
                className="my-2 w-full max-w-2xl rounded-2xl border border-brand-200 bg-white p-5 shadow-soft sm:my-4 sm:p-6"
                style={{ maxHeight: 'min(92vh, 920px)', overflowY: 'auto' }}
              >
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
              Agenda executiva
            </p>
            <h3 className="mt-1 font-display text-xl font-bold text-bordo-deep">
              Registrar aula(s)
            </h3>
            <p className="mt-2 text-sm text-bordo-soft">
              Para cada aula: data, turma, turno e os cards que serão realizados. Em cada card,
              declare o escopo desta turma. Ao registrar, os cards entram em Fazendo (execução).
              Mover para Pronto exige as aulas da turma concluídas (relato).
            </p>
            <p className="mt-2 rounded-lg bg-brand-50 px-3 py-2 text-xs text-bordo">
              <strong>Missão:</strong> {missaoCompleta}
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
                      {turmasCadastro.length > 0 ? (
                        <select
                          className="field-input mt-1 !py-2"
                          value={slot.turma}
                          onChange={(e) => updateSlot(slot.key, { turma: e.target.value })}
                          required
                          disabled={turmasLoading}
                        >
                          <option value="">Selecione a turma…</option>
                          {turmasCadastro.map((t) => {
                            const label = [
                              t.disciplina_nome,
                              t.curso_nome,
                              t.nome,
                              t.turno,
                            ]
                              .filter(Boolean)
                              .join(' · ')
                            return (
                              <option key={t.id || `${t.nome}-${t.curso_id}`} value={t.nome}>
                                {label}
                              </option>
                            )
                          })}
                          {slot.turma &&
                          !turmasCadastro.some((t) => t.nome === slot.turma) ? (
                            <option value={slot.turma}>{slot.turma} (livre)</option>
                          ) : null}
                        </select>
                      ) : (
                        <input
                          className="field-input mt-1 !py-2"
                          value={slot.turma}
                          onChange={(e) => updateSlot(slot.key, { turma: e.target.value })}
                          placeholder={
                            turmasLoading
                              ? 'Carregando turmas…'
                              : 'Cadastre turmas em Instituições, ou digite aqui'
                          }
                          required
                        />
                      )}
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

                  <div className="mt-3 border-t border-brand-100 pt-3">
                    <p className="text-[10px] font-bold uppercase tracking-wide text-bordo">
                      Cards desta aula (obrigatório)
                    </p>
                    {!cardsCatalogo.length ? (
                      <p className="mt-2 text-xs font-semibold text-rose-700">
                        Nenhum card no plano — volte e gere o método inove4us com os cards.
                      </p>
                    ) : (
                      <ul className="mt-2 space-y-2">
                        {cardsCatalogo.map((card) => {
                          const checked = (slot.card_ids || []).includes(card.id)
                          const checkId = `reg-card-${slot.key}-${card.id}`
                          const escopoId = `reg-escopo-${slot.key}-${card.id}`
                          return (
                            <li
                              key={`${slot.key}-${card.id}`}
                              className="rounded-lg border border-white bg-white/80 p-2"
                            >
                              <div className="flex items-start gap-2">
                                <input
                                  id={checkId}
                                  type="checkbox"
                                  className="mt-1"
                                  checked={checked}
                                  onChange={() => toggleSlotCard(slot.key, card.id)}
                                />
                                <label htmlFor={checkId} className="min-w-0 flex-1 cursor-pointer">
                                  <span className="block text-sm font-semibold text-bordo-deep">
                                    {card.titulo}
                                  </span>
                                  {card.objetivo ? (
                                    <span className="mt-0.5 block text-[11px] text-bordo-soft">
                                      {card.objetivo}
                                    </span>
                                  ) : null}
                                </label>
                              </div>
                              {checked ? (
                                <div
                                  className="mt-2 pl-6"
                                  onMouseDown={(e) => e.stopPropagation()}
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <label
                                    htmlFor={escopoId}
                                    className="text-[10px] font-bold uppercase text-bordo-soft"
                                  >
                                    O que esta turma realiza neste card
                                  </label>
                                  <textarea
                                    id={escopoId}
                                    className="field-input mt-1 !py-2 text-sm"
                                    rows={2}
                                    value={slot.escopos?.[card.id] || ''}
                                    onChange={(e) =>
                                      updateSlotEscopo(slot.key, card.id, e.target.value)
                                    }
                                    placeholder="Ex.: turma A faz o diagnóstico em campo; define entregáveis X e Y…"
                                    required
                                  />
                                </div>
                              ) : null}
                            </li>
                          )
                        })}
                      </ul>
                    )}
                  </div>
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

            {/* Convite multidisciplinar */}
            <div className="mt-5 rounded-xl border border-dashed border-brand-300 bg-white p-3">
              <p className="text-[10px] font-bold uppercase tracking-wide text-brand-700">
                Convidar outro professor
              </p>
              <p className="mt-1 text-[11px] leading-snug text-bordo-soft">
                Projeto multidisciplinar: o convidado recebe por e-mail a descrição do desafio e do
                card. Com um clique o desafio entra no mapa dele; cada um planeja as próprias aulas
                sem ver o planejamento do outro. Identificação do convidado = e-mail.
              </p>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label className="text-[10px] font-bold uppercase text-bordo-soft">
                    E-mail do professor convidado
                  </label>
                  <input
                    type="email"
                    className="field-input mt-1 !py-2"
                    value={conviteEmail}
                    onChange={(e) => setConviteEmail(e.target.value)}
                    placeholder="professor@escola.edu.br"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="text-[10px] font-bold uppercase text-bordo-soft">
                    Card que ele vai realizar
                  </label>
                  <select
                    className="field-input mt-1 !py-2"
                    value={conviteCardId}
                    onChange={(e) => setConviteCardId(e.target.value)}
                  >
                    <option value="">Selecione um card…</option>
                    {cardsCatalogo.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.titulo}
                      </option>
                    ))}
                  </select>
                  {conviteCardId ? (
                    <p className="mt-1.5 rounded-lg bg-brand-50 px-2 py-1.5 text-[11px] text-bordo">
                      <strong>Prévia do e-mail — Card:</strong>{' '}
                      {cardsCatalogo.find((c) => c.id === conviteCardId)?.titulo}
                      {cardsCatalogo.find((c) => c.id === conviteCardId)?.objetivo
                        ? ` — ${cardsCatalogo.find((c) => c.id === conviteCardId).objetivo}`
                        : ''}
                    </p>
                  ) : null}
                </div>
              </div>
              {desafioIdAtivo ? (
                <button
                  type="button"
                  className="btn-ghost mt-3 w-full !py-2 text-xs"
                  disabled={conviteBusy || registroBusy}
                  onClick={handleEnviarConviteAvulso}
                >
                  {conviteBusy ? 'Enviando convite…' : 'Enviar só o convite agora'}
                </button>
              ) : (
                <p className="mt-2 text-[11px] text-bordo-soft">
                  Quando o desafio estiver salvo (ou ao registrar as aulas), o convite pode ser
                  enviado.
                </p>
              )}
              {conviteErro ? (
                <p className="mt-2 text-xs font-semibold text-rose-700">{conviteErro}</p>
              ) : null}
              {conviteMsg ? (
                <p className="mt-2 break-all text-xs font-semibold text-emerald-800">{conviteMsg}</p>
              ) : null}
            </div>

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
            </div>,
            document.body,
          )
        : null}
    </section>
  )
}
