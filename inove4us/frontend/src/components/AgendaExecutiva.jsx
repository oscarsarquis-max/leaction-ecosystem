import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import DictationField from './DictationField'

function hasPlanData(planData) {
  if (!planData || typeof planData !== 'object') return false
  return Object.keys(planData).length > 0
}

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

function pad2(n) {
  return n < 10 ? `0${n}` : String(n)
}

function hojeISO() {
  const d = new Date()
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function mesAnoISO(y, m) {
  return `${y}-${pad2(m + 1)}`
}

function diaDeEvento(iso) {
  return String(iso || '').slice(0, 10)
}

function formatarDataBR(iso) {
  const p = String(iso || '').slice(0, 10).split('-')
  if (p.length !== 3) return iso || '—'
  return `${p[2]}/${p[1]}/${p[0]}`
}

const STATUS_STYLE = {
  planejado: 'bg-white/70 text-bordo',
  em_execucao: 'bg-white/80 text-amber-950',
  concluido: 'bg-white/80 text-emerald-900',
}

const STATUS_LABEL = {
  planejado: 'Planejado',
  em_execucao: 'Em execução',
  concluido: 'Concluído',
}

/** Separação visual: Desafio (âmbar) × Dia a Dia (verde) × geral (neutro). */
const TIPO_CARD = {
  aula_eduscrum: {
    card: 'border-amber-300 bg-amber-50 hover:border-amber-400 hover:bg-amber-100/80',
    label: 'text-amber-800',
    chip: 'bg-amber-200/80 text-amber-950',
    nome: 'Desafio · EduScrum',
  },
  aula_dia: {
    card: 'border-emerald-300 bg-emerald-50 hover:border-emerald-400 hover:bg-emerald-100/80',
    label: 'text-emerald-800',
    chip: 'bg-emerald-200/80 text-emerald-950',
    nome: 'Dia a Dia · ciclo rápido',
  },
  geral: {
    card: 'border-brand-100 bg-brand-50/50 hover:border-brand-300 hover:bg-brand-50',
    label: 'text-brand-600',
    chip: 'bg-brand-100 text-bordo',
    nome: 'Compromisso',
  },
}

function tipoVisual(tipo) {
  return TIPO_CARD[tipo] || TIPO_CARD.geral
}

const TURNO_LABEL = { manha: 'Manhã', tarde: 'Tarde', noite: 'Noite' }
const MODO_LABEL = {
  continuidade: 'Prosseguimento',
  reinicio: 'Começar do início',
}

/**
 * Agenda executiva — calendário mensal + lista/registro de compromissos.
 */
export default function AgendaExecutiva({ refreshKey = 0, onChanged }) {
  const navigate = useNavigate()
  const hoje = hojeISO()
  const now = new Date()
  const [viewYear, setViewYear] = useState(now.getFullYear())
  const [viewMonth, setViewMonth] = useState(now.getMonth())
  const [selectedDate, setSelectedDate] = useState(hoje)
  const [eventos, setEventos] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listAgendaEventos(mesAnoISO(viewYear, viewMonth))
      setEventos(data.eventos || [])
    } catch (err) {
      setError(err.message || 'Falha ao carregar agenda')
      setEventos([])
    } finally {
      setLoading(false)
    }
  }, [viewYear, viewMonth])

  useEffect(() => {
    load()
  }, [load, refreshKey])

  const diasComEvento = useMemo(() => {
    const map = {}
    eventos.forEach((ev) => {
      const d = diaDeEvento(ev.data_evento)
      if (!d) return
      if (!map[d]) {
        map[d] = { done: true, desafio: false, dia: false, geral: false }
      }
      if (ev.status !== 'concluido') map[d].done = false
      if (ev.tipo === 'aula_eduscrum') map[d].desafio = true
      else if (ev.tipo === 'aula_dia') map[d].dia = true
      else map[d].geral = true
    })
    return map
  }, [eventos])

  const eventosDoDia = useMemo(
    () => eventos.filter((ev) => diaDeEvento(ev.data_evento) === selectedDate),
    [eventos, selectedDate],
  )

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

  function shiftMonth(delta) {
    const d = new Date(viewYear, viewMonth + delta, 1)
    setViewYear(d.getFullYear())
    setViewMonth(d.getMonth())
  }

  function openNew() {
    setModal({
      mode: 'new',
      titulo: '',
      data_evento: selectedDate,
      nota_texto: '',
    })
  }

  function openEdit(ev) {
    setModal({
      mode: 'edit',
      id_evento: ev.id_evento,
      titulo: ev.titulo || '',
      data_evento: diaDeEvento(ev.data_evento),
      nota_texto: ev.nota_texto || '',
    })
  }

  /**
   * Clique no card: retoma execução se houver plan_data; senão Desafio (aula) ou edição.
   */
  function handleEventClick(ev) {
    if (!ev) return
    if (ev.status === 'concluido') {
      openEdit(ev)
      return
    }
    if (hasPlanData(ev.plan_data)) {
      navigate(`/execucao/${ev.id_evento}`, {
        state: {
          plan_data: ev.plan_data,
          kanban_state: ev.kanban_state,
          evento: ev,
        },
      })
      return
    }
    if (ev.tipo === 'aula_eduscrum') {
      navigate('/desafio')
      return
    }
    if (ev.tipo === 'aula_dia') {
      const aulaId = ev.meta_json?.aula_simples_id
      if (aulaId) {
        navigate(`/dia-a-dia/${aulaId}`)
        return
      }
      navigate('/dia-a-dia')
      return
    }
    openEdit(ev)
  }

  async function saveModal(e) {
    e.preventDefault()
    if (!modal) return
    const titulo = (modal.titulo || '').trim()
    if (!titulo) {
      setError('Informe o título do compromisso.')
      return
    }
    const payload = {
      titulo,
      data_evento: `${modal.data_evento}T12:00:00`,
      nota_texto: (modal.nota_texto || '').trim(),
    }
    try {
      if (modal.mode === 'new') {
        await api.createAgendaEvento(payload)
      } else {
        await api.updateAgendaEvento(modal.id_evento, payload)
      }
      setModal(null)
      await load()
      onChanged?.()
    } catch (err) {
      setError(err.message || 'Falha ao salvar compromisso')
    }
  }

  async function deleteModal() {
    if (!modal?.id_evento) return
    if (!window.confirm('Excluir este compromisso?')) return
    try {
      await api.deleteAgendaEvento(modal.id_evento)
      setModal(null)
      await load()
      onChanged?.()
    } catch (err) {
      setError(err.message || 'Falha ao excluir')
    }
  }

  return (
    <section className="mx-auto mb-8 max-w-6xl animate-fade-in print:hidden">
      <div className="rounded-2xl border border-brand-200 bg-white/95 p-4 shadow-soft sm:p-5">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
              Painel do professor
            </p>
            <h2 className="font-display text-xl font-bold text-bordo-deep sm:text-2xl">
              Agenda executiva
            </h2>
            <p className="mt-1 text-xs text-bordo-soft">
              Calendário e registro de eventos / compromissos da sua prática inovadora.
            </p>
          </div>
          {loading ? (
            <span className="text-[11px] font-semibold text-bordo-soft">Carregando…</span>
          ) : null}
        </div>

        {error && !modal ? (
          <p className="mb-3 rounded-lg bg-brand-50 px-3 py-2 text-xs font-semibold text-bordo">
            {error}
          </p>
        ) : null}

        <div className="grid gap-4 lg:grid-cols-2">
          {/* Calendário */}
          <div className="rounded-xl border border-brand-100 bg-brand-50/40 p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <button
                type="button"
                className="rounded-lg bg-white px-2.5 py-1.5 text-xs font-bold text-bordo shadow-sm hover:bg-brand-50"
                onClick={() => shiftMonth(-1)}
                aria-label="Mês anterior"
              >
                ‹
              </button>
              <p className="text-sm font-bold text-bordo-deep">
                {MESES[viewMonth]} {viewYear}
              </p>
              <button
                type="button"
                className="rounded-lg bg-white px-2.5 py-1.5 text-xs font-bold text-bordo shadow-sm hover:bg-brand-50"
                onClick={() => shiftMonth(1)}
                aria-label="Próximo mês"
              >
                ›
              </button>
            </div>
            <div className="grid grid-cols-7 gap-1 text-center">
              {DIAS_SEM.map((d) => (
                <div key={d} className="py-1 text-[10px] font-bold uppercase text-bordo-soft">
                  {d}
                </div>
              ))}
              {cells.map((iso, idx) => {
                if (!iso) {
                  return <div key={`b-${idx}`} className="aspect-square" />
                }
                const isToday = iso === hoje
                const isSelected = iso === selectedDate
                const dayInfo = diasComEvento[iso]
                const hasEv = Boolean(dayInfo)
                return (
                  <button
                    key={iso}
                    type="button"
                    onClick={() => setSelectedDate(iso)}
                    className={[
                      'relative aspect-square rounded-lg text-xs font-semibold transition',
                      isSelected
                        ? 'bg-bordo text-white shadow-soft'
                        : isToday
                          ? 'bg-brand-200 text-bordo-deep'
                          : 'bg-white text-bordo hover:bg-brand-100',
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
                        {dayInfo.geral ? (
                          <span
                            className={`h-1.5 w-1.5 rounded-full ${
                              isSelected ? 'bg-white' : 'bg-brand-600'
                            }`}
                            title="Compromisso"
                          />
                        ) : null}
                      </span>
                    ) : null}
                  </button>
                )
              })}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3 px-0.5 text-[10px] font-semibold text-bordo-soft">
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-amber-500" /> Desafio
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500" /> Dia a Dia
              </span>
              <span className="inline-flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-brand-600" /> Outros
              </span>
            </div>
          </div>

          {/* Lista do dia */}
          <div className="flex min-h-[280px] flex-col rounded-xl border border-brand-100 bg-white p-3">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide text-bordo-soft">
                  Compromissos
                </p>
                <p className="text-sm font-bold text-bordo-deep">{formatarDataBR(selectedDate)}</p>
              </div>
              <button type="button" className="btn-primary !px-3 !py-1.5 text-xs" onClick={openNew}>
                + Novo
              </button>
            </div>

            {eventosDoDia.length === 0 ? (
              <p className="flex flex-1 flex-col items-center justify-center gap-1 text-center text-xs text-bordo-soft">
                <span>Nenhum compromisso neste dia.</span>
                <span>
                  Use <strong>+</strong> para registrar.
                </span>
              </p>
            ) : (
              <ul className="flex-1 space-y-2 overflow-y-auto">
                {eventosDoDia.map((ev) => {
                  const retomavel = ev.status !== 'concluido' && hasPlanData(ev.plan_data)
                  const visual = tipoVisual(ev.tipo)
                  return (
                  <li key={ev.id_evento}>
                    <button
                      type="button"
                      onClick={() => handleEventClick(ev)}
                      className={`w-full rounded-xl border px-3 py-2.5 text-left transition ${visual.card}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-bold text-bordo-deep">{ev.titulo}</p>
                        <span
                          className={`shrink-0 rounded-full px-2 py-0.5 text-[9px] font-bold uppercase ${
                            STATUS_STYLE[ev.status] || STATUS_STYLE.planejado
                          }`}
                        >
                          {STATUS_LABEL[ev.status] || ev.status || 'Planejado'}
                        </span>
                      </div>
                      {ev.tipo === 'aula_eduscrum' || ev.tipo === 'aula_dia' ? (
                        <p
                          className={`mt-1 text-[10px] font-semibold uppercase tracking-wide ${visual.label}`}
                        >
                          {visual.nome}
                          {retomavel && ev.tipo === 'aula_eduscrum' ? ' · Retomar' : ''}
                        </p>
                      ) : null}
                      {(ev.turma || ev.turno || ev.modo_execucao) ? (
                        <p className="mt-1 text-[11px] text-bordo">
                          {[
                            ev.turma,
                            TURNO_LABEL[ev.turno] || ev.turno,
                            MODO_LABEL[ev.modo_execucao] || ev.modo_execucao,
                          ]
                            .filter(Boolean)
                            .join(' · ')}
                        </p>
                      ) : null}
                      {retomavel && ev.tipo !== 'aula_eduscrum' && ev.tipo !== 'aula_dia' ? (
                        <p className="mt-1 text-[10px] font-semibold uppercase tracking-wide text-brand-600">
                          Retomar execução
                        </p>
                      ) : null}
                      {ev.nota_texto ? (
                        <p className="mt-1 line-clamp-2 text-[11px] text-bordo-soft">
                          {ev.nota_texto}
                        </p>
                      ) : null}
                    </button>
                  </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>
      </div>

      {modal ? (
        <div
          className="fixed inset-0 z-[70] flex items-end justify-center bg-bordo-deep/45 p-4 sm:items-center"
          role="dialog"
          aria-modal="true"
          onClick={(e) => {
            if (e.target === e.currentTarget) setModal(null)
          }}
        >
          <form
            onSubmit={saveModal}
            className="w-full max-w-md rounded-2xl border border-brand-200 bg-white p-5 shadow-soft"
          >
            <h3 className="font-display text-lg font-bold text-bordo-deep">
              {modal.mode === 'new' ? 'Novo compromisso' : 'Editar compromisso'}
            </h3>

            <label className="mt-4 block text-xs font-bold uppercase tracking-wide text-bordo">
              Título
            </label>
            <input
              className="field-input mt-1"
              value={modal.titulo}
              onChange={(e) => setModal((m) => ({ ...m, titulo: e.target.value }))}
              placeholder="Ex.: Reunião de sprint com a turma"
              required
            />

            <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-bordo">
              Data
            </label>
            <input
              type="date"
              className="field-input mt-1"
              value={modal.data_evento}
              onChange={(e) => setModal((m) => ({ ...m, data_evento: e.target.value }))}
              required
            />

            <label className="mt-3 block text-xs font-bold uppercase tracking-wide text-bordo">
              Notas / detalhes
            </label>
            <div className="mt-1">
              <DictationField
                as="textarea"
                rows={4}
                className="field-input min-h-[100px] resize-y"
                value={modal.nota_texto}
                onChange={(v) => setModal((m) => ({ ...m, nota_texto: v }))}
                placeholder="Digite ou dite observações do compromisso…"
              />
            </div>

            {error && modal ? (
              <p className="mt-2 text-xs font-semibold text-brand-700">{error}</p>
            ) : null}

            <div className="mt-5 flex flex-wrap justify-between gap-2">
              {modal.mode === 'edit' ? (
                <button
                  type="button"
                  className="rounded-xl px-3 py-2 text-xs font-semibold text-rose-600 hover:bg-rose-50"
                  onClick={deleteModal}
                >
                  Excluir
                </button>
              ) : (
                <span />
              )}
              <div className="flex gap-2">
                <button type="button" className="btn-ghost !px-4 !py-2 text-sm" onClick={() => setModal(null)}>
                  Cancelar
                </button>
                <button type="submit" className="btn-primary !px-4 !py-2 text-sm">
                  Salvar
                </button>
              </div>
            </div>
          </form>
        </div>
      ) : null}
    </section>
  )
}
