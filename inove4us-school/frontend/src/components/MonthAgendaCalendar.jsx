import { useEffect, useMemo, useState } from 'react'

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

const TONE_DOT = {
  amber: { selected: 'bg-amber-200', idle: 'bg-amber-500' },
  emerald: { selected: 'bg-emerald-200', idle: 'bg-emerald-500' },
  violet: { selected: 'bg-violet-200', idle: 'bg-violet-500' },
  sky: { selected: 'bg-sky-200', idle: 'bg-sky-500' },
  rose: { selected: 'bg-rose-200', idle: 'bg-rose-500' },
  slate: { selected: 'bg-slate-200', idle: 'bg-slate-500' },
}

function pad2(n) {
  return n < 10 ? `0${n}` : String(n)
}

function hojeISO() {
  const d = new Date()
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

export function formatarDataBR(iso) {
  const p = String(iso || '').slice(0, 10).split('-')
  if (p.length !== 3) return iso || '—'
  return `${p[2]}/${p[1]}/${p[0]}`
}

/**
 * Grade mensal compartilhada (Radar Agenda + Secretaria Calendário).
 *
 * dayMarkers: { 'YYYY-MM-DD': [{ id?, tone, title? }] }
 * dayItems: itens do dia selecionado (render via renderDayItem)
 */
export default function MonthAgendaCalendar({
  viewYear,
  viewMonth,
  onShiftMonth,
  podeNavegarMes = true,
  dayMarkers = {},
  legend = [],
  selectedDate: selectedControlled,
  onSelectDate,
  dayPanelTitle = 'Itens do dia',
  dayEmptyText = 'Nenhum item neste dia.',
  dayItems = [],
  renderDayItem,
  onEmptyDayAction,
  emptyActionLabel = 'Adicionar',
}) {
  const hoje = hojeISO()
  const [selectedInternal, setSelectedInternal] = useState(hoje)
  const selectedDate = selectedControlled ?? selectedInternal

  function selectDate(iso) {
    if (onSelectDate) onSelectDate(iso)
    else setSelectedInternal(iso)
  }

  useEffect(() => {
    if (selectedControlled != null) return
    const now = new Date()
    if (viewYear === now.getFullYear() && viewMonth === now.getMonth()) {
      setSelectedInternal(hojeISO())
    } else {
      setSelectedInternal(`${viewYear}-${pad2(viewMonth + 1)}-01`)
    }
  }, [viewYear, viewMonth, selectedControlled])

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

  return (
    <div className="grid gap-4 p-4 lg:grid-cols-2">
      <div className="rounded-xl border border-slate-100 bg-slate-50/60 p-3">
        <div className="mb-3 flex items-center justify-between gap-2">
          <button
            type="button"
            className="rounded-lg bg-white px-2.5 py-1.5 text-xs font-bold text-ink shadow-sm hover:bg-school-50 disabled:opacity-40"
            onClick={() => onShiftMonth?.(-1)}
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
            onClick={() => onShiftMonth?.(1)}
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
            const markers = dayMarkers[iso] || []
            const hasEv = markers.length > 0
            const tones = []
            markers.forEach((m) => {
              if (m.tone && !tones.includes(m.tone)) tones.push(m.tone)
            })
            return (
              <button
                key={iso}
                type="button"
                onClick={() => selectDate(iso)}
                className={[
                  'relative aspect-square rounded-lg text-xs font-semibold transition',
                  isSelected
                    ? 'bg-school-700 text-white shadow-sm ring-2 ring-school-700'
                    : isToday
                      ? 'bg-school-100 text-school-800'
                      : 'bg-white text-ink hover:bg-school-50',
                ].join(' ')}
              >
                {Number(iso.slice(-2))}
                {hasEv ? (
                  <span className="absolute bottom-1 left-1/2 flex -translate-x-1/2 items-center gap-0.5">
                    {tones.slice(0, 3).map((tone) => {
                      const colors = TONE_DOT[tone] || TONE_DOT.slate
                      return (
                        <span
                          key={tone}
                          className={`h-1.5 w-1.5 rounded-full ${
                            isSelected ? colors.selected : colors.idle
                          }`}
                        />
                      )
                    })}
                  </span>
                ) : null}
              </button>
            )
          })}
        </div>

        {legend.length > 0 ? (
          <div className="mt-3 flex flex-wrap items-center gap-3 px-0.5 text-[10px] font-semibold text-muted">
            {legend.map((item) => {
              const colors = TONE_DOT[item.tone] || TONE_DOT.slate
              return (
                <span key={item.label} className="inline-flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${colors.idle}`} /> {item.label}
                </span>
              )
            })}
          </div>
        ) : null}
      </div>

      <div className="flex min-h-[280px] flex-col rounded-xl border border-slate-100 bg-white p-3">
        <div className="mb-3 flex items-start justify-between gap-2">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-muted">
              {dayPanelTitle}
            </p>
            <p className="text-sm font-bold text-ink">{formatarDataBR(selectedDate)}</p>
          </div>
          {onEmptyDayAction ? (
            <button
              type="button"
              className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-ink hover:bg-slate-50"
              onClick={() => onEmptyDayAction(selectedDate)}
            >
              {emptyActionLabel}
            </button>
          ) : null}
        </div>

        {dayItems.length === 0 ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
            <p className="text-xs text-muted">{dayEmptyText}</p>
            {onEmptyDayAction ? (
              <button
                type="button"
                className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-700"
                onClick={() => onEmptyDayAction(selectedDate)}
              >
                {emptyActionLabel}
              </button>
            ) : null}
          </div>
        ) : (
          <ul className="flex-1 space-y-2 overflow-y-auto">
            {dayItems.map((item) => (
              <li key={item.id || item.key}>{renderDayItem?.(item)}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export { MESES, DIAS_SEM, pad2, hojeISO }
