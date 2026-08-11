import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../lib/api'
import { listarInstituicoes, listarPeriodos } from '../services/instituicoesService'

/** Accent único do app (brand-600) — cápsulas e setas. */
const ACCENT = '#e11d48'
const ACCENT_SOFT = 'rgba(225, 29, 72, 0.08)'
const ACCENT_BORDER = 'rgba(225, 29, 72, 0.45)'
const NEUTRAL_CARD = '#f8fafc'
const NEUTRAL_BORDER = '#e2e8f0'
const PAST_CARD = '#ecfdf5'
const PAST_BORDER = '#6ee7b7'
const PAST_ACCENT = '#059669'
const TRACK_NONE = '__none__'

const LABEL_W = 168
const BRACKET_W = 36
const TRACK_H = 78
const PAD_TOP = 36
const PAD_BOTTOM = 24
const CARD_W = 112
const CARD_H = 44

function diaISO(iso) {
  return String(iso || '').slice(0, 10)
}

function parseDate(iso) {
  const s = diaISO(iso)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function formatDia(iso) {
  const p = diaISO(iso).split('-')
  if (p.length !== 3) return ''
  return `${p[2]}/${p[1]}`
}

function daysBetween(a, b) {
  return Math.round((b - a) / 86400000)
}

function addDays(d, n) {
  const x = new Date(d)
  x.setDate(x.getDate() + n)
  return x
}

function pad2(n) {
  return n < 10 ? `0${n}` : String(n)
}

function startOfWeekMonday(d) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const day = x.getDay() // 0=dom
  const diff = day === 0 ? -6 : 1 - day
  x.setDate(x.getDate() + diff)
  return x
}

/** Semanas (seg–dom) que intersectam o mês civil. */
function weeksOverlappingMonth(year, month) {
  const first = new Date(year, month, 1)
  const last = new Date(year, month + 1, 0)
  let cur = startOfWeekMonday(first)
  const weeks = []
  while (cur <= last) {
    const end = addDays(cur, 6)
    const inMonthStart = cur < first ? first : cur
    const inMonthEnd = end > last ? last : end
    weeks.push({
      start: new Date(cur),
      end,
      bandStart: inMonthStart,
      bandEnd: inMonthEnd,
      label: `Sem ${weeks.length + 1}`,
      sublabel: `${pad2(inMonthStart.getDate())}/${pad2(inMonthStart.getMonth() + 1)}–${pad2(inMonthEnd.getDate())}/${pad2(inMonthEnd.getMonth() + 1)}`,
    })
    cur = addDays(cur, 7)
    if (weeks.length >= 6) break
  }
  return weeks
}

const DIAS_UTEIS = [
  { key: 'seg', label: 'Seg', offset: 0 },
  { key: 'ter', label: 'Ter', offset: 1 },
  { key: 'qua', label: 'Qua', offset: 2 },
  { key: 'qui', label: 'Qui', offset: 3 },
  { key: 'sex', label: 'Sex', offset: 4 },
]

function connectedComponents(nodes, edges) {
  const ids = nodes.map((n) => n.id)
  const parent = Object.fromEntries(ids.map((id) => [id, id]))
  function find(x) {
    if (parent[x] !== x) parent[x] = find(parent[x])
    return parent[x]
  }
  function uni(a, b) {
    const ra = find(a)
    const rb = find(b)
    if (ra !== rb) parent[rb] = ra
  }
  edges.forEach((e) => {
    if (parent[e.from] != null && parent[e.to] != null) uni(e.from, e.to)
  })
  const groups = {}
  ids.forEach((id) => {
    const r = find(id)
    if (!groups[r]) groups[r] = []
    groups[r].push(id)
  })
  return Object.values(groups)
}

/**
 * Mapa de planejamento — trilhas por disciplina × tempo.
 * Clique no nó/cápsula: modal editável local (título, data, notas).
 */
export default function MapaRealizacoes({ refreshKey = 0, onSelectNode, onChanged }) {
  const [periodos, setPeriodos] = useState([])
  const [periodoId, setPeriodoId] = useState('')
  const [periodosLoaded, setPeriodosLoaded] = useState(false)
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [periodoMeta, setPeriodoMeta] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [granularity, setGranularity] = useState('mes') // semana | mes
  /** Âncora da janela visível (mês civil ou semana). */
  const [viewAnchor, setViewAnchor] = useState(() => new Date())
  const viewAnchorSeededRef = useRef(false)
  const [editModal, setEditModal] = useState(null)
  const [editSaving, setEditSaving] = useState(false)
  const [editError, setEditError] = useState('')

  const loadPeriodos = useCallback(async () => {
    try {
      const instData = await listarInstituicoes()
      const insts = Array.isArray(instData?.instituicoes) ? instData.instituicoes : []
      const list = []
      for (const inst of insts) {
        try {
          const pd = await listarPeriodos(inst.id)
          const pers = Array.isArray(pd?.periodos) ? pd.periodos : []
          for (const p of pers) {
            list.push({
              id: p.id,
              rotulo: p.rotulo,
              ano_letivo: p.ano_letivo,
              em_curso: Boolean(p.em_curso),
              data_inicio: p.data_inicio,
              data_fim: p.data_fim,
              instituicao_id: inst.id,
              instituicao_nome: inst.nome,
              label: `${inst.nome} · ${p.rotulo || p.ano_letivo || p.id}`,
            })
          }
        } catch {
          /* ignore */
        }
      }
      list.sort((a, b) => {
        if (a.em_curso !== b.em_curso) return a.em_curso ? -1 : 1
        return String(a.label).localeCompare(String(b.label), 'pt-BR')
      })
      setPeriodos(list)
      // Default: Todos (mostra também desafios sem disciplina em qualquer data).
      // Usuário pode filtrar por período em curso se quiser.
      setPeriodoId('')
    } catch {
      setPeriodos([])
      setPeriodoId('')
    } finally {
      setPeriodosLoaded(true)
    }
  }, [])

  useEffect(() => {
    void loadPeriodos()
  }, [loadPeriodos, refreshKey])

  const loadGrafo = useCallback(async () => {
    if (!periodosLoaded) return
    setLoading(true)
    setError('')
    try {
      const data = await api.grafoAgenda(periodoId || undefined)
      setNodes(data.nodes || [])
      setEdges(data.edges || [])
      setPeriodoMeta(data.periodo || null)
    } catch (err) {
      setError(err.message || 'Falha ao carregar o mapa')
      setNodes([])
      setEdges([])
      setPeriodoMeta(null)
    } finally {
      setLoading(false)
    }
  }, [periodoId, periodosLoaded])

  useEffect(() => {
    void loadGrafo()
  }, [loadGrafo, refreshKey])

  // Semeia a âncora uma vez com as aulas (navegação ‹ › do usuário prevalece depois).
  useEffect(() => {
    if (viewAnchorSeededRef.current) return
    const dates = nodes.map((n) => parseDate(n.data || n.data_evento)).filter(Boolean)
    if (!dates.length) return
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const hasTodayMonth = dates.some(
      (d) => d.getFullYear() === today.getFullYear() && d.getMonth() === today.getMonth(),
    )
    setViewAnchor(hasTodayMonth ? today : new Date(Math.max(...dates.map((d) => d.getTime()))))
    viewAnchorSeededRef.current = true
  }, [nodes])

  useEffect(() => {
    viewAnchorSeededRef.current = false
  }, [refreshKey])

  const layout = useMemo(() => {
    const anchor = viewAnchor instanceof Date ? viewAnchor : new Date()
    let bands = []
    let windowLabel = ''
    let rangeStart
    let rangeEnd

    if (granularity === 'mes') {
      const y = anchor.getFullYear()
      const m = anchor.getMonth()
      bands = weeksOverlappingMonth(y, m).map((w, i) => ({
        ...w,
        label: w.label || `Sem ${i + 1}`,
      }))
      rangeStart = new Date(y, m, 1)
      rangeEnd = new Date(y, m + 1, 0)
      windowLabel = anchor.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
    } else {
      const monday = startOfWeekMonday(anchor)
      const friday = addDays(monday, 4)
      const sunday = addDays(monday, 6)
      rangeStart = monday
      rangeEnd = sunday
      bands = DIAS_UTEIS.map((d) => {
        const day = addDays(monday, d.offset)
        return {
          start: day,
          end: day,
          bandStart: day,
          bandEnd: day,
          label: d.label,
          sublabel: `${pad2(day.getDate())}/${pad2(day.getMonth() + 1)}`,
          weekdayOffset: d.offset,
        }
      })
      windowLabel = `${pad2(monday.getDate())}/${pad2(monday.getMonth() + 1)} – ${pad2(friday.getDate())}/${pad2(friday.getMonth() + 1)}`
    }

    const bandCount = Math.max(1, bands.length)
    const bandW = Math.max(granularity === 'semana' ? 120 : 130, CARD_W + 28)
    const timelineW = Math.max(480, bandCount * bandW)

    const inWindow = (d) => {
      if (!d) return false
      if (granularity === 'mes') {
        return (
          d.getFullYear() === rangeStart.getFullYear() &&
          d.getMonth() === rangeStart.getMonth()
        )
      }
      return d >= rangeStart && d <= rangeEnd
    }

    const bandIndexForDate = (d) => {
      if (!d) return -1
      if (granularity === 'mes') {
        return bands.findIndex((b) => d >= b.start && d <= b.end)
      }
      let offset = daysBetween(rangeStart, d)
      if (offset < 0) return -1
      if (offset > 4) offset = 4 // sáb/dom → sexta
      return offset
    }

    const trackKey = (n) =>
      n.disciplina_id != null && n.disciplina_id !== ''
        ? `d:${n.disciplina_id}`
        : TRACK_NONE

    const trackMap = new Map()
    const nodesInView = []
    let nodesOutOfView = 0
    nodes.forEach((n) => {
      const d = parseDate(n.data || n.data_evento)
      if (!inWindow(d)) {
        nodesOutOfView += 1
        return
      }
      nodesInView.push(n)
      const key = trackKey(n)
      if (!trackMap.has(key)) {
        trackMap.set(key, {
          key,
          disciplina_id: n.disciplina_id ?? null,
          nome:
            key === TRACK_NONE
              ? 'Sem disciplina vinculada'
              : n.nome_disciplina || `Disciplina ${n.disciplina_id}`,
          instituicao_id: n.instituicao_id ?? null,
          nome_instituicao: n.nome_instituicao || null,
          nodes: [],
        })
      }
      trackMap.get(key).nodes.push(n)
    })
    if (!trackMap.has(TRACK_NONE)) {
      trackMap.set(TRACK_NONE, {
        key: TRACK_NONE,
        disciplina_id: null,
        nome: 'Sem disciplina vinculada',
        instituicao_id: null,
        nome_instituicao: null,
        nodes: [],
      })
    }

    const tracks = Array.from(trackMap.values()).sort((a, b) => {
      if (a.key === TRACK_NONE) return -1
      if (b.key === TRACK_NONE) return 1
      const ia = a.nome_instituicao || ''
      const ib = b.nome_instituicao || ''
      if (ia !== ib) return ia.localeCompare(ib, 'pt-BR')
      return a.nome.localeCompare(b.nome, 'pt-BR')
    })

    const instIds = new Set(
      tracks.filter((t) => t.key !== TRACK_NONE && t.instituicao_id != null).map((t) => t.instituicao_id),
    )
    const showBrackets = instIds.size >= 2
    const leftW = LABEL_W + (showBrackets ? BRACKET_W : 0)

    // Agrupa por trilha+faixa para espalhar cartões na mesma célula
    const slotCounts = new Map()
    const slotIndex = new Map()
    nodesInView.forEach((n) => {
      const d = parseDate(n.data || n.data_evento)
      const bi = bandIndexForDate(d)
      if (bi < 0) return
      const key = `${trackKey(n)}|${bi}`
      const idx = slotCounts.get(key) || 0
      slotCounts.set(key, idx + 1)
      slotIndex.set(n.id, idx)
    })

    const placed = []
    tracks.forEach((t, ti) => {
      const yBase = PAD_TOP + ti * TRACK_H + TRACK_H / 2
      t.nodes.forEach((n) => {
        const d = parseDate(n.data || n.data_evento)
        const bi = bandIndexForDate(d)
        if (bi < 0) return
        const key = `${t.key}|${bi}`
        const total = slotCounts.get(key) || 1
        const idx = slotIndex.get(n.id) || 0
        const bandCenter = bi * bandW + bandW / 2
        const stagger = (idx - (total - 1) / 2) * Math.min(36, (bandW - CARD_W) / Math.max(1, total))
        placed.push({
          ...n,
          trackKey: t.key,
          bandIndex: bi,
          x: bandCenter + stagger,
          y: yBase,
        })
      })
    })
    const placedById = Object.fromEntries(placed.map((p) => [p.id, p]))

    const comps = connectedComponents(nodesInView, edges)
    const capsules = []
    const crossEdges = []
    comps.forEach((ids) => {
      if (ids.length < 2) return
      const members = ids.map((id) => placedById[id]).filter(Boolean)
      if (members.length < 2) return
      const discKeys = new Set(members.map((m) => m.trackKey))
      const sameTrack = discKeys.size === 1
      const internal = edges.filter((e) => ids.includes(e.from) && ids.includes(e.to))
      if (!sameTrack) {
        internal.forEach((e) => crossEdges.push(e))
        return
      }
      const xs = members.map((m) => m.x)
      const ys = members.map((m) => m.y)
      const minX = Math.min(...xs) - CARD_W / 2 - 10
      const maxX = Math.max(...xs) + CARD_W / 2 + 10
      const minY = Math.min(...ys) - CARD_H / 2 - 14
      const maxY = Math.max(...ys) + CARD_H / 2 + 10
      const roots = members.filter((m) => !m.id_evento_pai || !ids.includes(m.id_evento_pai))
      const root = roots.sort(
        (a, b) => (parseDate(a.data || a.data_evento) || 0) - (parseDate(b.data || b.data_evento) || 0),
      )[0]
      const label =
        (root?.tema && String(root.tema).trim()) ||
        (root?.titulo && String(root.titulo).trim()) ||
        'Sequência'
      capsules.push({
        key: ids.sort().join('-'),
        rootId: root?.id ?? null,
        root,
        memberIds: ids,
        x: minX,
        y: minY,
        w: Math.max(CARD_W + 20, maxX - minX),
        h: Math.max(CARD_H + 24, maxY - minY),
        label: label.slice(0, 42),
        edges: internal,
      })
    })

    // Todas as aulas da sequência aparecem como cartão (incluindo a 1ª / tema).
    const hiddenCardIds = new Set()

    const brackets = []
    if (showBrackets) {
      const byInst = {}
      tracks.forEach((t, ti) => {
        if (t.key === TRACK_NONE || t.instituicao_id == null) return
        const k = String(t.instituicao_id)
        if (!byInst[k]) {
          byInst[k] = { id: t.instituicao_id, nome: t.nome_instituicao || 'Instituição', indices: [] }
        }
        byInst[k].indices.push(ti)
      })
      Object.values(byInst).forEach((b) => {
        const i0 = Math.min(...b.indices)
        const i1 = Math.max(...b.indices)
        brackets.push({
          id: b.id,
          nome: b.nome,
          y0: PAD_TOP + i0 * TRACK_H + 8,
          y1: PAD_TOP + (i1 + 1) * TRACK_H - 8,
        })
      })
    }

    const ticks = bands.map((b, i) => ({
      x: i * bandW + bandW / 2,
      label: b.label,
      sublabel: b.sublabel || '',
      x0: i * bandW,
      x1: (i + 1) * bandW,
    }))

    const height = PAD_TOP + tracks.length * TRACK_H + PAD_BOTTOM
    const visibleCards = placed

    return {
      tracks,
      placed,
      placedById,
      visibleCards,
      hiddenCardIds,
      capsules,
      crossEdges,
      brackets,
      showBrackets,
      leftW,
      timelineW,
      height,
      ticks,
      bands,
      bandW,
      rangeStart,
      rangeEnd,
      windowLabel,
      nodesInView: nodesInView.length,
      nodesOutOfView,
      bandCount,
    }
  }, [nodes, edges, granularity, viewAnchor])

  function shiftView(delta) {
    setViewAnchor((prev) => {
      const base = prev instanceof Date ? prev : new Date()
      if (granularity === 'mes') {
        return new Date(base.getFullYear(), base.getMonth() + delta, 1)
      }
      return addDays(startOfWeekMonday(base), delta * 7)
    })
  }

  async function openEditModal(n, { asTema = false } = {}) {
    if (!n?.id && !n?.id_evento) return
    const id = n.id ?? n.id_evento
    setSelectedId(id)
    setEditError('')
    setEditModal({
      id_evento: id,
      titulo: n.titulo || '',
      data_evento: diaISO(n.data || n.data_evento),
      nota_texto: n.nota_texto || '',
      asTema,
      loading: true,
    })
    try {
      const data = await api.getAgendaEvento(id)
      const ev = data?.evento || data
      if (!ev) throw new Error('Evento não encontrado')
      setEditModal({
        id_evento: ev.id_evento ?? id,
        titulo: ev.titulo || '',
        data_evento: diaISO(ev.data_evento),
        nota_texto: ev.nota_texto || '',
        asTema,
        loading: false,
      })
    } catch (err) {
      setEditModal((m) => (m ? { ...m, loading: false } : null))
      setEditError(err?.message || 'Não foi possível carregar o evento.')
    }
  }

  function handleSelectNode(n, opts = {}) {
    void openEditModal(n, { asTema: Boolean(opts.asTema) })
    // Só destaca o dia na agenda; não abre o fluxo de navegação/execução.
    onSelectNode?.(n, { ...opts, preferEditModal: true, skipNavigate: true })
  }

  function handleCapsuleClick(c, e) {
    e?.stopPropagation?.()
    if (!c.root) return
    handleSelectNode(c.root, { asTema: true })
  }

  async function saveEditModal(e) {
    e.preventDefault()
    if (!editModal?.id_evento || editModal.loading) return
    const titulo = (editModal.titulo || '').trim()
    if (!titulo) {
      setEditError('Informe o título.')
      return
    }
    if (!editModal.data_evento) {
      setEditError('Informe a data.')
      return
    }
    setEditSaving(true)
    setEditError('')
    try {
      await api.updateAgendaEvento(editModal.id_evento, {
        titulo,
        data_evento: `${editModal.data_evento}T12:00:00`,
        nota_texto: (editModal.nota_texto || '').trim(),
      })
      setEditModal(null)
      await loadGrafo()
      onChanged?.()
    } catch (err) {
      setEditError(err?.message || 'Falha ao salvar.')
    } finally {
      setEditSaving(false)
    }
  }

  const showPeriodoSelect = periodos.length > 0

  return (
    <section className="mx-auto mb-6 max-w-6xl animate-fade-in print:hidden">
      <div className="rounded-2xl border border-brand-200 bg-white p-4 shadow-soft sm:p-5">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
              Planejamento
            </p>
            <h2 className="font-display text-xl font-bold text-bordo-deep sm:text-2xl">
              Grafo do período
            </h2>
            <p className="mt-1 max-w-xl text-xs text-bordo-soft">
              Em mês, o grafo divide em semanas; em semana, em dias úteis (seg–sex). Cada aula
              cai na faixa da sua data. Clique no cartão para editar.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {showPeriodoSelect ? (
              <label className="flex flex-col gap-0.5 text-[10px] font-semibold uppercase tracking-wide text-bordo-soft">
                Período letivo
                <select
                  className="field-input min-h-9 !py-1.5 text-sm font-normal normal-case"
                  value={periodoId}
                  onChange={(e) => setPeriodoId(e.target.value)}
                >
                  <option value="">Todos os períodos</option>
                  {periodos.map((p) => (
                    <option key={p.id} value={String(p.id)}>
                      {p.em_curso ? '● ' : ''}
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <div className="flex items-center gap-1">
              <button
                type="button"
                className="rounded-lg border border-brand-100 bg-white px-2.5 py-1.5 text-xs font-bold text-bordo shadow-sm hover:bg-brand-50"
                onClick={() => shiftView(-1)}
                aria-label={granularity === 'mes' ? 'Mês anterior' : 'Semana anterior'}
              >
                ‹
              </button>
              <div className="flex rounded-lg border border-brand-100 p-0.5 text-[11px] font-semibold">
                <button
                  type="button"
                  className={`rounded-md px-2.5 py-1.5 ${
                    granularity === 'semana' ? 'bg-brand-50 text-bordo' : 'text-bordo-soft'
                  }`}
                  onClick={() => setGranularity('semana')}
                >
                  Semana
                </button>
                <button
                  type="button"
                  className={`rounded-md px-2.5 py-1.5 ${
                    granularity === 'mes' ? 'bg-brand-50 text-bordo' : 'text-bordo-soft'
                  }`}
                  onClick={() => setGranularity('mes')}
                >
                  Mês
                </button>
              </div>
              <button
                type="button"
                className="rounded-lg border border-brand-100 bg-white px-2.5 py-1.5 text-xs font-bold text-bordo shadow-sm hover:bg-brand-50"
                onClick={() => shiftView(1)}
                aria-label={granularity === 'mes' ? 'Próximo mês' : 'Próxima semana'}
              >
                ›
              </button>
            </div>
          </div>
        </div>

        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
          <p>
            {granularity === 'mes'
              ? 'Faixas = semanas do mês · cartões = todas as aulas (inclui a 1ª da sequência)'
              : 'Faixas = seg–sex · cada aula na coluna do dia'}
          </p>
          <p className="font-semibold capitalize text-bordo-soft">
            {layout.windowLabel || '—'}
            {layout.nodesOutOfView > 0
              ? ` · ${layout.nodesOutOfView} fora desta vista`
              : ''}
          </p>
        </div>

        {loading ? (
          <p className="py-10 text-center text-sm text-bordo-soft">Carregando mapa…</p>
        ) : error ? (
          <p className="rounded-lg bg-brand-50 px-3 py-2 text-xs font-semibold text-bordo">{error}</p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-slate-50/80">
            <div className="flex max-h-[min(70vh,560px)]">
              {/* Labels sticky */}
              <div
                className="sticky left-0 z-10 shrink-0 border-r border-slate-200 bg-white"
                style={{ width: layout.leftW }}
              >
                <svg width={layout.leftW} height={layout.height} className="block">
                  {layout.showBrackets
                    ? layout.brackets.map((b) => (
                        <g key={b.id}>
                          <path
                            d={`M ${BRACKET_W - 8} ${b.y0} L 10 ${b.y0} L 10 ${b.y1} L ${BRACKET_W - 8} ${b.y1}`}
                            fill="none"
                            stroke="#94a3b8"
                            strokeWidth="1.5"
                          />
                          <text
                            x={6}
                            y={(b.y0 + b.y1) / 2}
                            transform={`rotate(-90 6 ${(b.y0 + b.y1) / 2})`}
                            textAnchor="middle"
                            style={{ fontSize: 10, fill: '#64748b', fontWeight: 600 }}
                          >
                            {(b.nome || '').slice(0, 28)}
                          </text>
                        </g>
                      ))
                    : null}
                  {layout.tracks.map((t, ti) => {
                    const y = PAD_TOP + ti * TRACK_H + TRACK_H / 2
                    const x = layout.showBrackets ? BRACKET_W + 8 : 10
                    return (
                      <text
                        key={t.key}
                        x={x}
                        y={y + 4}
                        style={{
                          fontSize: 11,
                          fontWeight: t.key === TRACK_NONE ? 500 : 700,
                          fill: t.key === TRACK_NONE ? '#64748b' : '#7f1d1d',
                        }}
                      >
                        {(t.nome || '').slice(0, 22)}
                        {(t.nome || '').length > 22 ? '…' : ''}
                      </text>
                    )
                  })}
                </svg>
              </div>

              {/* Timeline scrollable */}
              <div className="min-w-0 flex-1 overflow-x-auto overflow-y-auto">
                <svg
                  width={layout.timelineW}
                  height={layout.height}
                  className="block"
                  role="img"
                  aria-label="Grafo de planejamento por disciplina e tempo"
                >
                  {/* track lanes */}
                  {layout.tracks.map((t, ti) => (
                    <rect
                      key={`lane-${t.key}`}
                      x={0}
                      y={PAD_TOP + ti * TRACK_H}
                      width={layout.timelineW}
                      height={TRACK_H}
                      fill={ti % 2 === 0 ? '#ffffff' : '#f8fafc'}
                    />
                  ))}
                  {/* faixas (semanas ou dias) */}
                  {layout.ticks.map((tk, i) => (
                    <g key={`band-${i}`}>
                      <rect
                        x={tk.x0}
                        y={PAD_TOP - 28}
                        width={Math.max(1, (tk.x1 ?? tk.x) - (tk.x0 ?? tk.x))}
                        height={layout.height - PAD_TOP + 28 - PAD_BOTTOM + 4}
                        fill={i % 2 === 0 ? 'rgba(225, 29, 72, 0.03)' : 'transparent'}
                        pointerEvents="none"
                      />
                      <line
                        x1={tk.x0}
                        y1={PAD_TOP - 28}
                        x2={tk.x0}
                        y2={layout.height - PAD_BOTTOM + 4}
                        stroke="#e2e8f0"
                        strokeWidth="1"
                      />
                      <text
                        x={tk.x}
                        y={PAD_TOP - 16}
                        textAnchor="middle"
                        style={{ fontSize: 10, fill: '#7f1d1d', fontWeight: 700 }}
                      >
                        {tk.label}
                      </text>
                      {tk.sublabel ? (
                        <text
                          x={tk.x}
                          y={PAD_TOP - 4}
                          textAnchor="middle"
                          style={{ fontSize: 8, fill: '#94a3b8', fontWeight: 600 }}
                        >
                          {tk.sublabel}
                        </text>
                      ) : null}
                    </g>
                  ))}

                  {/* capsules — clique na área pontilhada abre o evento pai (tema) */}
                  {layout.capsules.map((c) => (
                    <g key={c.key}>
                      <rect
                        x={c.x}
                        y={c.y}
                        width={c.w}
                        height={c.h}
                        rx={12}
                        ry={12}
                        fill={ACCENT_SOFT}
                        stroke={ACCENT_BORDER}
                        strokeWidth="1.5"
                        strokeDasharray="5 4"
                        className="cursor-pointer"
                        role="button"
                        aria-label={`Tema: ${c.label}`}
                        onClick={(e) => handleCapsuleClick(c, e)}
                      />
                      <text
                        x={c.x + 10}
                        y={c.y - 4}
                        style={{ fontSize: 10, fontWeight: 700, fill: ACCENT, cursor: 'pointer' }}
                        onClick={(e) => handleCapsuleClick(c, e)}
                      >
                        {c.label}
                      </text>
                      {c.edges.map((e) => {
                        const a = layout.placedById[e.from]
                        const b = layout.placedById[e.to]
                        if (!a || !b) return null
                        return (
                          <line
                            key={`${e.from}-${e.to}`}
                            x1={a.x + CARD_W / 2 - 4}
                            y1={a.y}
                            x2={b.x - CARD_W / 2 + 4}
                            y2={b.y}
                            stroke={ACCENT}
                            strokeWidth="1.75"
                            strokeOpacity="0.7"
                            markerEnd="url(#arrow-grafo-accent)"
                            pointerEvents="none"
                          />
                        )
                      })}
                    </g>
                  ))}

                  {/* cross-track edges */}
                  {layout.crossEdges.map((e) => {
                    const a = layout.placedById[e.from]
                    const b = layout.placedById[e.to]
                    if (!a || !b) return null
                    return (
                      <line
                        key={`x-${e.from}-${e.to}`}
                        x1={a.x}
                        y1={a.y + CARD_H / 2}
                        x2={b.x}
                        y2={b.y - CARD_H / 2}
                        stroke={ACCENT}
                        strokeWidth="1.5"
                        strokeOpacity="0.55"
                        markerEnd="url(#arrow-grafo-accent)"
                      />
                    )
                  })}

                  <defs>
                    <marker
                      id="arrow-grafo-accent"
                      markerWidth="7"
                      markerHeight="7"
                      refX="6"
                      refY="3"
                      orient="auto"
                    >
                      <path d="M0,0 L7,3 L0,6 Z" fill={ACCENT} opacity="0.75" />
                    </marker>
                  </defs>

                  {/* cards (aulas) — todas as aulas da sequência, inclusive a 1ª */}
                  {layout.visibleCards.map((n) => {
                    const active = selectedId === n.id
                    const passado = n.status === 'concluido' || n.no_passado || n.cards_prontos
                    return (
                      <g
                        key={n.id}
                        transform={`translate(${n.x - CARD_W / 2}, ${n.y - CARD_H / 2})`}
                        className="cursor-pointer"
                        role="button"
                        tabIndex={0}
                        aria-label={`${n.titulo || 'Evento'} — ${formatDia(n.data || n.data_evento)}${
                          passado ? ' — realizada (passado)' : ''
                        }`}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleSelectNode(n, { preferEditModal: true })
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            e.stopPropagation()
                            handleSelectNode(n, { preferEditModal: true })
                          }
                        }}
                      >
                        <title>
                          {`${n.titulo}\n${formatDia(n.data || n.data_evento)}${
                            passado ? '\nRealizada — no passado' : ''
                          }`}
                        </title>
                        <rect
                          width={CARD_W}
                          height={CARD_H}
                          rx={8}
                          ry={8}
                          fill={passado ? PAST_CARD : NEUTRAL_CARD}
                          stroke={active ? ACCENT : passado ? PAST_BORDER : NEUTRAL_BORDER}
                          strokeWidth={active ? 2 : 1}
                          opacity={passado ? 0.88 : 1}
                        />
                        <rect
                          x={0}
                          y={0}
                          width={3}
                          height={CARD_H}
                          rx={2}
                          fill={passado ? PAST_ACCENT : ACCENT}
                          opacity={passado ? 0.85 : 0.35}
                        />
                        <text
                          x={10}
                          y={18}
                          style={{
                            fontSize: 10,
                            fontWeight: 700,
                            fill: passado ? '#064e3b' : '#450a0a',
                          }}
                        >
                          {(n.titulo || 'Evento').slice(0, 16)}
                          {(n.titulo || '').length > 16 ? '…' : ''}
                        </text>
                        <text
                          x={10}
                          y={34}
                          style={{
                            fontSize: 9,
                            fill: passado ? PAST_ACCENT : '#64748b',
                            fontWeight: 600,
                          }}
                        >
                          {passado
                            ? `✓ ${formatDia(n.data || n.data_evento)}`
                            : formatDia(n.data || n.data_evento)}
                        </text>
                      </g>
                    )
                  })}
                </svg>
              </div>
            </div>
            {!nodes.length ? (
              <p className="border-t border-slate-200 px-4 py-6 text-center text-sm text-bordo-soft">
                Nenhum evento neste período. Importe aulas ou planeje no Dia a Dia / Agenda.
              </p>
            ) : null}
          </div>
        )}
      </div>

      {editModal ? (
        <div
          className="fixed inset-0 z-[80] flex items-end justify-center bg-bordo-deep/45 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          onClick={(ev) => {
            if (ev.target === ev.currentTarget && !editSaving) setEditModal(null)
          }}
        >
          <form
            onSubmit={(ev) => void saveEditModal(ev)}
            className="w-full max-w-md rounded-2xl border border-brand-200 bg-white p-5 shadow-soft"
          >
            <h3 className="font-display text-lg font-bold text-bordo-deep">
              {editModal.asTema ? 'Editar tema da sequência' : 'Editar evento'}
            </h3>
            {editModal.asTema ? (
              <p className="mt-1 text-xs text-bordo-soft">
                Tema (pai) da sequência no grafo — também listado nos compromissos do dia.
              </p>
            ) : null}

            {editModal.loading ? (
              <p className="mt-6 text-sm text-bordo-soft">Carregando…</p>
            ) : (
              <>
                <label className="mt-4 block text-xs font-bold uppercase tracking-wide text-bordo">
                  Título
                </label>
                <input
                  type="text"
                  className="field-input mt-1 text-base font-semibold"
                  value={editModal.titulo}
                  onChange={(ev) =>
                    setEditModal((m) => (m ? { ...m, titulo: ev.target.value } : m))
                  }
                  placeholder="Título do tema ou da aula"
                  required
                  autoFocus
                  maxLength={200}
                  disabled={editSaving}
                />

                <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-bordo">
                  Data
                </label>
                <input
                  type="date"
                  className="field-input mt-1"
                  value={editModal.data_evento}
                  onChange={(ev) =>
                    setEditModal((m) => (m ? { ...m, data_evento: ev.target.value } : m))
                  }
                  required
                  disabled={editSaving}
                />

                <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-bordo">
                  Notas / detalhes
                </label>
                <textarea
                  className="field-input mt-1 min-h-[100px] resize-y"
                  rows={4}
                  value={editModal.nota_texto}
                  onChange={(ev) =>
                    setEditModal((m) => (m ? { ...m, nota_texto: ev.target.value } : m))
                  }
                  placeholder="Observações do compromisso…"
                  disabled={editSaving}
                />
              </>
            )}

            {editError ? (
              <p className="mt-2 text-xs font-semibold text-brand-700">{editError}</p>
            ) : null}

            <div className="mt-5 flex flex-wrap justify-end gap-2">
              <button
                type="button"
                className="btn-ghost !px-4 !py-2 text-sm"
                disabled={editSaving}
                onClick={() => setEditModal(null)}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn-primary !px-4 !py-2 text-sm disabled:opacity-60"
                disabled={editSaving || editModal.loading}
              >
                {editSaving ? 'Salvando…' : 'Salvar'}
              </button>
            </div>
          </form>
        </div>
      ) : null}
    </section>
  )
}

/** Mantido para compatibilidade com imports que usavam o helper do mapa antigo. */
export function destinoAtividadeDoNo(n) {
  if (!n) return null
  if (n.tipo === 'aula_dia') {
    const aulaId = n.aula_simples_id || n.meta_json?.aula_simples_id
    if (aulaId) return { path: `/dia-a-dia/${aulaId}#kanban`, label: 'Ir para a mesa do ciclo' }
    return { path: '/dia-a-dia', label: 'Abrir Dia a Dia' }
  }
  if (n.tipo === 'aula_eduscrum' || n.tem_plano) {
    if (n.status === 'concluido') {
      return { path: null, label: 'Aula concluída — veja o dia na agenda', agendaOnly: true }
    }
    return { path: `/execucao/${n.id}`, label: 'Ir para a mesa da aula' }
  }
  return { path: null, label: 'Ver este dia na agenda', agendaOnly: true }
}
