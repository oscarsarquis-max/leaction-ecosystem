import { useEffect, useMemo, useState } from 'react'
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

const COL_W = 156
const LABEL_W = 112
const HEADER_H = 44
const PILL_H = 40

/**
 * Cores semânticas do grafo:
 * - família: Dia a Dia (verde) | Desafio (âmbar) | Evento (ardósia)
 * - saturação: planejada (sólida) | encerrada (clara)
 */
function isEventoItem(item) {
  return item?.item_kind === 'evento' || item?.tipo_aula === 'evento'
}

function isEncerrada(item) {
  return item?.execucao_status === 'concluida'
}

function pillSemanticStyle(item) {
  if (isEventoItem(item)) {
    return isEncerrada(item)
      ? 'border-slate-300 bg-slate-100 text-slate-700'
      : 'border-slate-700 bg-slate-700 text-white'
  }
  const desafio = item?.tipo_aula === 'desafio'
  if (desafio) {
    return isEncerrada(item)
      ? 'border-amber-200 bg-amber-50 text-amber-900'
      : 'border-amber-600 bg-amber-500 text-amber-950'
  }
  return isEncerrada(item)
    ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
    : 'border-emerald-700 bg-emerald-600 text-white'
}

function pillCodigo(item) {
  if (isEventoItem(item)) {
    return String(item.disciplina_codigo || 'EVT').trim().toUpperCase() || 'EVT'
  }
  return (
    String(item.disciplina_codigo || item.curso_codigo || '').trim().toUpperCase() || '—'
  )
}

function pillTurmaShort(nome) {
  const t = String(nome || '').trim()
  if (!t) return ''
  // "6º Ano A" → "6A"; fallback truncado
  const m = t.match(/(\d+)\s*[ºªo]?\s*(?:ano)?\s*([A-Za-z])?/i)
  if (m) return `${m[1]}${(m[2] || '').toUpperCase()}`
  return t.length > 8 ? `${t.slice(0, 7)}…` : t
}

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
    const parts = raw.replace(/^Prof\.?\s*/i, '').split(/\s+/).filter(Boolean)
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
    .replace(/^Prof\.?\s*/i, '')
    .trim()
  const parts = cleaned.split(/\s+/).filter(Boolean)
  if (parts.length >= 2) {
    return `${parts[0][0] || ''}${parts[parts.length - 1][0] || ''}`.toUpperCase()
  }
  return (parts[0] || 'P').slice(0, 2).toUpperCase()
}

function pillTooltip(item) {
  const codigo = pillCodigo(item)
  if (isEventoItem(item)) {
    return [
      item.aula_titulo || 'Evento escolar',
      item.disciplina_nome || (codigo === 'REU' ? 'Reunião pedagógica' : 'Evento escolar'),
      item.turma_nome ? `Público: ${item.turma_nome}` : null,
      item.horario_label ? `Horário: ${item.horario_label}` : null,
      item.semana_referencia ? `Data: ${formatarDataBR(item.semana_referencia)}` : null,
      isEncerrada(item) ? 'Estado: encerrado' : 'Estado: planejado',
    ]
      .filter(Boolean)
      .join('\n')
  }
  const lines = [
    codigo !== '—' ? `Código: ${codigo}` : null,
    item.disciplina_nome ? `Disciplina: ${item.disciplina_nome}` : null,
    item.curso_nome ? `Curso: ${item.curso_nome}` : null,
    item.turma_nome || 'Turma',
    item.horario_label ? `Horário: ${item.horario_label}` : null,
    item.professor_nome || item.professor_email
      ? `Professor: ${professorDisplayName(item.professor_nome || item.professor_email, 0)}`
      : null,
    item.aula_titulo || item.conteudo_resumo || item.metodologia_nome
      ? `Plano: ${item.aula_titulo || item.conteudo_resumo || item.metodologia_nome}`
      : null,
    item.metodologia_nome ? `Metodologia: ${item.metodologia_nome}` : null,
    `Status: ${STATUS_LABEL[item.status] || item.status || '—'}`,
    isEncerrada(item) ? 'Execução: encerrada' : 'Execução: planejada',
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
  return lines.join('\n')
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
  const list = (Array.isArray(planos) ? planos : []).filter((p) => !isEventoItem(p))
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
    if (isEventoItem(p)) continue
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

function HorarioLaneLabel({ label, sortKey }) {
  const isClock = /^\d{2}:\d{2}/.test(String(sortKey || ''))
  return (
    <div
      className="flex min-w-0 items-center overflow-hidden"
      style={{ width: LABEL_W - 16 }}
      title={label}
    >
      <span
        className={[
          'truncate font-semibold tabular-nums tracking-tight text-ink',
          isClock ? 'text-base' : 'text-sm',
        ].join(' ')}
      >
        {label}
      </span>
    </div>
  )
}

function LessonPill({ item, onClick }) {
  const evento = isEventoItem(item)
  const desafio = item.tipo_aula === 'desafio'
  const encerrada = isEncerrada(item)
  const curadoria = Boolean(item.has_sugestao_curadoria)
  const codigo = pillCodigo(item)
  const turmaShort = pillTurmaShort(item.turma_nome)
  const label = evento
    ? String(item.aula_titulo || codigo).trim()
    : `${codigo}${turmaShort ? ` · ${turmaShort}` : ''}`
  return (
    <button
      type="button"
      onClick={() => onClick?.(item)}
      title={pillTooltip(item)}
      className={[
        'inline-flex max-w-full items-center gap-1.5 rounded-lg border px-2 text-left text-xs font-semibold transition',
        'hover:brightness-[0.97] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-school-500',
        pillSemanticStyle(item),
        encerrada ? 'opacity-90' : '',
        curadoria && !evento
          ? 'ring-2 ring-violet-400/80 ring-offset-1'
          : '',
      ].join(' ')}
      style={{ height: PILL_H, maxHeight: PILL_H }}
    >
      <span className="min-w-0 flex-1 truncate">
        {evento ? (
          <>
            <span className="font-bold tracking-wide">{codigo}</span>
            <span className="font-medium opacity-90">
              {' '}
              · {String(item.aula_titulo || 'Evento').slice(0, 18)}
            </span>
          </>
        ) : (
          <span className="font-bold tracking-wide">{label}</span>
        )}
      </span>
      {desafio && !evento ? (
        <span className="shrink-0 text-[9px] font-bold uppercase opacity-90" aria-hidden>
          D
        </span>
      ) : null}
      {curadoria && !evento ? (
        <span
          className={[
            'shrink-0 text-[10px] font-bold',
            encerrada ? 'text-violet-700' : 'text-violet-200',
          ].join(' ')}
          aria-hidden
        >
          ◆
        </span>
      ) : null}
    </button>
  )
}

function GraphLegend() {
  const items = [
    { key: 'dd-p', label: 'Dia a Dia · planejada', className: 'border-emerald-700 bg-emerald-600' },
    { key: 'dd-e', label: 'Dia a Dia · encerrada', className: 'border-emerald-200 bg-emerald-50' },
    { key: 'dz-p', label: 'Desafio · planejada', className: 'border-amber-600 bg-amber-500' },
    { key: 'dz-e', label: 'Desafio · encerrada', className: 'border-amber-200 bg-amber-50' },
    { key: 'ev-p', label: 'Evento escolar · planejado', className: 'border-slate-700 bg-slate-700' },
    { key: 'ev-e', label: 'Evento escolar · encerrado', className: 'border-slate-300 bg-slate-100' },
    { key: 'cur', label: 'Com sugestão p/ curadoria', className: 'border-violet-400 bg-white ring-2 ring-violet-400' },
  ]
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-slate-100 bg-slate-50/70 px-4 py-2.5">
      <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-muted">
        Legenda
      </p>
      {items.map((it) => (
        <div key={it.key} className="inline-flex items-center gap-1.5 text-[11px] text-slate-700">
          <span
            className={['h-3 w-5 shrink-0 rounded border', it.className].join(' ')}
            aria-hidden
          />
          <span>{it.label}</span>
        </div>
      ))}
      <p className="text-[11px] text-muted">
        Texto na pílula = código da disciplina (ou EVT/REU) · turma
      </p>
    </div>
  )
}

/** Faixas do grafo = horário (eixo esquerdo tabular). */
function buildLanes(planos) {
  const byHorario = new Map()
  for (const p of planos) {
    const sort = p.horario_sort || '99:99'
    const label = p.horario_label || 'Sem horário'
    const key = `${sort}|${label}`
    if (!byHorario.has(key)) {
      byHorario.set(key, { sortKey: sort, label, items: [] })
    }
    byHorario.get(key).items.push(p)
  }
  return [...byHorario.values()]
    .sort((a, b) => {
      if (a.sortKey !== b.sortKey) return a.sortKey.localeCompare(b.sortKey)
      return a.label.localeCompare(b.label)
    })
    .map((lane) => ({
      ...lane,
      laneId: `${lane.sortKey}-${lane.label}`,
      items: [...lane.items].sort((a, b) => {
        const da = a.semana_referencia || ''
        const db = b.semana_referencia || ''
        if (da !== db) return da.localeCompare(db)
        const ca = pillCodigo(a)
        const cb = pillCodigo(b)
        if (ca !== cb) return ca.localeCompare(cb)
        return (a.desafio_sequencia || 0) - (b.desafio_sequencia || 0)
      }),
    }))
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
              className="sticky left-0 z-30 flex shrink-0 items-end border-r border-slate-200 bg-slate-50 px-2 pb-2 text-[10px] font-semibold uppercase tracking-wide text-muted"
              style={{ width: LABEL_W, height: HEADER_H }}
            >
              Horário
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

          {/* Swimlanes por horário — pílulas diferenciadas por código */}
          {lanes.map((lane, laneIdx) => {
            const byWeek = cellsByLane[laneIdx]
            return (
              <div
                key={lane.laneId}
                className="flex items-stretch border-b border-slate-100"
              >
                <div
                  className="sticky left-0 z-20 flex shrink-0 items-center overflow-hidden border-r border-slate-200 bg-white px-2 py-2"
                  style={{ width: LABEL_W }}
                >
                  <HorarioLaneLabel label={lane.label} sortKey={lane.sortKey} />
                </div>
                {weeks.map((w) => {
                  const cellItems = byWeek.get(w) || []
                  return (
                    <div
                      key={`${lane.laneId}-${w}`}
                      className="flex shrink-0 flex-col content-start gap-1 border-r border-slate-50 p-1.5"
                      style={{
                        width: COL_W,
                        minHeight: 56,
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

  if (!planos.length) {
    return (
      <div>
        <GraphLegend />
        <EmptyState />
      </div>
    )
  }

  // Unidade específica: um único grafo amplo
  if (unidadeId) {
    return (
      <div>
        <GraphLegend />
        <PedagogicalGraph
          planos={planos}
          weeks={weeks}
          title={planos[0]?.unidade_nome || 'Unidade'}
          onNodeClick={onNodeClick}
        />
      </div>
    )
  }

  // Todas: superior agregado + inferiores por unidade
  return (
    <div className="space-y-6 pb-4">
      <GraphLegend />
      <div className="overflow-hidden rounded-none border-b border-slate-200">
        <PedagogicalGraph
          planos={planos}
          weeks={weeks}
          title="Todas as unidades · aulas e eventos"
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
    const list = (Array.isArray(planos) ? planos : []).filter((p) => !isEventoItem(p))
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
      let tone = 'emerald'
      if (isEventoItem(p)) tone = 'slate'
      else if (p.tipo_aula === 'desafio') tone = 'amber'
      map[d].push({ id: p.id, tone })
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
        { tone: 'emerald', label: 'Dia a Dia' },
        { tone: 'amber', label: 'Desafio' },
        { tone: 'slate', label: 'Evento escolar' },
      ]}
      selectedDate={selectedDate}
      onSelectDate={setSelectedDate}
      dayPanelTitle="Planos e eventos do dia"
      dayEmptyText="Nenhum plano ou evento neste dia."
      dayItems={planosDoDia}
      renderDayItem={(p) => {
        if (isEventoItem(p)) {
          return (
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink">
                {p.aula_titulo || 'Evento escolar'}
              </p>
              <p className="mt-0.5 text-xs text-muted">
                {[p.disciplina_nome, p.horario_label, p.turma_nome].filter(Boolean).join(' · ')}
              </p>
              <span className="mt-1 inline-flex rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-700">
                Evento
              </span>
            </div>
          )
        }
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
      if (isEventoItem(p)) {
        // Eventos da escola ficam no grafo; somem se houver filtro de prof/metodologia.
        if (professorId || metodologia) return false
        return true
      }
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
            onNodeClick={(p) => {
              if (isEventoItem(p)) return
              setSelectedPlanoId(p.id)
            }}
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
        <article className="flex flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-panel">
          <div className="border-b border-slate-100 px-4 py-3">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-muted">
              Central de ações
            </p>
            <div className="mt-1 flex flex-wrap items-end justify-between gap-2">
              <h2 className="text-base font-semibold text-ink">Curadoria pendente</h2>
              <p className="text-2xl font-semibold tabular-nums text-ink">
                {curadoria?.total ?? 0}
              </p>
            </div>
            <p className="mt-1 text-sm text-muted">
              {curadoria?.metodologia ?? 0} sugestões de metodologia e{' '}
              {curadoria?.pei ?? 0} de PEI aguardando análise — atalho para o Editor
              Pedagógico.
            </p>
          </div>

          <ul className="max-h-[min(28rem,55vh)] divide-y divide-slate-100 overflow-y-auto">
            {(curadoria?.itens || []).length === 0 ? (
              <li className="px-4 py-8 text-center text-sm text-muted">
                Nenhuma sugestão pendente no momento.
              </li>
            ) : (
              (curadoria?.itens || []).map((item) => {
                const pei = item.tipo === 'pei'
                const met = (item.metodologia_nome || '').trim()
                const q = new URLSearchParams({
                  pilar: pei ? 'pei' : 'metodologias',
                })
                if (met && met !== '—') q.set('met', met)
                return (
                  <li key={`${item.tipo}-${item.id}`}>
                    <button
                      type="button"
                      onClick={() => navigate(`/editor-pedagogico?${q}`)}
                      className="flex w-full items-start gap-3 border-l-[5px] border-l-amber-500 bg-amber-50/30 px-4 py-3 text-left transition hover:bg-amber-50/70"
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-sm font-semibold text-ink">
                            {met && met !== '—' ? met : 'Metodologia'}
                          </p>
                          <span
                            className={[
                              'inline-flex rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase',
                              pei
                                ? 'bg-emerald-100 text-emerald-800'
                                : 'bg-violet-100 text-violet-800',
                            ].join(' ')}
                          >
                            {pei ? 'PEI' : 'Metodologia'}
                          </span>
                          <span className="rounded-md bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-900">
                            p/ análise
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-muted">
                          {item.turma_nome || '—'}
                          {item.professor_label ? ` · ${item.professor_label}` : ''}
                          {item.data ? ` · ${formatarDataBR(item.data)}` : ''}
                        </p>
                        {item.trecho ? (
                          <p className="mt-1 line-clamp-2 text-xs text-slate-600">
                            {item.trecho}
                          </p>
                        ) : null}
                      </div>
                      <span className="shrink-0 pt-0.5 text-xs font-semibold text-amber-900">
                        Avaliar →
                      </span>
                    </button>
                  </li>
                )
              })
            )}
          </ul>
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
