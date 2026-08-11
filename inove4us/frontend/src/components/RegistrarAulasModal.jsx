import { useEffect, useMemo, useState } from 'react'
import { createPortal } from 'react-dom'
import { api } from '../lib/api'
import { isSchemaPendingError, listarMinhasTurmas } from '../services/instituicoesService'

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

function pad2(n) {
  return n < 10 ? `0${n}` : String(n)
}

function hojeISO() {
  const d = new Date()
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function emptySlot(overrides = {}) {
  return {
    key: `s-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
    data: hojeISO(),
    turma: '',
    turno: 'tarde',
    modo_execucao: 'continuidade',
    card_ids: [],
    escopos: {},
    ...overrides,
  }
}

function cardsFromDesafio(desafio, cardsMesa = []) {
  const seen = new Set()
  const out = []
  const plan = desafio?.plan_data
  const plano = plan?.plano || plan?.plano_eduscrum || plan || {}
  const fontes = [
    ...(Array.isArray(plano?.tarefas_kanban) ? plano.tarefas_kanban : []),
    ...(Array.isArray(cardsMesa) ? cardsMesa : []),
  ]
  for (const t of fontes) {
    const id = String(t?.id || '').trim()
    if (!id || seen.has(id)) continue
    seen.add(id)
    out.push({
      id,
      titulo: (t.titulo || 'Card').trim() || 'Card',
      objetivo: (t.objetivo || t.descricao || '').trim(),
    })
  }
  return out
}

/**
 * Acrescentar / ratificar aulas em um desafio já existente (ou primeiro registro).
 * Em execução o plano pode mudar a qualquer momento.
 */
export default function RegistrarAulasModal({
  open,
  onClose,
  onDone,
  desafio,
  cardsMesa = [],
  missao = '',
  planoSession = null,
  suggestTurma = '',
}) {
  const [slots, setSlots] = useState(() => [emptySlot()])
  const [busy, setBusy] = useState(false)
  const [erro, setErro] = useState('')
  const [turmasCadastro, setTurmasCadastro] = useState([])
  const [turmasLoading, setTurmasLoading] = useState(false)

  const catalogo = useMemo(
    () => cardsFromDesafio(desafio, cardsMesa),
    [desafio, cardsMesa],
  )

  useEffect(() => {
    if (!open) return
    setErro('')
    setSlots([
      emptySlot({
        turma: suggestTurma || '',
        modo_execucao: suggestTurma ? 'continuidade' : 'reinicio',
      }),
    ])
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
          console.warn('[RegistrarAulasModal] turmas:', err?.message)
        }
        setTurmasCadastro([])
      })
      .finally(() => {
        if (!cancelled) setTurmasLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open, suggestTurma, desafio?.id])

  useEffect(() => {
    if (!open) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [open])

  if (!open || typeof document === 'undefined') return null

  function updateSlot(key, patch) {
    setSlots((prev) => prev.map((s) => (s.key === key ? { ...s, ...patch } : s)))
  }

  function toggleCard(key, cardId) {
    setSlots((prev) =>
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

  function updateEscopo(key, cardId, nota) {
    setSlots((prev) =>
      prev.map((s) => {
        if (s.key !== key) return s
        return { ...s, escopos: { ...(s.escopos || {}), [cardId]: nota } }
      }),
    )
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setErro('')
    if (!catalogo.length) {
      setErro('Não há cards no plano para associar.')
      return
    }
    const aulas = slots.map((s) => ({
      data: s.data,
      turma: (s.turma || '').trim(),
      turno: s.turno,
      modo_execucao: s.modo_execucao,
      card_ids: Array.isArray(s.card_ids) ? s.card_ids.map(String) : [],
      escopos: s.escopos || {},
    }))
    for (const a of aulas) {
      if (!a.data) {
        setErro('Cada aula precisa de uma data.')
        return
      }
      if (!a.turma) {
        setErro('Informe a turma de cada aula.')
        return
      }
      if (!a.card_ids.length) {
        setErro(`Aula ${a.turma}: associe ao menos um card.`)
        return
      }
      for (const cid of a.card_ids) {
        if (!String(a.escopos[cid] || '').trim()) {
          const titulo = catalogo.find((c) => c.id === cid)?.titulo || cid
          setErro(`Aula ${a.turma}: declare o escopo no card «${titulo}».`)
          return
        }
      }
    }

    const missaoTxt = (missao || desafio?.titulo || 'Aula · método inove4us').trim()
    const titulo =
      missaoTxt.length > 140 ? `Método inove4us · ${missaoTxt.slice(0, 120)}…` : `Método inove4us · ${missaoTxt}`

    setBusy(true)
    try {
      const planData = desafio?.plan_data || null
      const hipotese = desafio?.hipotese || planData?.hipotese || ''
      const problema = desafio?.problema || planData?.problema || ''
      const data = await api.registrarAulas({
        aulas,
        titulo,
        desafio_id: desafio?.id || undefined,
        nota_texto: [
          hipotese ? `Hipótese: ${hipotese}` : null,
          problema ? `Problema: ${problema}` : null,
        ]
          .filter(Boolean)
          .join('\n'),
        plano_session: planoSession || undefined,
        ...(desafio?.disciplina_id != null ? { disciplina_id: desafio.disciplina_id } : {}),
        ...(desafio?.causas != null ? { causas: desafio.causas } : {}),
        meta_json: {
          missao: missaoTxt,
          hipotese: hipotese || '',
          problema: problema || '',
          ...(desafio?.id ? { desafio_id: desafio.id } : {}),
        },
        plan_data: planData,
        kanban_state: {
          tarefas: catalogo.map((c) => ({
            id: c.id,
            titulo: c.titulo,
            objetivo: c.objetivo,
            coluna: 'para_fazer',
          })),
        },
        tema: desafio?.tema || undefined,
      })
      onDone?.(data)
      onClose?.()
    } catch (err) {
      setErro(err?.message || 'Falha ao registrar aulas.')
    } finally {
      setBusy(false)
    }
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center overflow-y-auto bg-bordo-deep/55 p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="registrar-aulas-title"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) {
          e.currentTarget.dataset.closeOnClick = '1'
        }
      }}
      onClick={(e) => {
        if (
          e.target === e.currentTarget &&
          e.currentTarget.dataset.closeOnClick === '1' &&
          !busy
        ) {
          onClose?.()
        }
        delete e.currentTarget.dataset.closeOnClick
      }}
    >
      <form
        onSubmit={handleSubmit}
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
        className="my-2 w-full max-w-2xl rounded-2xl border border-brand-200 bg-white p-5 shadow-soft sm:my-4 sm:p-6"
        style={{ maxHeight: 'min(92vh, 920px)', overflowY: 'auto' }}
      >
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
          Plano em execução
        </p>
        <h2 id="registrar-aulas-title" className="mt-1 font-display text-2xl font-bold text-bordo-deep">
          Acrescentar / ratificar aulas
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-bordo-soft">
          O plano pode mudar a qualquer momento: inclua novas datas, turmas ou turnos e vincule os
          cards com o escopo de cada turma. As aulas entram neste mesmo desafio.
        </p>
        {missao ? (
          <p className="mt-3 whitespace-pre-wrap rounded-xl bg-brand-50 px-4 py-3 text-sm text-bordo">
            <strong>Missão:</strong> {missao}
          </p>
        ) : null}

        <ul className="mt-5 space-y-4">
          {slots.map((slot, idx) => (
            <li key={slot.key} className="rounded-xl border border-brand-100 bg-brand-50/40 p-4">
              <div className="mb-3 flex items-center justify-between gap-2">
                <p className="text-[11px] font-bold uppercase tracking-wide text-bordo">
                  Aula {idx + 1}
                </p>
                {slots.length > 1 ? (
                  <button
                    type="button"
                    className="text-xs font-bold text-rose-600 hover:underline"
                    onClick={() =>
                      setSlots((prev) => (prev.length <= 1 ? prev : prev.filter((s) => s.key !== slot.key)))
                    }
                  >
                    Remover
                  </button>
                ) : null}
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="text-[10px] font-bold uppercase text-bordo-soft">Data</label>
                  <input
                    type="date"
                    className="field-input mt-1 !py-2.5"
                    value={slot.data}
                    onChange={(e) => updateSlot(slot.key, { data: e.target.value })}
                    required
                    disabled={busy}
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold uppercase text-bordo-soft">Turma</label>
                  {turmasCadastro.length > 0 ? (
                    <select
                      className="field-input mt-1 !py-2.5"
                      value={slot.turma}
                      onChange={(e) => updateSlot(slot.key, { turma: e.target.value })}
                      required
                      disabled={busy || turmasLoading}
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
                      className="field-input mt-1 !py-2.5"
                      value={slot.turma}
                      onChange={(e) => updateSlot(slot.key, { turma: e.target.value })}
                      placeholder={
                        turmasLoading
                          ? 'Carregando turmas…'
                          : 'Cadastre turmas em Instituições, ou digite aqui'
                      }
                      required
                      disabled={busy}
                    />
                  )}
                </div>
                <div>
                  <label className="text-[10px] font-bold uppercase text-bordo-soft">Turno</label>
                  <select
                    className="field-input mt-1 !py-2.5"
                    value={slot.turno}
                    onChange={(e) => updateSlot(slot.key, { turno: e.target.value })}
                    disabled={busy}
                  >
                    {TURNO_OPTS.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-bold uppercase text-bordo-soft">Caminho</label>
                  <select
                    className="field-input mt-1 !py-2.5"
                    value={slot.modo_execucao}
                    onChange={(e) => updateSlot(slot.key, { modo_execucao: e.target.value })}
                    disabled={busy}
                  >
                    {MODO_OPTS.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <p className="mt-2 text-[12px] text-bordo-soft">
                {MODO_OPTS.find((m) => m.id === slot.modo_execucao)?.hint}
              </p>

              <div className="mt-4 border-t border-brand-100 pt-3">
                <p className="text-[10px] font-bold uppercase tracking-wide text-bordo">
                  Cards desta aula
                </p>
                <ul className="mt-2 space-y-2">
                  {catalogo.map((card) => {
                    const checked = (slot.card_ids || []).includes(card.id)
                    const checkId = `mesa-card-${slot.key}-${card.id}`
                    const escopoId = `mesa-escopo-${slot.key}-${card.id}`
                    return (
                      <li key={`${slot.key}-${card.id}`} className="rounded-lg bg-white p-3">
                        <div className="flex items-start gap-2">
                          <input
                            id={checkId}
                            type="checkbox"
                            className="mt-1"
                            checked={checked}
                            onChange={() => toggleCard(slot.key, card.id)}
                            disabled={busy}
                          />
                          <label htmlFor={checkId} className="min-w-0 flex-1 cursor-pointer">
                            <span className="block text-sm font-semibold text-bordo-deep">
                              {card.titulo}
                            </span>
                            {card.objetivo ? (
                              <span className="mt-1 block whitespace-pre-wrap text-[12px] text-bordo-soft">
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
                              rows={3}
                              value={slot.escopos?.[card.id] || ''}
                              onChange={(e) => updateEscopo(slot.key, card.id, e.target.value)}
                              placeholder="Escopo desta turma neste card…"
                              required
                              disabled={busy}
                            />
                          </div>
                        ) : null}
                      </li>
                    )
                  })}
                </ul>
              </div>
            </li>
          ))}
        </ul>

        <button
          type="button"
          className="btn-ghost mt-4 w-full !py-2.5 text-sm"
          onClick={() =>
            setSlots((prev) => [
              ...prev,
              emptySlot({
                turma: prev[prev.length - 1]?.turma || suggestTurma || '',
                turno: 'tarde',
                modo_execucao: 'continuidade',
              }),
            ])
          }
          disabled={busy}
        >
          + Outra aula
        </button>

        {erro ? (
          <p className="mt-4 rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">
            {erro}
          </p>
        ) : null}

        <div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-end">
          <button
            type="button"
            className="btn-ghost min-h-[48px] w-full sm:w-auto"
            disabled={busy}
            onClick={() => !busy && onClose?.()}
          >
            Cancelar
          </button>
          <button type="submit" className="btn-primary min-h-[48px] w-full sm:w-auto" disabled={busy}>
            {busy ? 'Salvando…' : 'Salvar aulas no desafio'}
          </button>
        </div>
      </form>
    </div>,
    document.body,
  )
}
