import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { useInstituicaoId } from '../lib/auth'
import { tabClassName } from '../lib/tabs'
import LessonMirrorModal from '../components/LessonMirrorModal'
import RadarAvisosPanel from '../components/RadarAvisosPanel'
import MonthAgendaCalendar, { hojeISO as hojeISOCal } from '../components/MonthAgendaCalendar'

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

const COL_W = 148
const LABEL_W = 250
const HEADER_H = 44
const PILL_H = 36

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
    { id: 'diario', label: 'Dia' },
    { id: 'semanal', label: 'Semana' },
    { id: 'quinzenal', label: 'Quinzena' },
    { id: 'mensal', label: 'Mês' },
    { id: 'anual', label: 'Ano' },
  ]
}

/**
 * Resolve o intervalo [inicio, fim] a partir do tipo e de uma data âncora.
 */
function resolverPeriodo(tipo, anchor) {
  const a = startOfDay(anchor || new Date())
  const y = a.getFullYear()
  const m = a.getMonth()

  if (tipo === 'diario') {
    return { data_inicio: toISODate(a), data_fim: toISODate(a), inicio: a, fim: a }
  }

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
  if (tipo === 'diario') return addDays(a, delta)
  if (tipo === 'semanal') return addDays(a, delta * 7)
  if (tipo === 'quinzenal') return addDays(a, delta * 15)
  if (tipo === 'anual') {
    return new Date(a.getFullYear() + delta, a.getMonth(), 1)
  }
  // mensal
  return new Date(a.getFullYear(), a.getMonth() + delta, 1)
}

function rotuloPeriodo(tipo, periodo) {
  const ini = formatarDataBR(periodo.data_inicio)
  const fim = formatarDataBR(periodo.data_fim)
  if (tipo === 'diario') return ini
  if (tipo === 'anual') return String(periodo.inicio.getFullYear())
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

function capitalizeToken(s) {
  const t = String(s || '').trim()
  if (!t) return ''
  return t.charAt(0).toUpperCase() + t.slice(1).toLowerCase()
}

/**
 * Nunca exibe e-mail completo. Extrai primeiro + último nome do local-part
 * (ex.: maria.silva@escola → "Prof. Maria Silva").
 */
function professorDisplayName(emailOrName, idx = 0) {
  const raw = String(emailOrName || '').trim()
  if (!raw) return `Prof. ${idx + 1}`
  if (!raw.includes('@')) {
    const parts = raw.replace(/^Prof.?s*/i, '').split(/s+/).filter(Boolean)
    if (parts.length >= 2) {
      return `Prof. ${capitalizeToken(parts[0])} ${capitalizeToken(parts[parts.length - 1])}`
    }
    if (parts.length === 1) return `Prof. ${capitalizeToken(parts[0])}`
    return `Prof. ${idx + 1}`
  }
  const local = raw.split('@')[0] || ''
  const parts = local.split(/[._+-]+/).filter(Boolean)
  if (parts.length >= 2) {
    return `Prof. ${capitalizeToken(parts[0])} ${capitalizeToken(parts[parts.length - 1])}`
  }
  if (parts.length === 1) return `Prof. ${capitalizeToken(parts[0])}`
  return `Prof. ${idx + 1}`
}

function professorInitials(displayName) {
  const cleaned = String(displayName || '')
    .replace(/^Prof.?s*/i, '')
    .trim()
  const parts = cleaned.split(/s+/).filter(Boolean)
  if (parts.length >= 2) {
    return `${parts[0][0] || ''}${parts[parts.length - 1][0] || ''}`.toUpperCase()
  }
  return (parts[0] || 'P').slice(0, 2).toUpperCase()
}

function pillTooltip(item) {
  const lines = [
    item.turma_nome || 'Turma',
    item.aula_titulo || item.conteudo_resumo || item.metodologia_nome
      ? `Plano: ${item.aula_titulo || item.conteudo_resumo || item.metodologia_nome}`
      : null,
    item.metodologia_nome ? `Metodologia: ${item.metodologia_nome}` : null,
    `Status: ${STATUS_LABEL[item.status] || item.status || '—'}`,
    item.semana_referencia
      ? `Referência: ${formatarDataBR(item.semana_referencia)}`
      : null,
    item.tipo_aula === 'desafio'
      ? `Tipo: Desafio${item.desafio_titulo ? ` · ${item.desafio_titulo}` : ''}`
      : 'Tipo: Dia a Dia',
    item.has_sugestao_curadoria
      ? 'Curadoria: gerou insumo para a matriz'
      : null,
  ].filter(Boolean)
  return lines.join('n')
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

function KpiCard({ label, value, hint, onClick }) {
  const clickable = typeof onClick === 'function'
  const Comp = clickable ? 'button' : 'article'
  return (
    <Comp
      type={clickable ? 'button' : undefined}
      onClick={onClick}
      className={[
        'rounded-xl border border-slate-200 bg-white p-4 text-left shadow-panel',
        clickable
          ? 'cursor-pointer transition hover:border-school-300 hover:bg-school-50/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-school-500'
          : '',
      ].join(' ')}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-2 text-3xl font-semibold tabular-nums tracking-tight text-ink">
        {value}
      </p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </Comp>
  )
}

function deriveKpis(planos) {
  const list = Array.isArray(planos) ? planos : []
  let dia = 0
  let desafio = 0
  let pendente = 0
  let aprovado = 0
  let reprovado = 0
  const profs = new Set()
  for (const p of list) {
    if (p.tipo_aula === 'desafio') desafio += 1
    else dia += 1
    if (p.status === 'aprovado') aprovado += 1
    else if (p.status === 'reprovado') reprovado += 1
    else pendente += 1
    if (p.professor_vinculo_id) profs.add(p.professor_vinculo_id)
  }
  return {
    total: list.length,
    por_tipo_aula: { dia_a_dia: dia, desafio },
    por_status: { pendente, aprovado, reprovado },
    professores_ativos: profs.size,
  }
}

function countExecucao(planos) {
  let andamento = 0
  let concluidas = 0
  for (const p of planos || []) {
    if (p.execucao_status === 'concluida') concluidas += 1
    else andamento += 1
  }
  return { andamento, concluidas }
}

function EmptyState() {
  return (
    <p className="px-6 py-12 text-center text-sm text-muted">
      Nenhum plano de aula ainda nesta visão. Quando os professores planejarem no
      inove4us, os planos aparecem aqui.
    </p>
  )
}

function ProfessorLaneLabel({ displayName }) {
  const initials = professorInitials(displayName)
  return (
    <div
      className="flex min-w-0 items-center gap-2.5 overflow-hidden"
      style={{ width: LABEL_W - 24 }}
      title={displayName}
    >
      <span
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-school-100 text-xs font-bold text-school-700"
        aria-hidden
      >
        {initials}
      </span>
      <span className="min-w-0 flex-1 truncate text-sm font-semibold text-ink">
        {displayName}
      </span>
    </div>
  )
}

function LessonPill({ item, onClick }) {
  const desafio = item.tipo_aula === 'desafio'
  const curadoria = Boolean(item.has_sugestao_curadoria)
  return (
    <button
      type="button"
      onClick={() => onClick?.(item)}
      title={pillTooltip(item)}
      className={[
        'inline-flex max-w-full items-center gap-1 rounded-full border px-2.5 text-left text-xs font-semibold transition',
        'hover:brightness-[0.97] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-school-500',
        desafio
          ? 'border-amber-200/90 bg-amber-50 text-amber-950'
          : 'border-emerald-200/90 bg-emerald-50 text-emerald-950',
        curadoria
          ? 'border-violet-500 shadow-[0_0_12px_rgba(109,40,217,0.45)] ring-1 ring-violet-400/80'
          : '',
      ].join(' ')}
      style={{ height: PILL_H, maxHeight: PILL_H }}
    >
      <span
        className={[
          'h-1.5 w-1.5 shrink-0 rounded-full',
          desafio ? 'bg-amber-500' : 'bg-emerald-500',
          curadoria ? 'bg-violet-600' : '',
        ].join(' ')}
        aria-hidden
      />
      <span className="min-w-0 truncate">{item.turma_nome || 'Turma'}</span>
      {curadoria ? (
        <span className="shrink-0 text-[10px] font-bold text-violet-700" aria-hidden>
          ◆
        </span>
      ) : null}
    </button>
  )
}

function buildLanes(planos) {
  const byProf = new Map()
  for (const p of planos) {
    const key = p.professor_vinculo_id || 'sem-professor'
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
    const displayName = professorDisplayName(
      items[0]?.professor_nome || items[0]?.professor_email,
      idx,
    )
    return {
      professorId,
      displayName,
      items: sorted,
    }
  })
}

function weeksFromPlanos(planos) {
  return [...new Set(planos.map((p) => p.semana_referencia).filter(Boolean))].sort()
}

function PedagogicalGraph({ planos, weeks: weeksProp, title, onNodeClick }) {
  const weeks = weeksProp?.length ? weeksProp : weeksFromPlanos(planos)
  const lanes = useMemo(() => buildLanes(planos), [planos])

  const cellsByLane = useMemo(() => {
    return lanes.map((lane) => {
      const byWeek = new Map()
      for (const w of weeks) byWeek.set(w, [])
      for (const item of lane.items) {
        const key = item.semana_referencia
        if (!byWeek.has(key)) byWeek.set(key, [])
        byWeek.get(key).push(item)
      }
      return byWeek
    })
  }, [lanes, weeks])

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

  const gridW = Math.max(weeks.length * COL_W, 480)

  return (
    <div>
      {title ? (
        <h3 className="border-b border-slate-100 px-5 py-3 text-sm font-semibold text-ink">
          {title}
        </h3>
      ) : null}
      <div className="overflow-x-auto">
        <div className="inline-block min-w-full align-top" style={{ minWidth: LABEL_W + gridW }}>
          {/* Header */}
          <div className="flex border-b border-slate-100 bg-slate-50/90">
            <div
              className="sticky left-0 z-30 flex shrink-0 items-end border-r border-slate-200 bg-slate-50 px-3 pb-2 text-[10px] font-semibold uppercase tracking-wide text-muted"
              style={{ width: LABEL_W, height: HEADER_H }}
            >
              Professor
            </div>
            {weeks.map((w) => (
              <div
                key={w}
                className="flex shrink-0 items-center justify-center border-r border-slate-100 px-1 text-[11px] font-semibold text-muted"
                style={{ width: COL_W, height: HEADER_H }}
              >
                {formatSemana(w)}
              </div>
            ))}
          </div>

          {/* Swimlanes — altura da linha cresce com o stacking */}
          {lanes.map((lane, laneIdx) => {
            const byWeek = cellsByLane[laneIdx]
            return (
              <div
                key={lane.professorId}
                className="flex items-stretch border-b border-slate-100"
              >
                <div
                  className="sticky left-0 z-20 flex shrink-0 items-center overflow-hidden border-r border-slate-200 bg-white px-3 py-2"
                  style={{ width: LABEL_W }}
                >
                  <ProfessorLaneLabel displayName={lane.displayName} />
                </div>
                {weeks.map((w) => {
                  const cellItems = byWeek.get(w) || []
                  return (
                    <div
                      key={`${lane.professorId}-${w}`}
                      className="flex shrink-0 flex-col flex-wrap content-start gap-1 border-r border-slate-50 p-1.5"
                      style={{
                        width: COL_W,
                        minHeight: 52,
                        gap: 4,
                      }}
                    >
                      {cellItems.map((item) => (
                        <LessonPill
                          key={item.id}
                          item={item}
                          onClick={onNodeClick}
                        />
                      ))}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/** Em "Todas": grafo geral em cima + um grafo por unidade abaixo. */
function GraphStack({ planos, unidadeId, onNodeClick }) {
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
        onNodeClick={onNodeClick}
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
          onNodeClick={onNodeClick}
        />
      </div>
      {porUnidade.map((u) => (
        <div
          key={u.id}
          className="mx-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel sm:mx-4"
        >
          <PedagogicalGraph
            planos={u.planos}
            weeks={weeks}
            title={u.nome}
            onNodeClick={onNodeClick}
          />
        </div>
      ))}
    </div>
  )
}


function AulasRadarLists({ planos, onOpen, statusFilter = null }) {
  const base = useMemo(() => {
    const list = Array.isArray(planos) ? planos : []
    if (!statusFilter || !statusFilter.length) return list
    const set = new Set(statusFilter)
    return list.filter((p) => set.has(p.status))
  }, [planos, statusFilter])

  const emAndamento = useMemo(
    () =>
      base
        .filter((p) => p.execucao_status === 'em_andamento')
        .sort((a, b) =>
          String(b.updated_at || b.semana_referencia).localeCompare(
            String(a.updated_at || a.semana_referencia),
          ),
        ),
    [base],
  )
  const concluidas = useMemo(
    () =>
      base
        .filter((p) => p.execucao_status === 'concluida')
        .sort((a, b) =>
          String(b.updated_at || b.semana_referencia).localeCompare(
            String(a.updated_at || a.semana_referencia),
          ),
        )
        .slice(0, 12),
    [base],
  )
  const filtradosPorStatus = useMemo(
    () =>
      [...base].sort((a, b) =>
        String(b.updated_at || b.semana_referencia).localeCompare(
          String(a.updated_at || a.semana_referencia),
        ),
      ),
    [base],
  )

  function ListBlock({ title, items, empty }) {
    return (
      <div className="rounded-xl border border-slate-100 bg-slate-50/40">
        <div className="border-b border-slate-100 px-4 py-3">
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          <p className="text-xs text-muted">{items.length} aula(s)</p>
        </div>
        {items.length === 0 ? (
          <p className="px-4 py-6 text-sm text-muted">{empty}</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {items.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => onOpen?.(p)}
                  className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition hover:bg-school-50/50"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-ink">
                      {p.turma_nome}
                      {p.aula_titulo ? ` · ${p.aula_titulo}` : ''}
                    </p>
                    <p className="mt-0.5 truncate text-xs text-muted">
                      {[
                        p.metodologia_nome,
                        professorDisplayName(p.professor_email || p.professor_nome, 0),
                        p.semana_referencia,
                      ]
                        .filter(Boolean)
                        .join(' · ')}
                    </p>
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      <TipoBadge tipo={p.tipo_aula} />
                      <StatusBadge status={p.status} />
                      {p.has_sugestao_curadoria ? (
                        <span className="rounded-md bg-violet-100 px-1.5 py-0.5 text-[10px] font-bold uppercase text-violet-800">
                          Insumo matriz
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <span className="shrink-0 text-xs font-semibold text-school-700">
                    Ver mesa →
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    )
  }

  return (
    <div className="grid gap-4 p-4 lg:grid-cols-2">
      {statusFilter?.length ? (
        <div className="lg:col-span-2">
          <ListBlock
            title="Pendentes e reprovados no recorte"
            items={filtradosPorStatus}
            empty="Nenhum plano pendente ou reprovado neste recorte."
          />
        </div>
      ) : (
        <>
          <ListBlock
            title="Aulas em andamento"
            items={emAndamento}
            empty="Nenhuma aula em execução no período (sync Mesa → School)."
          />
          <ListBlock
            title="Aulas concluídas recentemente"
            items={concluidas}
            empty="Nenhuma aula concluída no período."
          />
        </>
      )}
    </div>
  )
}

/** Agenda mensal do Radar — usa o mesmo MonthAgendaCalendar da Secretaria. */
function AgendaCalendario({
  planos,
  showUnidade,
  viewYear,
  viewMonth,
  onShiftMonth,
  podeNavegarMes,
  onOpenPlano,
}) {
  const [selectedDate, setSelectedDate] = useState(() => hojeISOCal())

  useEffect(() => {
    const now = new Date()
    if (viewYear === now.getFullYear() && viewMonth === now.getMonth()) {
      setSelectedDate(hojeISOCal())
    } else {
      setSelectedDate(`${viewYear}-${pad2(viewMonth + 1)}-01`)
    }
  }, [viewYear, viewMonth])

  const dayMarkers = useMemo(() => {
    const map = {}
    planos.forEach((p) => {
      const d = String(p.semana_referencia || '').slice(0, 10)
      if (!d) return
      if (!map[d]) map[d] = []
      map[d].push({
        id: p.id,
        tone: p.tipo_aula === 'desafio' ? 'amber' : 'emerald',
      })
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
    <MonthAgendaCalendar
      viewYear={viewYear}
      viewMonth={viewMonth}
      onShiftMonth={onShiftMonth}
      podeNavegarMes={podeNavegarMes}
      dayMarkers={dayMarkers}
      legend={[
        { tone: 'amber', label: 'Desafio' },
        { tone: 'emerald', label: 'Dia a Dia' },
      ]}
      selectedDate={selectedDate}
      onSelectDate={setSelectedDate}
      dayPanelTitle="Planos do dia"
      dayEmptyText="Nenhum plano neste dia."
      dayItems={planosDoDia}
      renderDayItem={(p) => {
        const desafio = p.tipo_aula === 'desafio'
        return (
          <button
            type="button"
            onClick={() => onOpenPlano?.(p)}
            className={[
              'w-full rounded-xl border px-3 py-2.5 text-left transition hover:ring-2 hover:ring-school-500/30',
              desafio ? 'border-amber-300 bg-amber-50' : 'border-emerald-300 bg-emerald-50',
              p.has_sugestao_curadoria ? 'ring-2 ring-violet-300/70' : '',
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
              {professorDisplayName(p.professor_email || p.professor_nome, 0)}
            </p>
          </button>
        )
      }}
    />
  )
}

export default function Dashboard() {
  const INSTITUICAO_ID = useInstituicaoId()
  const navigate = useNavigate()
  const [tipoPeriodo, setTipoPeriodo] = useState('diario')
  const [anchor, setAnchor] = useState(() => startOfDay(new Date()))
  const periodo = useMemo(
    () => resolverPeriodo(tipoPeriodo, anchor),
    [tipoPeriodo, anchor],
  )

  const [agendaYear, setAgendaYear] = useState(() => new Date().getFullYear())
  const [agendaMonth, setAgendaMonth] = useState(() => new Date().getMonth())

  useEffect(() => {
    setAgendaYear(periodo.inicio.getFullYear())
    setAgendaMonth(periodo.inicio.getMonth())
  }, [periodo.data_inicio, periodo.data_fim])

  const [unidades, setUnidades] = useState([])
  const [unidadeId, setUnidadeId] = useState('')
  const [professorId, setProfessorId] = useState('')
  const [metodologia, setMetodologia] = useState('')
  const [abaExplorar, setAbaExplorar] = useState('linha')
  const [listaStatusFilter, setListaStatusFilter] = useState(null)
  const [planos, setPlanos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedPlanoId, setSelectedPlanoId] = useState(null)
  const [consolidado, setConsolidado] = useState(null)
  const [curadoria, setCuradoria] = useState(null)
  const [curadoriaOpen, setCuradoriaOpen] = useState(false)

  useEffect(() => {
    if (!INSTITUICAO_ID) return undefined
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/unidades`, {
          credentials: 'include',
        })
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
  }, [INSTITUICAO_ID])

  useEffect(() => {
    if (!INSTITUICAO_ID) return undefined
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(`/api/instituicoes/${INSTITUICAO_ID}/resumo-consolidado`, {
          credentials: 'include',
        })
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha no resumo consolidado')
        if (!cancelled) setConsolidado(body)
      } catch {
        if (!cancelled) setConsolidado(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [INSTITUICAO_ID])

  useEffect(() => {
    if (!INSTITUICAO_ID) return undefined
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
        const rPlanos = await fetch(
          `/api/instituicoes/${INSTITUICAO_ID}/calendario-pedagogico?${q}`,
          { credentials: 'include' },
        )
        const jPlanos = await rPlanos.json().catch(() => [])
        if (!rPlanos.ok) throw new Error(jPlanos.error || 'Falha ao carregar os planos')
        if (cancelled) return
        setPlanos(Array.isArray(jPlanos) ? jPlanos : [])
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Erro ao carregar o calendário')
          setPlanos([])
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [INSTITUICAO_ID, unidadeId, periodo.data_inicio, periodo.data_fim])

  useEffect(() => {
    if (!INSTITUICAO_ID) return undefined
    let cancelled = false
    ;(async () => {
      const q = new URLSearchParams()
      if (unidadeId) q.set('unidade_id', unidadeId)
      try {
        const res = await fetch(
          `/api/instituicoes/${INSTITUICAO_ID}/curadoria-pendente?${q}`,
          { credentials: 'include' },
        )
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha na curadoria')
        if (!cancelled) setCuradoria(body)
      } catch {
        if (!cancelled) setCuradoria({ total: 0, metodologia: 0, pei: 0, itens: [] })
      }
    })()
    return () => {
      cancelled = true
    }
  }, [INSTITUICAO_ID, unidadeId])

  const professoresOpts = useMemo(() => {
    const map = new Map()
    for (const p of planos) {
      const id = p.professor_vinculo_id
      if (!id || map.has(id)) continue
      map.set(id, {
        id,
        label: professorDisplayName(p.professor_email || p.professor_nome, map.size),
      })
    }
    return [...map.values()].sort((a, b) => a.label.localeCompare(b.label))
  }, [planos])

  const metodologiasOpts = useMemo(() => {
    const set = new Set()
    for (const p of planos) {
      if (p.metodologia_nome) set.add(p.metodologia_nome)
    }
    return [...set].sort((a, b) => a.localeCompare(b))
  }, [planos])

  const planosFiltrados = useMemo(() => {
    return planos.filter((p) => {
      if (professorId && p.professor_vinculo_id !== professorId) return false
      if (metodologia && p.metodologia_nome !== metodologia) return false
      return true
    })
  }, [planos, professorId, metodologia])

  const kpis = useMemo(() => deriveKpis(planosFiltrados), [planosFiltrados])

  function shiftPeriodo(delta) {
    setAnchor((prev) => shiftAnchor(tipoPeriodo, prev, delta))
  }

  function onDatePick(iso) {
    if (!iso) return
    const [y, m, d] = iso.split('-').map(Number)
    if (!y || !m || !d) return
    setAnchor(startOfDay(new Date(y, m - 1, d)))
  }

  function shiftAgendaMonth(delta) {
    const next = new Date(agendaYear, agendaMonth + delta, 1)
    if (next < new Date(periodo.inicio.getFullYear(), periodo.inicio.getMonth(), 1)) return
    if (next > new Date(periodo.fim.getFullYear(), periodo.fim.getMonth(), 1)) return
    setAgendaYear(next.getFullYear())
    setAgendaMonth(next.getMonth())
  }

  const podeNavegarMesAgenda =
    periodo.inicio.getFullYear() !== periodo.fim.getFullYear() ||
    periodo.inicio.getMonth() !== periodo.fim.getMonth()

  const selectClass =
    'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-school-500 focus:ring-2 focus:ring-school-100'

  const consolidadoCards = [
    {
      key: 'gestao',
      label: 'Gestão Acadêmica',
      value: consolidado
        ? `${consolidado.unidades ?? 0} unidades · ${consolidado.turmas_ativas ?? 0} turmas`
        : '—',
      to: '/secretaria',
    },
    {
      key: 'docente',
      label: 'Corpo Docente',
      value: consolidado
        ? `${consolidado.professores_ativos ?? 0} professores ativos`
        : '—',
      to: '/equipe',
    },
    {
      key: 'com',
      label: 'Comunicações',
      value: consolidado
        ? `${consolidado.eventos_semana ?? 0} eventos esta semana`
        : '—',
      to: '/secretaria',
    },
    {
      key: 'editor',
      label: 'Editor Pedagógico',
      value: consolidado
        ? `${consolidado.metodologias_ativas ?? 0} metodologias · ${consolidado.planos_pei ?? 0} planos PEI`
        : '—',
      to: '/editor-pedagogico',
    },
  ]

  const abasExplorar = [
    { id: 'linha', label: 'Linha do Tempo' },
    { id: 'agenda', label: 'Agenda' },
    { id: 'lista', label: 'Lista' },
  ]

  return (
    <div className="mx-auto max-w-[90rem] space-y-5">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Radar Pedagógico
        </h1>
        <p className="mt-1 text-sm text-muted">
          Visão da Torre — consolidado da escola e exploração do recorte pedagógico.
        </p>
      </div>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {consolidadoCards.map((c) => (
          <KpiCard
            key={c.key}
            label={c.label}
            value={c.value}
            onClick={() => navigate(c.to)}
          />
        ))}
      </section>

      <section className="rounded-xl border border-slate-200 bg-slate-50/80 p-4 shadow-panel">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted">
            Mesa de som · Filtros
          </p>
          <p className="text-xs font-semibold text-ink">
            {rotuloPeriodo(tipoPeriodo, periodo)}
          </p>
        </div>

        <div className="grid gap-3 lg:grid-cols-12 lg:items-end">
          <label className="block lg:col-span-2">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Unidade
            </span>
            <select
              value={unidadeId}
              onChange={(e) => setUnidadeId(e.target.value)}
              className={selectClass}
            >
              <option value="">Todas</option>
              {unidades.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nome}
                </option>
              ))}
            </select>
          </label>

          <label className="block lg:col-span-2">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Professor
            </span>
            <select
              value={professorId}
              onChange={(e) => setProfessorId(e.target.value)}
              className={selectClass}
            >
              <option value="">Todos</option>
              {professoresOpts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block lg:col-span-2">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Disciplina / Metodologia
            </span>
            <select
              value={metodologia}
              onChange={(e) => setMetodologia(e.target.value)}
              className={selectClass}
            >
              <option value="">Todas</option>
              {metodologiasOpts.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </label>

          <div className="lg:col-span-4">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Período
            </span>
            <div className="flex flex-wrap gap-1 rounded-lg border border-slate-200 bg-white p-1">
              {PERIODOS().map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setTipoPeriodo(p.id)}
                  className={[
                    'flex-1 rounded-md px-2 py-1.5 text-xs font-semibold transition sm:text-sm',
                    tipoPeriodo === p.id
                      ? 'bg-school-700 text-white'
                      : 'text-muted hover:bg-school-50 hover:text-ink',
                  ].join(' ')}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          <label className="block lg:col-span-2">
            <span className="mb-1 block text-[10px] font-bold uppercase tracking-wide text-muted">
              Data base
            </span>
            <input
              type="date"
              value={toISODate(anchor)}
              onChange={(e) => onDatePick(e.target.value)}
              className={selectClass}
            />
          </label>
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
          <button
            type="button"
            onClick={() => shiftPeriodo(1)}
            className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-bold text-ink hover:bg-school-50"
            aria-label="Próximo período"
          >
            ›
          </button>
          <button
            type="button"
            onClick={() => {
              setUnidadeId('')
              setProfessorId('')
              setMetodologia('')
              setListaStatusFilter(null)
              setTipoPeriodo('diario')
              setAnchor(startOfDay(new Date()))
            }}
            className="ml-auto rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-muted hover:border-school-300 hover:text-ink"
          >
            Limpar filtros
          </button>
        </div>
      </section>

      {error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}

      {loading && !planos.length ? (
        <p className="text-sm text-muted" role="status">
          Carregando…
        </p>
      ) : null}

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Planos no recorte" value={kpis.total} />
        <KpiCard
          label="Dia a Dia"
          value={kpis.por_tipo_aula.dia_a_dia}
          hint={`${kpis.por_tipo_aula.desafio} no Desafio`}
        />
        <KpiCard
          label="Pendentes"
          value={kpis.por_status.pendente}
          hint={`${kpis.por_status.aprovado} aprovados · ${kpis.por_status.reprovado} reprovados`}
          onClick={() => {
            setAbaExplorar('lista')
            setListaStatusFilter(['pendente', 'reprovado'])
          }}
        />
        <KpiCard label="Professores no recorte" value={kpis.professores_ativos} />
      </section>

      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
        <div className="border-b border-slate-100 px-4 pt-3">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-muted">
            Explorar o recorte
          </p>
          <div className="flex gap-1">
            {abasExplorar.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  setAbaExplorar(t.id)
                  if (t.id !== 'lista') setListaStatusFilter(null)
                }}
                className={tabClassName(abaExplorar === t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        <div className={abaExplorar === 'linha' ? '' : 'hidden'} aria-hidden={abaExplorar !== 'linha'}>
          <GraphStack
            planos={planosFiltrados}
            unidadeId={
              unidadeId ||
              (professorId ? planosFiltrados[0]?.unidade_id || null : null)
            }
            onNodeClick={(p) => setSelectedPlanoId(p.id)}
          />
        </div>

        <div className={abaExplorar === 'agenda' ? '' : 'hidden'} aria-hidden={abaExplorar !== 'agenda'}>
          <AgendaCalendario
            planos={planosFiltrados}
            showUnidade={!unidadeId}
            viewYear={agendaYear}
            viewMonth={agendaMonth}
            onShiftMonth={shiftAgendaMonth}
            podeNavegarMes={podeNavegarMesAgenda}
            onOpenPlano={(p) => setSelectedPlanoId(p.id)}
          />
        </div>

        <div className={abaExplorar === 'lista' ? '' : 'hidden'} aria-hidden={abaExplorar !== 'lista'}>
          {listaStatusFilter ? (
            <div className="flex items-center justify-between gap-2 border-b border-amber-100 bg-amber-50/60 px-4 py-2">
              <p className="text-xs font-semibold text-amber-900">
                Filtro ativo: pendentes e reprovados
              </p>
              <button
                type="button"
                onClick={() => setListaStatusFilter(null)}
                className="text-xs font-semibold text-amber-800 underline"
              >
                Limpar
              </button>
            </div>
          ) : null}
          <AulasRadarLists
            planos={planosFiltrados}
            statusFilter={listaStatusFilter}
            onOpen={(p) => setSelectedPlanoId(p.id)}
          />
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-panel">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted">
            Central de ações
          </p>
          <h2 className="mt-1 text-base font-semibold text-ink">Curadoria pendente</h2>
          <p className="mt-2 text-3xl font-semibold tabular-nums text-ink">
            {curadoria?.total ?? 0}
          </p>
          <p className="mt-1 text-sm text-muted">
            {curadoria?.metodologia ?? 0} sugestões de metodologia e{' '}
            {curadoria?.pei ?? 0} de PEI aguardando revisão.
          </p>
          <button
            type="button"
            onClick={() => setCuradoriaOpen(true)}
            className="mt-4 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-700"
          >
            Revisar
          </button>
        </article>

        <article className="rounded-xl border border-slate-200 bg-white shadow-panel">
          <div className="border-b border-slate-100 px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted">
              Central de ações
            </p>
            <h2 className="mt-1 text-base font-semibold text-ink">Quadro de avisos</h2>
          </div>
          <RadarAvisosPanel />
        </article>
      </section>

      {curadoriaOpen
        ? createPortal(
            <div
              className="fixed inset-0 z-[200] flex items-start justify-center overflow-y-auto bg-ink/50 p-3 sm:p-6"
              role="dialog"
              aria-modal="true"
              onClick={(e) => {
                if (e.target === e.currentTarget) setCuradoriaOpen(false)
              }}
            >
              <div className="my-4 w-full max-w-lg rounded-2xl border border-slate-200 bg-white shadow-panel">
                <div className="flex items-start justify-between gap-3 border-b border-slate-100 px-4 py-3">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-wide text-muted">
                      Curadoria
                    </p>
                    <h3 className="text-lg font-semibold text-ink">Pendências</h3>
                  </div>
                  <button
                    type="button"
                    onClick={() => setCuradoriaOpen(false)}
                    className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-muted hover:bg-slate-50"
                  >
                    Fechar
                  </button>
                </div>
                <ul className="max-h-[min(70vh,560px)] divide-y divide-slate-100 overflow-y-auto">
                  {(curadoria?.itens || []).length === 0 ? (
                    <li className="px-4 py-8 text-center text-sm text-muted">
                      Nenhuma pendência no momento.
                    </li>
                  ) : (
                    (curadoria?.itens || []).map((item) => (
                      <li key={`${item.tipo}-${item.id}`}>
                        <button
                          type="button"
                          disabled={!item.plano_id}
                          onClick={() => {
                            if (!item.plano_id) return
                            setCuradoriaOpen(false)
                            setSelectedPlanoId(item.plano_id)
                          }}
                          className="flex w-full items-start justify-between gap-3 px-4 py-3 text-left transition hover:bg-school-50/50 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-ink">
                              {item.turma_nome}
                            </p>
                            <p className="mt-0.5 text-xs text-muted">
                              {item.professor_label}
                              {item.data ? ` · ${formatarDataBR(item.data)}` : ''}
                            </p>
                            <span
                              className={[
                                'mt-1.5 inline-flex rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase',
                                item.tipo === 'pei'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : 'bg-violet-100 text-violet-800',
                              ].join(' ')}
                            >
                              {item.tipo === 'pei' ? 'PEI' : 'Metodologia'}
                            </span>
                          </div>
                          <span className="shrink-0 text-xs font-semibold text-school-700">
                            {item.plano_id ? 'Abrir mesa →' : 'Sem plano'}
                          </span>
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </div>,
            document.body,
          )
        : null}

      {selectedPlanoId ? (
        <LessonMirrorModal
          planoId={selectedPlanoId}
          instituicaoId={INSTITUICAO_ID}
          onClose={() => setSelectedPlanoId(null)}
        />
      ) : null}
    </div>
  )
}
