import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

function formatPct(n) {
  const v = Number(n)
  return Number.isFinite(v) ? `${Math.max(0, Math.min(100, Math.round(v)))}%` : '—'
}

function formatDias(resumo) {
  if (!resumo || resumo.dias_restantes == null) return 'Sem prazo no calendário'
  const d = Number(resumo.dias_restantes)
  if (resumo.atrasado || d < 0) return `${Math.abs(d)} dia(s) em atraso`
  if (d === 0) return 'Encerra hoje'
  return `${d} dia(s) restantes`
}

/**
 * Busca e seleção de desafios (próprios + aceitos) — fica antes do grafo.
 */
export default function DesafioSeletor({ className = '' }) {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const rootRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    const t = window.setTimeout(() => setDebouncedQ(q.trim()), 220)
    return () => window.clearTimeout(t)
  }, [q])

  const load = useCallback(async (query) => {
    setLoading(true)
    setError('')
    try {
      const data = await api.listDesafios({ q: query || undefined, limit: 40 })
      setItems(Array.isArray(data?.desafios) ? data.desafios : [])
      setHighlight(0)
    } catch (err) {
      setError(err?.message || 'Não foi possível carregar os desafios.')
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load(debouncedQ)
  }, [debouncedQ, load])

  useEffect(() => {
    function onDocClick(e) {
      if (!rootRef.current?.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocClick)
    return () => document.removeEventListener('mousedown', onDocClick)
  }, [])

  const filteredHint = useMemo(() => {
    if (loading) return 'Buscando…'
    if (error) return error
    if (!items.length) {
      return debouncedQ
        ? 'Nenhum desafio encontrado para esta busca.'
        : 'Ainda não há desafios. Crie com + Desafio ou aceite um convite.'
    }
    return `${items.length} desafio${items.length === 1 ? '' : 's'}`
  }, [loading, error, items.length, debouncedQ])

  function openMesa(d) {
    if (!d?.id) return
    setOpen(false)
    navigate(`/desafios/${d.id}`)
  }

  function onKeyDown(e) {
    if (!open && (e.key === 'ArrowDown' || e.key === 'Enter')) {
      setOpen(true)
      return
    }
    if (!open) return
    if (e.key === 'Escape') {
      setOpen(false)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlight((h) => Math.min(items.length - 1, h + 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlight((h) => Math.max(0, h - 1))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const pick = items[highlight]
      if (pick) openMesa(pick)
    }
  }

  return (
    <section
      ref={rootRef}
      className={`mx-auto max-w-6xl ${className}`}
      aria-label="Selecionar desafio"
    >
      <div className="rounded-2xl border border-brand-200 bg-white p-4 shadow-soft sm:p-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
              Seus desafios
            </p>
            <h2 className="mt-1 font-display text-xl font-bold text-bordo-deep sm:text-2xl">
              Abrir a mesa do desafio
            </h2>
            <p className="mt-1 max-w-xl text-sm text-bordo-soft">
              Busque pelos desafios que você criou ou aceitou — inclusive os que ainda aguardam
              registro de aulas. Ao selecionar, retoma a gestão da execução sem nova IA.
            </p>
          </div>
          <p className="text-xs font-semibold text-bordo-soft">{filteredHint}</p>
        </div>

        <div className="relative mt-4">
          <label htmlFor="desafio-busca" className="sr-only">
            Buscar desafio
          </label>
          <div className="flex gap-2">
            <div className="relative min-w-0 flex-1">
              <span
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-bordo-soft"
                aria-hidden
              >
                <i className="fa-solid fa-magnifying-glass text-sm" />
              </span>
              <input
                ref={inputRef}
                id="desafio-busca"
                type="search"
                value={q}
                onChange={(e) => {
                  setQ(e.target.value)
                  setOpen(true)
                }}
                onFocus={() => setOpen(true)}
                onKeyDown={onKeyDown}
                placeholder="Buscar por título, tema ou problema…"
                className="field-input w-full !py-3 pl-10 pr-3 text-sm"
                autoComplete="off"
                aria-expanded={open}
                aria-controls="desafio-lista"
                aria-autocomplete="list"
              />
            </div>
            <button
              type="button"
              className="btn-ghost shrink-0 !px-3"
              onClick={() => {
                setOpen((v) => !v)
                inputRef.current?.focus()
              }}
              aria-label={open ? 'Fechar lista' : 'Abrir lista'}
            >
              <i className={`fa-solid fa-chevron-${open ? 'up' : 'down'}`} />
            </button>
          </div>

          {open ? (
            <ul
              id="desafio-lista"
              role="listbox"
              className="absolute z-30 mt-2 max-h-80 w-full overflow-y-auto rounded-xl border border-brand-200 bg-white py-1 shadow-lg"
            >
              {loading ? (
                <li className="px-4 py-3 text-sm text-bordo-soft">Carregando…</li>
              ) : null}
              {!loading && error ? (
                <li className="px-4 py-3 text-sm text-rose-700">{error}</li>
              ) : null}
              {!loading && !error && !items.length ? (
                <li className="px-4 py-3 text-sm text-bordo-soft">{filteredHint}</li>
              ) : null}
              {!loading &&
                items.map((d, idx) => {
                  const r = d.resumo || {}
                  const active = idx === highlight
                  return (
                    <li key={d.id} role="option" aria-selected={active}>
                      <button
                        type="button"
                        className={[
                          'flex w-full flex-col gap-1 px-4 py-3 text-left transition',
                          active ? 'bg-brand-50' : 'hover:bg-brand-50/70',
                        ].join(' ')}
                        onMouseEnter={() => setHighlight(idx)}
                        onClick={() => openMesa(d)}
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold text-bordo-deep">
                            {d.titulo || 'Desafio sem título'}
                          </span>
                          <span
                            className={[
                              'rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide',
                              d.sou_dono
                                ? 'bg-emerald-50 text-emerald-800'
                                : 'bg-amber-50 text-amber-900',
                            ].join(' ')}
                          >
                            {d.sou_dono ? 'Meu' : 'Atribuído'}
                          </span>
                          {d.precisa_registrar_aulas || !(r.n_aulas > 0) ? (
                            <span className="rounded-full bg-sky-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-sky-900">
                              Aguardando aulas
                            </span>
                          ) : null}
                          {d.tema ? (
                            <span className="text-[11px] font-medium text-bordo-soft">
                              {d.tema}
                            </span>
                          ) : null}
                        </div>
                        <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-bordo-soft">
                          {d.precisa_registrar_aulas || !(r.n_aulas > 0) ? (
                            <span>Cards prontos · registre as aulas para executar</span>
                          ) : (
                            <>
                              <span>Progresso {formatPct(r.progresso_pct)}</span>
                              <span>
                                Aulas {r.n_concluido || 0}/{r.n_aulas || 0}
                              </span>
                              <span>{formatDias(r)}</span>
                            </>
                          )}
                          {!d.sou_dono && d.dono_nome ? (
                            <span>de {d.dono_nome}</span>
                          ) : null}
                        </div>
                      </button>
                    </li>
                  )
                })}
            </ul>
          ) : null}
        </div>

        {!open && items.length > 0 ? (
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {items.slice(0, 4).map((d) => {
              const r = d.resumo || {}
              return (
                <li key={`chip-${d.id}`}>
                  <button
                    type="button"
                    onClick={() => openMesa(d)}
                    className="flex w-full flex-col rounded-xl border border-brand-100 bg-brand-50/40 px-3 py-3 text-left transition hover:border-brand-300 hover:bg-brand-50"
                  >
                    <span className="text-sm font-bold leading-snug text-bordo-deep">
                      {d.titulo || 'Desafio'}
                    </span>
                    <span className="mt-1 text-[11px] text-bordo-soft">
                      {d.sou_dono ? 'Meu desafio' : 'Aceito'}
                      {d.precisa_registrar_aulas || !(r.n_aulas > 0)
                        ? ' · Aguardando aulas'
                        : ` · ${formatPct(r.progresso_pct)} · ${formatDias(r)}`}
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : null}
      </div>
    </section>
  )
}
