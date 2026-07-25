import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../lib/api'
import { listarInstituicoes, listarPeriodos } from '../services/instituicoesService'

/** Accent único do app (brand-600) — cápsulas e setas. */
const ACCENT = '#e11d48'
const ACCENT_SOFT = 'rgba(225, 29, 72, 0.08)'
const ACCENT_BORDER = 'rgba(225, 29, 72, 0.45)'
const NEUTRAL_CARD = '#f8fafc'
const NEUTRAL_BORDER = '#e2e8f0'
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
      const emCurso = list.find((p) => p.em_curso)
      setPeriodoId(emCurso ? String(emCurso.id) : list[0] ? String(list[0].id) : '')
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

  useEffect(() => {
    if (!periodoMeta?.data_inicio || !periodoMeta?.data_fim) return
    const a = parseDate(periodoMeta.data_inicio)
    const b = parseDate(periodoMeta.data_fim)
    if (!a || !b) return
    const span = daysBetween(a, b)
    setGranularity(span > 45 ? 'mes' : 'semana')
  }, [periodoMeta?.id, periodoMeta?.data_inicio, periodoMeta?.data_fim])

  const layout = useMemo(() => {
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]))

    let rangeStart = periodoMeta ? parseDate(periodoMeta.data_inicio) : null
    let rangeEnd = periodoMeta ? parseDate(periodoMeta.data_fim) : null
    if (!rangeStart || !rangeEnd) {
      const dates = nodes.map((n) => parseDate(n.data || n.data_evento)).filter(Boolean)
      if (dates.length) {
        rangeStart = new Date(Math.min(...dates))
        rangeEnd = new Date(Math.max(...dates))
      } else {
        const now = new Date()
        rangeStart = new Date(now.getFullYear(), now.getMonth(), 1)
        rangeEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0)
      }
    }
    if (rangeEnd < rangeStart) rangeEnd = addDays(rangeStart, 30)
    // margem visual
    const spanDays = Math.max(7, daysBetween(rangeStart, rangeEnd) + 1)
    const pxPerDay = granularity === 'semana' ? 18 : 6
    const timelineW = Math.max(480, spanDays * pxPerDay + CARD_W)

    const trackKey = (n) =>
      n.disciplina_id != null && n.disciplina_id !== ''
        ? `d:${n.disciplina_id}`
        : TRACK_NONE

    const trackMap = new Map()
    nodes.forEach((n) => {
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
    // Sempre mostrar trilha genérica
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
      if (a.key === TRACK_NONE) return 1
      if (b.key === TRACK_NONE) return -1
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

    const xForDate = (iso) => {
      const d = parseDate(iso)
      if (!d) return CARD_W / 2
      const day = Math.max(0, Math.min(spanDays - 1, daysBetween(rangeStart, d)))
      return day * pxPerDay + CARD_W / 2
    }

    const placed = []
    tracks.forEach((t, ti) => {
      const y = PAD_TOP + ti * TRACK_H + TRACK_H / 2
      t.nodes.forEach((n) => {
        placed.push({
          ...n,
          trackKey: t.key,
          x: xForDate(n.data || n.data_evento),
          y,
        })
      })
    })
    const placedById = Object.fromEntries(placed.map((p) => [p.id, p]))

    const comps = connectedComponents(nodes, edges)
    const capsules = []
    const crossEdges = []
    comps.forEach((ids) => {
      if (ids.length < 2) return
      const members = ids.map((id) => placedById[id]).filter(Boolean)
      if (members.length < 2) return
      const discKeys = new Set(members.map((m) => m.trackKey))
      const sameTrack = discKeys.size === 1
      // arestas internas
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
        w: maxX - minX,
        h: maxY - minY,
        label: label.slice(0, 42),
        edges: internal,
      })
    })

    // Pais de cápsula = "tema": não renderizam cartão (só a área pontilhada).
    const hiddenCardIds = new Set(
      capsules.map((c) => c.rootId).filter((id) => id != null),
    )

    // brackets por instituição
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

    // ticks do eixo
    const ticks = []
    if (granularity === 'mes') {
      let cur = new Date(rangeStart.getFullYear(), rangeStart.getMonth(), 1)
      while (cur <= rangeEnd) {
        ticks.push({
          x: xForDate(
            `${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, '0')}-01`,
          ),
          label: cur.toLocaleDateString('pt-BR', { month: 'short', year: '2-digit' }),
        })
        cur = new Date(cur.getFullYear(), cur.getMonth() + 1, 1)
      }
    } else {
      let cur = new Date(rangeStart)
      const dow = cur.getDay()
      cur = addDays(cur, dow === 0 ? 0 : -dow) // domingo
      while (cur <= rangeEnd) {
        const iso = `${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, '0')}-${String(cur.getDate()).padStart(2, '0')}`
        ticks.push({
          x: xForDate(iso),
          label: `${String(cur.getDate()).padStart(2, '0')}/${String(cur.getMonth() + 1).padStart(2, '0')}`,
        })
        cur = addDays(cur, 7)
      }
    }

    const height = PAD_TOP + tracks.length * TRACK_H + PAD_BOTTOM
    const visibleCards = placed.filter((n) => !hiddenCardIds.has(n.id))

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
      rangeStart,
      rangeEnd,
    }
  }, [nodes, edges, periodoMeta, granularity])

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
              Tempo na horizontal · uma trilha por disciplina. Clique num cartão ou na cápsula
              para editar título, data e notas.
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
                  {periodos.map((p) => (
                    <option key={p.id} value={String(p.id)}>
                      {p.em_curso ? '● ' : ''}
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
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
          </div>
        </div>

        <p className="mb-3 text-[11px] text-slate-500">
          Cápsula tracejada = tema (clique na área pontilhada para editar) · cartões = aulas
          da sequência · cartão cinza isolado = aula avulsa
        </p>

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
                  {/* ticks */}
                  {layout.ticks.map((tk, i) => (
                    <g key={`tick-${i}`}>
                      <line
                        x1={tk.x}
                        y1={PAD_TOP - 8}
                        x2={tk.x}
                        y2={layout.height - PAD_BOTTOM + 4}
                        stroke="#e2e8f0"
                        strokeWidth="1"
                      />
                      <text
                        x={tk.x}
                        y={PAD_TOP - 14}
                        textAnchor="middle"
                        style={{ fontSize: 9, fill: '#94a3b8', fontWeight: 600 }}
                      >
                        {tk.label}
                      </text>
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
                        // Se o pai está oculto (tema), seta parte da borda esquerda da cápsula.
                        const fromHidden = layout.hiddenCardIds.has(e.from)
                        const x1 = fromHidden ? c.x + 16 : a.x + CARD_W / 2 - 4
                        const y1 = fromHidden ? a.y : a.y
                        return (
                          <line
                            key={`${e.from}-${e.to}`}
                            x1={x1}
                            y1={y1}
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

                  {/* cards (aulas) — pais de cápsula ficam de fora da lista visual */}
                  {layout.visibleCards.map((n) => {
                    const active = selectedId === n.id
                    return (
                      <g
                        key={n.id}
                        transform={`translate(${n.x - CARD_W / 2}, ${n.y - CARD_H / 2})`}
                        className="cursor-pointer"
                        role="button"
                        tabIndex={0}
                        aria-label={`${n.titulo || 'Evento'} — ${formatDia(n.data || n.data_evento)}`}
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
                        <title>{`${n.titulo}\n${formatDia(n.data || n.data_evento)}`}</title>
                        <rect
                          width={CARD_W}
                          height={CARD_H}
                          rx={8}
                          ry={8}
                          fill={NEUTRAL_CARD}
                          stroke={active ? ACCENT : NEUTRAL_BORDER}
                          strokeWidth={active ? 2 : 1}
                        />
                        <rect
                          x={0}
                          y={0}
                          width={3}
                          height={CARD_H}
                          rx={2}
                          fill={ACCENT}
                          opacity={0.35}
                        />
                        <text
                          x={10}
                          y={18}
                          style={{ fontSize: 10, fontWeight: 700, fill: '#450a0a' }}
                        >
                          {(n.titulo || 'Evento').slice(0, 16)}
                          {(n.titulo || '').length > 16 ? '…' : ''}
                        </text>
                        <text
                          x={10}
                          y={34}
                          style={{ fontSize: 9, fill: '#64748b', fontWeight: 600 }}
                        >
                          {formatDia(n.data || n.data_evento)}
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
                Pai da cadeia no grafo — não aparece na lista de compromissos do dia.
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
    if (aulaId) return { path: `/dia-a-dia/${aulaId}#kanban`, label: 'Ir para o Kanban do ciclo' }
    return { path: '/dia-a-dia', label: 'Abrir Dia a Dia' }
  }
  if (n.tipo === 'aula_eduscrum' || n.tem_plano) {
    if (n.status === 'concluido') {
      return { path: null, label: 'Aula concluída — veja o dia na agenda', agendaOnly: true }
    }
    return { path: `/execucao/${n.id}`, label: 'Ir para o Kanban da aula' }
  }
  return { path: null, label: 'Ver este dia na agenda', agendaOnly: true }
}
