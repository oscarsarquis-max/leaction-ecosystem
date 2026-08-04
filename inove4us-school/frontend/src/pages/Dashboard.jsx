import { useEffect, useMemo, useState } from 'react'

const INSTITUICAO_ID =
  import.meta.env.VITE_INSTITUICAO_ID || 'a1111111-1111-4111-8111-111111111111'

const MESES = [
  'Janeiro',
  'Fevereiro',
  'Março',
  'Abril',
  'Maio',
  'Junho',
  'Julho',
  'Agosto',
  'Setembro',
  'Outubro',
  'Novembro',
  'Dezembro',
]
const DIAS_SEM = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']

const STATUS_LABEL = {
  pendente: 'Pendente',
  aprovado: 'Aprovado',
  reprovado: 'Reprovado',
}

const STATUS_CLASS = {
  pendente: 'bg-amber-50 text-amber-800',
  aprovado: 'bg-emerald-50 text-emerald-800',
  reprovado: 'bg-red-50 text-red-700',
}

const COL_W = 220
const LANE_H = 148
const LABEL_W = 180
const CARD_PAD_X = 20
const HEADER_H = 48

function pad2(n) {
  return n < 10 ? `0${n}` : String(n)
}

function toISODate(d) {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function startOfDay(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

function addDays(d, n) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  x.setDate(x.getDate() + n)
  return x
}

/** Domingo = 0 → início da semana na segunda. */
function startOfWeek(d) {
  const x = startOfDay(d)
  const day = x.getDay()
  const diff = day === 0 ? -6 : 1 - day
  return addDays(x, diff)
}

function PERIODOS() {
  return [
    { id: 'semanal', label: 'Semanal' },
    { id: 'quinzenal', label: 'Quinzenal' },
    { id: 'mensal', label: 'Mensal' },
    { id: 'semestral', label: 'Semestral' },
    { id: 'anual', label: 'Anual' },
  ]
}

/**
 * Resolve o intervalo [inicio, fim] a partir do tipo e de uma data âncora.
 */
function resolverPeriodo(tipo, anchor) {
  const a = startOfDay(anchor || new Date())
  const y = a.getFullYear()
  const m = a.getMonth()

  if (tipo === 'semanal') {
    const inicio = startOfWeek(a)
    const fim = addDays(inicio, 6)
    return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
  }

  if (tipo === 'quinzenal') {
    if (a.getDate() <= 15) {
      const inicio = new Date(y, m, 1)
      const fim = new Date(y, m, 15)
      return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
    }
    const inicio = new Date(y, m, 16)
    const fim = new Date(y, m + 1, 0)
    return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
  }

  if (tipo === 'semestral') {
    const firstHalf = m < 6
    const inicio = new Date(y, firstHalf ? 0 : 6, 1)
    const fim = new Date(y, firstHalf ? 6 : 12, 0)
    return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
  }

  if (tipo === 'anual') {
    const inicio = new Date(y, 0, 1)
    const fim = new Date(y, 12, 0)
    return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
  }

  // mensal (default)
  const inicio = new Date(y, m, 1)
  const fim = new Date(y, m + 1, 0)
  return { data_inicio: toISODate(inicio), data_fim: toISODate(fim), inicio, fim }
}

function shiftAnchor(tipo, anchor, delta) {
  const a = startOfDay(anchor)
  if (tipo === 'semanal') return addDays(a, delta * 7)
  if (tipo === 'quinzenal') return addDays(a, delta * 15)
  if (tipo === 'semestral') {
    return new Date(a.getFullYear(), a.getMonth() + delta * 6, 1)
  }
  if (tipo === 'anual') {
    return new Date(a.getFullYear() + delta, a.getMonth(), 1)
  }
  // mensal
  return new Date(a.getFullYear(), a.getMonth() + delta, 1)
}

function rotuloPeriodo(tipo, periodo) {
  const ini = formatarDataBR(periodo.data_inicio)
  const fim = formatarDataBR(periodo.data_fim)
  if (tipo === 'anual') return String(periodo.inicio.getFullYear())
  if (tipo === 'semestral') {
    const s = periodo.inicio.getMonth() < 6 ? '1º semestre' : '2º semestre'
    return `${s} ${periodo.inicio.getFullYear()}`
  }
  if (tipo === 'mensal') {
    return `${MESES[periodo.inicio.getMonth()]} ${periodo.inicio.getFullYear()}`
  }
  return `${ini} — ${fim}`
}

function hojeISO() {
  return toISODate(new Date())
}

function formatSemana(iso) {
  if (!iso) return '—'
  const [, m, d] = iso.split('-')
  return `${d}/${m}`
}

function formatarDataBR(iso) {
  const p = String(iso || '').slice(0, 10).split('-')
  if (p.length !== 3) return iso || '—'
  return `${p[2]}/${p[1]}/${p[0]}`
}

function labelProfessor(vinculoId, idx) {
  if (!vinculoId) return `Professor ${idx + 1}`
  return `Professor · ${String(vinculoId).slice(0, 8)}`
}

function TipoBadge({ tipo }) {
  const desafio = tipo === 'desafio'
  return (
    <span
      className={[
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold',
        desafio ? 'bg-amber-100 text-amber-950' : 'bg-emerald-100 text-emerald-900',
      ].join(' ')}
    >
      {desafio ? 'Desafio' : 'Dia a Dia'}
    </span>
  )
}

function StatusBadge({ status }) {
  return (
    <span
      className={[
        'inline-flex items-center rounded-md px-2 py-0.5 text-xs font-semibold',
        STATUS_CLASS[status] || 'bg-slate-100 text-slate-600',
      ].join(' ')}
    >
      {STATUS_LABEL[status] || status}
    </span>
  )
}

function KpiCard({ label, value, hint }) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-panel">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-ink">
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </article>
  )
}

function EmptyState() {
  return (
    <p className="px-6 py-12 text-center text-sm text-muted">
      Nenhum plano de aula ainda nesta visão. Quando os professores planejarem no
      inove4us, os planos aparecem aqui.
    </p>
  )
}

function buildLanes(planos) {
  const byProf = new Map()
  for (const p of planos) {
    const key = p.professor_vinculo_id
    if (!byProf.has(key)) byProf.set(key, [])
    byProf.get(key).push(p)
  }
  return [...byProf.entries()].map(([professorId, items], idx) => {
    const sorted = [...items].sort((a, b) => {
      const da = a.semana_referencia || ''
      const db = b.semana_referencia || ''
      if (da !== db) return da.localeCompare(db)
      return (a.desafio_sequencia || 0) - (b.desafio_sequencia || 0)
    })
    return {
      professorId,
      label: labelProfessor(professorId, idx),
      items: sorted,
    }
  })
}

function weeksFromPlanos(planos) {
  return [...new Set(planos.map((p) => p.semana_referencia).filter(Boolean))].sort()
}

function PedagogicalGraph({ planos, weeks: weeksProp, title }) {
  const weeks = weeksProp?.length ? weeksProp : weeksFromPlanos(planos)
  const weekIndex = useMemo(() => {
    const map = new Map()
    weeks.forEach((w, i) => map.set(w, i))
    return map
  }, [weeks])

  const lanes = useMemo(() => buildLanes(planos), [planos])

  if (!planos.length || !weeks.length) {
    return (
      <div>
        {title ? (
          <h3 className="border-b border-slate-100 px-5 py-3 text-sm font-semibold text-ink">
            {title}
          </h3>
        ) : null}
        <EmptyState />
      </div>
    )
  }

  const gridW = Math.max(weeks.length * COL_W, 640)

  return (
    <div>
      {title ? (
        <h3 className="border-b border-slate-100 px-5 py-3 text-sm font-semibold text-ink">
          {title}
        </h3>
      ) : null}
      <div className="overflow-x-auto px-2 py-3">
        <div className="inline-flex min-w-full">
          <div
            className="sticky left-0 z-20 shrink-0 border-r border-slate-200 bg-white"
            style={{ width: LABEL_W }}
          >
            <div
              className="flex items-end border-b border-slate-100 px-4 pb-2 text-[10px] font-semibold uppercase tracking-wide text-muted"
              style={{ height: HEADER_H }}
            >
              Professor
            </div>
            {lanes.map((lane) => (
              <div
                key={lane.professorId}
                className="flex items-center border-b border-slate-100 px-4 text-sm font-semibold leading-snug text-ink"
                style={{ height: LANE_H }}
              >
                {lane.label}
              </div>
            ))}
          </div>

          <div className="relative" style={{ width: gridW, minWidth: '100%' }}>
            <div
              className="flex border-b border-slate-100 bg-slate-50/90"
              style={{ height: HEADER_H }}
            >
              {weeks.map((w) => (
                <div
                  key={w}
                  className="flex shrink-0 items-center justify-center border-r border-slate-100 px-2 text-xs font-semibold text-muted"
                  style={{ width: COL_W }}
                >
                  Semana {formatSemana(w)}
                </div>
              ))}
            </div>

            {lanes.map((lane) => {
              const desafios = new Map()
              for (const item of lane.items) {
                if (item.tipo_aula !== 'desafio' || !item.desafio_grupo_id) continue
                if (!desafios.has(item.desafio_grupo_id)) {
                  desafios.set(item.desafio_grupo_id, [])
                }
                desafios.get(item.desafio_grupo_id).push(item)
              }

              return (
                <div
                  key={lane.professorId}
                  className="relative border-b border-slate-100"
                  style={{ height: LANE_H, width: gridW }}
                >
                  <div className="absolute inset-x-4 top-1/2 h-px bg-slate-200" />

                  {[...desafios.entries()].map(([gid, nodes]) => {
                    const idxs = nodes
                      .map((n) => weekIndex.get(n.semana_referencia))
                      .filter((i) => i != null)
                    if (!idxs.length) return null
                    const minI = Math.min(...idxs)
                    const maxI = Math.max(...idxs)
                    const left = minI * COL_W + 12
                    const width = (maxI - minI + 1) * COL_W - 24
                    const titulo = nodes[0]?.desafio_titulo || 'Desafio'
                    return (
                      <div
                        key={gid}
                        className="absolute top-3 bottom-3 rounded-xl border border-dashed border-school-500/45 bg-school-50/80"
                        style={{ left, width }}
                      >
                        <p className="truncate px-3 pt-2 text-[11px] font-semibold uppercase tracking-wide text-school-700">
                          {titulo}
                        </p>
                      </div>
                    )
                  })}

                  {lane.items.map((item, i) => {
                    const wi = weekIndex.get(item.semana_referencia)
                    if (wi == null) return null
                    const left = wi * COL_W + CARD_PAD_X
                    const next = lane.items[i + 1]
                    const sameGroup =
                      item.tipo_aula === 'desafio' &&
                      next &&
                      next.desafio_grupo_id &&
                      next.desafio_grupo_id === item.desafio_grupo_id
                    const nextWi = next ? weekIndex.get(next.semana_referencia) : null
                    const showArrow = sameGroup && nextWi != null && nextWi > wi
                    const cardW = COL_W - CARD_PAD_X * 2

                    return (
                      <div key={item.id}>
                        <div
                          className="absolute z-10 rounded-lg border border-slate-200 bg-white px-3 py-2.5 shadow-panel"
                          style={{ left, top: 44, width: cardW }}
                        >
                          <p className="truncate text-sm font-semibold text-ink">
                            {item.turma_nome}
                          </p>
                          <p className="mt-0.5 truncate text-xs text-muted">
                            {item.metodologia_nome}
                          </p>
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            <TipoBadge tipo={item.tipo_aula} />
                            <StatusBadge status={item.status} />
                          </div>
                        </div>
                        {showArrow ? (
                          <svg
                            className="pointer-events-none absolute z-[5] text-school-500"
                            style={{
                              left: left + cardW,
                              top: 68,
                              width: (nextWi - wi) * COL_W - cardW,
                              height: 14,
                            }}
                            viewBox="0 0 100 14"
                            preserveAspectRatio="none"
                            aria-hidden
                          >
                            <line
                              x1="0"
                              y1="7"
                              x2="90"
                              y2="7"
                              stroke="currentColor"
                              strokeWidth="2.5"
                            />
                            <polygon points="90,1 100,7 90,13" fill="currentColor" />
                          </svg>
                        ) : null}
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

/** Em "Todas": grafo geral em cima + um grafo por unidade abaixo. */
function GraphStack({ planos, unidadeId }) {
  const weeks = useMemo(() => weeksFromPlanos(planos), [planos])

  const porUnidade = useMemo(() => {
    const map = new Map()
    for (const p of planos) {
      const key = p.unidade_id || 'sem-unidade'
      if (!map.has(key)) {
        map.set(key, {
          id: key,
          nome: p.unidade_nome || 'Unidade',
          planos: [],
        })
      }
      map.get(key).planos.push(p)
    }
    return [...map.values()].sort((a, b) => a.nome.localeCompare(b.nome))
  }, [planos])

  if (!planos.length) return <EmptyState />

  // Unidade específica: um único grafo amplo
  if (unidadeId) {
    return (
      <PedagogicalGraph
        planos={planos}
        weeks={weeks}
        title={planos[0]?.unidade_nome || 'Unidade'}
      />
    )
  }

  // Todas: superior agregado + inferiores por unidade
  return (
    <div className="space-y-6 pb-4">
      <div className="overflow-hidden rounded-none border-b border-slate-200">
        <PedagogicalGraph
          planos={planos}
          weeks={weeks}
          title="Todas as unidades"
        />
      </div>
      {porUnidade.map((u) => (
        <div
          key={u.id}
          className="mx-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel sm:mx-4"
        >
          <PedagogicalGraph planos={u.planos} weeks={weeks} title={u.nome} />
        </div>
      ))}
    </div>
  )
}

/** Agenda mensal no formato do inove4us: grade + lista do dia (mês do período). */
function AgendaCalendario({ planos, showUnidade, viewYear, viewMonth, onShiftMonth, podeNavegarMes }) {
  const hoje = hojeISO()
  const [selectedDate, setSelectedDate] = useState(hoje)

  useEffect(() => {
    const now = new Date()
    if (viewYear === now.getFullYear() && viewMonth === now.getMonth()) {
      setSelectedDate(hojeISO())
    } else {
      setSelectedDate(`${viewYear}-${pad2(viewMonth + 1)}-01`)
    }
  }, [viewYear, viewMonth])

  const cells = useMemo(() => {
    const first = new Date(viewYear, viewMonth, 1)
    const offset = first.getDay()
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate()
    const list = []
    for (let i = 0; i < offset; i += 1) list.push(null)
    for (let d = 1; d <= daysInMonth; d += 1) {
      list.push(`${viewYear}-${pad2(viewMonth + 1)}-${pad2(d)}`)
    }
    return list
  }, [viewYear, viewMonth])

  const diasComPlano = useMemo(() => {
    const map = {}
    planos.forEach((p) => {
      const d = String(p.semana_referencia || '').slice(0, 10)
      if (!d) return
      if (!map[d]) map[d] = { desafio: false, dia: false }
      if (p.tipo_aula === 'desafio') map[d].desafio = true
      else map[d].dia = true
    })
    return map
  }, [planos])

  const planosDoDia = useMemo(
    () =>
      planos.filter(
        (p) => String(p.semana_referencia || '').slice(0, 10) === selectedDate,
      ),
    [planos, selectedDate],
  )

  return (
    <div className="grid gap-4 p-4 lg:grid-cols-2">
      <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <button
            type="button"
            className="rounded-lg bg-white px-2.5 py-1.5 text-xs font-bold text-ink shadow-sm hover:bg-school-50 disabled:opacity-40"
            onClick={() => onShiftMonth(-1)}
            disabled={!podeNavegarMes}
            aria-label="Mês anterior"
          >
            ‹
          </button>
          <p className="text-sm font-bold text-ink">
            {MESES[viewMonth]} {viewYear}
          </p>
          <button
            type="button"
            className="rounded-lg bg-white px-2.5 py-1.5 text-xs font-bold text-ink shadow-sm hover:bg-school-50 disabled:opacity-40"
            onClick={() => onShiftMonth(1)}
            disabled={!podeNavegarMes}
            aria-label="Próximo mês"
          >
            ›
          </button>
        </div>

        <div className="grid grid-cols-7 gap-1 text-center">
          {DIAS_SEM.map((d) => (
            <div key={d} className="py-1 text-[10px] font-bold uppercase text-muted">
              {d}
            </div>
          ))}
          {cells.map((iso, idx) => {
            if (!iso) return <div key={`b-${idx}`} className="aspect-square" />
            const isToday = iso === hoje
            const isSelected = iso === selectedDate
            const dayInfo = diasComPlano[iso]
            const hasEv = Boolean(dayInfo)
            return (
              <button
                key={iso}
                type="button"
                onClick={() => setSelectedDate(iso)}
                className={[
                  'relative aspect-square rounded-lg text-xs font-semibold transition',
                  isSelected
                    ? 'bg-school-500 text-white shadow-sm ring-2 ring-school-700'
                    : isToday
                      ? 'bg-school-100 text-school-800'
                      : 'bg-white text-ink hover:bg-school-50',
                ].join(' ')}
              >
                {Number(iso.slice(-2))}
                {hasEv ? (
                  <span className="absolute bottom-1 left-1/2 flex -translate-x-1/2 items-center gap-0.5">
                    {dayInfo.desafio ? (
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          isSelected ? 'bg-amber-200' : 'bg-amber-500'
                        }`}
                        title="Desafio"
                      />
                    ) : null}
                    {dayInfo.dia ? (
                      <span
                        className={`h-1.5 w-1.5 rounded-full ${
                          isSelected ? 'bg-emerald-200' : 'bg-emerald-500'
                        }`}
                        title="Dia a Dia"
                      />
                    ) : null}
                  </span>
                ) : null}
              </button>
            )
          })}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3 px-0.5 text-[10px] font-semibold text-muted">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-500" /> Desafio
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Dia a Dia
          </span>
        </div>
      </div>

      <div className="flex min-h-[280px] flex-col rounded-xl border border-slate-100 bg-white p-3">
        <div className="mb-3">
          <p className="text-[10px] font-bold uppercase tracking-wide text-muted">
            Planos do dia
          </p>
          <p className="text-sm font-bold text-ink">{formatarDataBR(selectedDate)}</p>
        </div>

        {planosDoDia.length === 0 ? (
          <p className="flex flex-1 items-center justify-center text-center text-xs text-muted">
            Nenhum plano neste dia.
          </p>
        ) : (
          <ul className="flex-1 space-y-2 overflow-y-auto">
            {planosDoDia.map((p) => {
              const desafio = p.tipo_aula === 'desafio'
              return (
                <li
                  key={p.id}
                  className={[
                    'rounded-xl border px-3 py-2.5',
                    desafio
                      ? 'border-amber-300 bg-amber-50'
                      : 'border-emerald-300 bg-emerald-50',
                  ].join(' ')}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-bold text-ink">{p.turma_nome}</p>
                    <StatusBadge status={p.status} />
                  </div>
                  <p
                    className={[
                      'mt-1 text-[10px] font-semibold uppercase tracking-wide',
                      desafio ? 'text-amber-800' : 'text-emerald-800',
                    ].join(' ')}
                  >
                    {desafio ? 'Desafio · método inove4us' : 'Dia a Dia · ciclo rápido'}
                  </p>
                  <p className="mt-1 text-[11px] text-muted">
                    {p.metodologia_nome}
                    {showUnidade && p.unidade_nome ? ` · ${p.unidade_nome}` : ''}
                    {p.desafio_titulo ? ` · ${p.desafio_titulo}` : ''}
                  </p>
                  <p className="mt-0.5 text-[11px] text-muted">
                    {labelProfessor(p.professor_vinculo_id, 0)}
                  </p>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [tipoPeriodo, setTipoPeriodo] = useState('mensal')
  const [anchor, setAnchor] = useState(() => startOfDay(new Date()))
  const periodo = useMemo(
    () => resolverPeriodo(tipoPeriodo, anchor),
    [tipoPeriodo, anchor],
  )

  // Mês exibido na grade da Agenda (dentro do período carregado).
  const [agendaYear, setAgendaYear] = useState(() => new Date().getFullYear())
  const [agendaMonth, setAgendaMonth] = useState(() => new Date().getMonth())

  useEffect(() => {
    setAgendaYear(periodo.inicio.getFullYear())
    setAgendaMonth(periodo.inicio.getMonth())
  }, [periodo.data_inicio, periodo.data_fim])

  const [unidades, setUnidades] = useState([])
  const [unidadeId, setUnidadeId] = useState(null)
  const [buscaUnidade, setBuscaUnidade] = useState('')
  const [modo, setModo] = useState('grafo')
  const [resumo, setResumo] = useState(null)
  const [planos, setPlanos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/unidades`)
        const body = await res.json().catch(() => [])
        if (!res.ok) throw new Error(body.error || 'Não foi possível carregar as unidades')
        if (!cancelled) setUnidades(body)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Erro ao carregar unidades')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError('')
      const q = new URLSearchParams({
        data_inicio: periodo.data_inicio,
        data_fim: periodo.data_fim,
      })
      if (unidadeId) q.set('unidade_id', unidadeId)
      try {
        const [rResumo, rPlanos] = await Promise.all([
          fetch(
            `/api/instituicoes/${INSTITUICAO_ID}/calendario-pedagogico/resumo?${q}`,
          ),
          fetch(`/api/instituicoes/${INSTITUICAO_ID}/calendario-pedagogico?${q}`),
        ])
        const jResumo = await rResumo.json().catch(() => ({}))
        const jPlanos = await rPlanos.json().catch(() => [])
        if (!rResumo.ok) throw new Error(jResumo.error || 'Falha ao carregar o resumo')
        if (!rPlanos.ok) throw new Error(jPlanos.error || 'Falha ao carregar os planos')
        if (cancelled) return
        setResumo(jResumo)
        setPlanos(jPlanos)
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Erro ao carregar o calendário')
          setResumo(null)
          setPlanos([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [unidadeId, periodo.data_inicio, periodo.data_fim])

  const unidadesFiltradas = useMemo(() => {
    const q = buscaUnidade.trim().toLowerCase()
    if (!q) return unidades
    return unidades.filter(
      (u) =>
        u.nome.toLowerCase().includes(q) ||
        (u.codigo || '').toLowerCase().includes(q) ||
        (u.cidade || '').toLowerCase().includes(q),
    )
  }, [unidades, buscaUnidade])

  const unidadeSelecionada = unidades.find((u) => u.id === unidadeId)

  function selecionarUnidade(u) {
    setUnidadeId(u.id)
    setBuscaUnidade(u.nome)
  }

  function limparUnidade() {
    setUnidadeId(null)
    setBuscaUnidade('')
  }

  function shiftPeriodo(delta) {
    setAnchor((prev) => shiftAnchor(tipoPeriodo, prev, delta))
  }

  function shiftAgendaMonth(delta) {
    const next = new Date(agendaYear, agendaMonth + delta, 1)
    // Mantém a navegação da grade dentro do período carregado.
    if (next < new Date(periodo.inicio.getFullYear(), periodo.inicio.getMonth(), 1)) return
    if (next > new Date(periodo.fim.getFullYear(), periodo.fim.getMonth(), 1)) return
    setAgendaYear(next.getFullYear())
    setAgendaMonth(next.getMonth())
  }

  const podeNavegarMesAgenda =
    periodo.inicio.getFullYear() !== periodo.fim.getFullYear() ||
    periodo.inicio.getMonth() !== periodo.fim.getMonth()

  return (
    <div className="mx-auto max-w-[90rem] space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Calendário pedagógico
        </h1>
        <p className="mt-1 text-sm text-muted">
          Para onde a escola está indo agora — Dia a Dia e Desafio, por unidade.
        </p>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-panel">
        <label className="block">
          <span className="mb-1.5 block text-xs font-semibold uppercase tracking-wide text-muted">
            Unidade
          </span>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <input
              type="search"
              value={buscaUnidade}
              onChange={(e) => {
                setBuscaUnidade(e.target.value)
                if (!e.target.value.trim()) setUnidadeId(null)
              }}
              placeholder="Buscar unidade…"
              className="min-w-0 flex-1 rounded-lg border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100"
            />
            <button
              type="button"
              onClick={limparUnidade}
              className={[
                'rounded-lg border px-3 py-2.5 text-sm font-semibold transition',
                unidadeId === null
                  ? 'border-school-500 bg-school-50 text-school-700'
                  : 'border-slate-200 text-muted hover:border-school-300 hover:text-ink',
              ].join(' ')}
            >
              Todas
            </button>
          </div>
        </label>

        {buscaUnidade.trim() && !unidadeId ? (
          <ul className="mt-2 max-h-40 overflow-y-auto rounded-lg border border-slate-100">
            {unidadesFiltradas.length === 0 ? (
              <li className="px-3 py-2 text-sm text-muted">Nenhuma unidade encontrada.</li>
            ) : (
              unidadesFiltradas.map((u) => (
                <li key={u.id}>
                  <button
                    type="button"
                    onClick={() => selecionarUnidade(u)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-school-50"
                  >
                    <span className="font-semibold text-ink">{u.nome}</span>
                    {u.codigo ? (
                      <span className="ml-2 text-xs text-muted">{u.codigo}</span>
                    ) : null}
                    {u.cidade ? (
                      <span className="ml-2 text-xs text-muted">
                        {u.cidade}
                        {u.uf ? `/${u.uf}` : ''}
                      </span>
                    ) : null}
                  </button>
                </li>
              ))
            )}
          </ul>
        ) : null}

        {unidadeSelecionada ? (
          <p className="mt-2 text-xs text-school-700">
            Filtrando: <strong>{unidadeSelecionada.nome}</strong>
          </p>
        ) : (
          <p className="mt-2 text-xs text-muted">Mostrando todas as unidades.</p>
        )}
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-panel">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
          Período
        </p>
        <div className="flex flex-wrap gap-2">
          {PERIODOS().map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                setTipoPeriodo(p.id)
                setAnchor(startOfDay(new Date()))
              }}
              className={[
                'rounded-lg border px-3 py-1.5 text-sm font-semibold transition',
                tipoPeriodo === p.id
                  ? 'border-school-500 bg-school-50 text-school-700'
                  : 'border-slate-200 text-muted hover:border-school-300 hover:text-ink',
              ].join(' ')}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => shiftPeriodo(-1)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-bold text-ink hover:bg-school-50"
            aria-label="Período anterior"
          >
            ‹
          </button>
          <p className="min-w-[12rem] text-center text-sm font-semibold text-ink">
            {rotuloPeriodo(tipoPeriodo, periodo)}
          </p>
          <button
            type="button"
            onClick={() => shiftPeriodo(1)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-bold text-ink hover:bg-school-50"
            aria-label="Próximo período"
          >
            ›
          </button>
        </div>
      </section>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          {modo === 'grafo'
            ? 'Grafo do período selecionado'
            : 'Calendário · planos do dia selecionado'}
        </p>
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-0.5">
          {[
            { id: 'grafo', label: 'Grafo' },
            { id: 'agenda', label: 'Agenda' },
          ].map((m) => (
            <button
              key={m.id}
              type="button"
              onClick={() => setModo(m.id)}
              className={[
                'rounded-md px-3 py-1.5 text-sm font-semibold transition',
                modo === m.id
                  ? 'bg-school-500 text-white'
                  : 'text-muted hover:text-ink',
              ].join(' ')}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      {loading && !resumo ? (
        <p className="text-sm text-muted" role="status">
          Carregando…
        </p>
      ) : null}

      {resumo ? (
        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard label="Planos no período" value={resumo.total} />
          <KpiCard
            label="Dia a Dia"
            value={resumo.por_tipo_aula?.dia_a_dia ?? 0}
            hint={`${resumo.por_tipo_aula?.desafio ?? 0} no Desafio`}
          />
          <KpiCard
            label="Pendentes"
            value={resumo.por_status?.pendente ?? 0}
            hint={`${resumo.por_status?.aprovado ?? 0} aprovados · ${resumo.por_status?.reprovado ?? 0} reprovados`}
          />
          <KpiCard label="Professores com plano" value={resumo.professores_ativos ?? 0} />
        </section>
      ) : null}

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
        <div className="border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-ink">
            {modo === 'grafo' ? 'Grafo do período' : 'Agenda'}
          </h2>
        </div>

        {modo === 'grafo' ? (
          <GraphStack planos={planos} unidadeId={unidadeId} />
        ) : (
          <AgendaCalendario
            planos={planos}
            showUnidade={unidadeId === null}
            viewYear={agendaYear}
            viewMonth={agendaMonth}
            onShiftMonth={shiftAgendaMonth}
            podeNavegarMes={podeNavegarMesAgenda}
          />
        )}
      </section>
    </div>
  )
}
