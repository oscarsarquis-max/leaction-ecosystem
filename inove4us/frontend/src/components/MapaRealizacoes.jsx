import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

const STATUS_FILL = {
  planejado: '#fda4af',
  em_execucao: '#fbbf24',
  concluido: '#34d399',
}

const STATUS_LABEL = {
  planejado: 'Planejado',
  em_execucao: 'Em execução',
  concluido: 'Realizado',
}

function formatDia(iso) {
  const p = String(iso || '').slice(0, 10).split('-')
  if (p.length !== 3) return ''
  return `${p[2]}/${p[1]}`
}

function diaISO(iso) {
  return String(iso || '').slice(0, 10)
}

function tipoLabel(tipo) {
  if (tipo === 'aula_eduscrum') return 'Desafio · EduScrum'
  if (tipo === 'aula_dia') return 'Dia a Dia · ciclo rápido'
  return 'Compromisso'
}

/** Destino do Kanban / atividade a partir de um nó do grafo. */
export function destinoAtividadeDoNo(n) {
  if (!n) return null
  if (n.tipo === 'aula_dia') {
    const aulaId = n.aula_simples_id || n.meta_json?.aula_simples_id
    if (aulaId) {
      return {
        path: `/dia-a-dia/${aulaId}#kanban`,
        label: 'Ir para o Kanban do ciclo',
      }
    }
    return { path: '/dia-a-dia', label: 'Abrir Dia a Dia' }
  }
  if (n.tipo === 'aula_eduscrum' || n.tem_plano) {
    if (n.status === 'concluido') {
      return {
        path: null,
        label: 'Aula concluída — veja o dia na agenda',
        agendaOnly: true,
      }
    }
    return {
      path: `/execucao/${n.id}`,
      label: 'Ir para o Kanban da aula',
    }
  }
  return {
    path: null,
    label: 'Ver este dia na agenda',
    agendaOnly: true,
  }
}

/**
 * Mapa estilizado de realizações — nós = eventos, arestas = desdobramentos vinculados.
 * Clique no nó: destaca dias com atividade na agenda + painel de explicação.
 * Do painel: desloca para o Kanban da atividade.
 */
export default function MapaRealizacoes({ refreshKey = 0, onSelectNode }) {
  const navigate = useNavigate()
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.grafoAgenda()
      setNodes(data.nodes || [])
      setEdges(data.edges || [])
    } catch (err) {
      setError(err.message || 'Falha ao carregar realizações')
      setNodes([])
      setEdges([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load, refreshKey])

  const layout = useMemo(() => {
    if (!nodes.length) return { placed: [], width: 640, height: 180 }

    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]))
    const children = {}
    nodes.forEach((n) => {
      const p = n.id_evento_pai
      if (p) {
        if (!children[p]) children[p] = []
        children[p].push(n.id)
      }
    })

    const roots = nodes.filter((n) => !n.id_evento_pai || !byId[n.id_evento_pai])
    const levels = []
    const visited = new Set()
    let frontier = roots.map((n) => n.id)
    while (frontier.length) {
      levels.push(frontier)
      frontier.forEach((id) => visited.add(id))
      const next = []
      frontier.forEach((id) => {
        ;(children[id] || []).forEach((cid) => {
          if (!visited.has(cid)) next.push(cid)
        })
      })
      frontier = next
    }
    nodes.forEach((n) => {
      if (!visited.has(n.id)) {
        if (!levels.length) levels.push([])
        levels[0].push(n.id)
      }
    })

    const colW = 160
    const rowH = 88
    const padX = 48
    const padY = 36
    const width = Math.max(640, padX * 2 + levels.length * colW)
    let maxRows = 1
    levels.forEach((lv) => {
      maxRows = Math.max(maxRows, lv.length)
    })
    const height = Math.max(180, padY * 2 + maxRows * rowH)

    const placed = []
    levels.forEach((lv, col) => {
      const total = lv.length
      lv.forEach((id, row) => {
        const n = byId[id]
        if (!n) return
        const ySpread =
          total === 1 ? height / 2 : padY + ((row + 0.5) * (height - padY * 2)) / total
        placed.push({
          ...n,
          x: padX + col * colW + colW / 2,
          y: ySpread,
        })
      })
    })
    return { placed, width, height, byId: Object.fromEntries(placed.map((p) => [p.id, p])) }
  }, [nodes])

  const edgePaths = useMemo(() => {
    const { byId } = layout
    if (!byId) return []
    return edges
      .map((e) => {
        const a = byId[e.from]
        const b = byId[e.to]
        if (!a || !b) return null
        const mx = (a.x + b.x) / 2
        return {
          key: `${e.from}-${e.to}`,
          d: `M ${a.x} ${a.y} C ${mx} ${a.y}, ${mx} ${b.y}, ${b.x} ${b.y}`,
        }
      })
      .filter(Boolean)
  }, [edges, layout])

  function handleSelectNode(n) {
    setSelected(n)
    onSelectNode?.(n)
  }

  function goToKanban(n) {
    const dest = destinoAtividadeDoNo(n)
    if (!dest) return
    if (dest.path) {
      navigate(dest.path)
      return
    }
    // só agenda: reforça o destaque do dia
    onSelectNode?.(n)
    document.getElementById('agenda-executiva')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const destSelected = selected ? destinoAtividadeDoNo(selected) : null

  return (
    <section className="mx-auto mb-6 max-w-6xl animate-fade-in print:hidden">
      <div className="rounded-2xl border border-brand-200 bg-gradient-to-br from-white via-brand-50/40 to-rose-50/50 p-4 shadow-soft sm:p-5">
        <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
              Realizações
            </p>
            <h2 className="font-display text-xl font-bold text-bordo-deep sm:text-2xl">
              Mapa de eventos
            </h2>
            <p className="mt-1 text-xs text-bordo-soft">
              Clique num nó para marcar na agenda os dias com atividade; na explicação, vá ao Kanban.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 text-[10px] font-bold">
            {Object.entries(STATUS_LABEL).map(([k, label]) => (
              <span
                key={k}
                className="inline-flex items-center gap-1.5 rounded-full bg-white/80 px-2 py-1 text-bordo ring-1 ring-brand-100"
              >
                <span
                  className="h-2.5 w-2.5 rounded-full"
                  style={{ background: STATUS_FILL[k] }}
                />
                {label}
              </span>
            ))}
          </div>
        </div>

        {loading ? (
          <p className="py-10 text-center text-sm text-bordo-soft">Carregando mapa…</p>
        ) : error ? (
          <p className="rounded-lg bg-brand-50 px-3 py-2 text-xs font-semibold text-bordo">{error}</p>
        ) : !nodes.length ? (
          <div className="rounded-xl border border-dashed border-brand-200 bg-white/70 px-4 py-10 text-center">
            <p className="font-display text-lg font-bold text-bordo-deep">Nenhuma realização ainda</p>
            <p className="mt-1 text-sm text-bordo-soft">
              Comece um desafio e registre a aula na agenda — o mapa cresce a cada desdobramento.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-brand-100 bg-white/80">
            <svg
              viewBox={`0 0 ${layout.width} ${layout.height}`}
              className="min-h-[180px] w-full"
              role="img"
              aria-label="Grafo de realizações"
            >
              <defs>
                <marker
                  id="arrow-realizacoes"
                  markerWidth="8"
                  markerHeight="8"
                  refX="7"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L7,3 L0,6 Z" fill="#9f1239" opacity="0.55" />
                </marker>
              </defs>
              {edgePaths.map((p) => (
                <path
                  key={p.key}
                  d={p.d}
                  fill="none"
                  stroke="#9f1239"
                  strokeOpacity="0.35"
                  strokeWidth="2"
                  markerEnd="url(#arrow-realizacoes)"
                />
              ))}
              {layout.placed.map((n) => {
                const fill = STATUS_FILL[n.status] || STATUS_FILL.planejado
                const active = selected?.id === n.id
                return (
                  <g
                    key={n.id}
                    transform={`translate(${n.x}, ${n.y})`}
                    className="cursor-pointer"
                    role="button"
                    tabIndex={0}
                    aria-label={`${n.titulo || 'Evento'} — ${formatDia(n.data_evento)}`}
                    onClick={() => handleSelectNode(n)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleSelectNode(n)
                      }
                    }}
                  >
                    <circle
                      r={active ? 28 : 24}
                      fill={fill}
                      stroke={active ? '#7f1d1d' : '#fff'}
                      strokeWidth={active ? 3 : 2}
                      opacity={0.95}
                    />
                    <circle r={10} fill="#fff" opacity={0.35} cy={-6} />
                    <text
                      y={42}
                      textAnchor="middle"
                      className="fill-bordo"
                      style={{ fontSize: 11, fontWeight: 700 }}
                    >
                      {(n.titulo || 'Evento').slice(0, 18)}
                      {(n.titulo || '').length > 18 ? '…' : ''}
                    </text>
                    <text
                      y={56}
                      textAnchor="middle"
                      style={{ fontSize: 9, fill: '#9f1239', fontWeight: 600 }}
                    >
                      {formatDia(n.data_evento)} · {STATUS_LABEL[n.status] || n.status}
                    </text>
                  </g>
                )
              })}
            </svg>
          </div>
        )}

        {selected ? (
          <div className="mt-3 rounded-xl border border-brand-100 bg-white px-4 py-3 text-sm">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <p className="font-bold text-bordo-deep">{selected.titulo}</p>
                <p className="text-xs text-bordo-soft">
                  {formatDia(selected.data_evento)} ·{' '}
                  {STATUS_LABEL[selected.status] || selected.status}
                  {' · '}
                  {tipoLabel(selected.tipo)}
                </p>
                {selected.relato_sala ? (
                  <p className="mt-2 text-xs leading-relaxed text-bordo">
                    <span className="font-bold">Relato:</span> {selected.relato_sala}
                  </p>
                ) : null}
                {selected.participantes ? (
                  <p className="mt-1 text-xs leading-relaxed text-bordo-soft">
                    <span className="font-bold text-bordo">Participantes:</span>{' '}
                    {selected.participantes}
                  </p>
                ) : null}
                <p className="mt-2 text-[11px] text-bordo-soft">
                  Dia do evento: <strong className="text-bordo">{diaISO(selected.data_evento)}</strong>
                  {' — '}os dias com atividade na agenda abaixo ficam destacados.
                </p>
              </div>
              <button
                type="button"
                className="text-xs font-semibold text-bordo-soft hover:text-bordo"
                onClick={() => setSelected(null)}
              >
                Fechar
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-primary !px-4 !py-2 text-xs"
                onClick={() => goToKanban(selected)}
              >
                {destSelected?.label || 'Ir para a atividade'}
              </button>
              <button
                type="button"
                className="btn-ghost !px-4 !py-2 text-xs"
                onClick={() => {
                  onSelectNode?.(selected)
                  document
                    .getElementById('agenda-executiva')
                    ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                }}
              >
                Ver dia na agenda
              </button>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  )
}
