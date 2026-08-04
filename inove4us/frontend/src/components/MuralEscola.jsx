import { useCallback, useEffect, useState } from 'react'
import { api } from '../lib/api'

function formatQuando(iso) {
  if (!iso) return null
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return null
    return d.toLocaleString('pt-BR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return null
  }
}

/**
 * Mural da escola — faixa no topo da Mesa (separado de grafo/agenda).
 * Comunicados empurrados pelo inove4us School (somente leitura + ciência).
 */
export default function MuralEscola() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.getMural()
      setItems(Array.isArray(data?.items) ? data.items : [])
    } catch (err) {
      setError(err.message || 'Não foi possível carregar o mural')
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function marcarCiencia(id) {
    setBusyId(id)
    try {
      await api.marcarCienciaMural(id)
      setItems((prev) => prev.filter((it) => it.id !== id))
    } catch {
      /* keep */
    } finally {
      setBusyId(null)
    }
  }

  if (loading && items.length === 0) {
    return (
      <section className="mb-8" aria-busy="true" aria-label="Mural da escola">
        <div className="h-24 animate-pulse rounded-2xl border border-brand-100 bg-brand-50/60" />
      </section>
    )
  }

  if (!items.length && !error) return null

  return (
    <section className="mb-8" aria-label="Mural da escola">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-brand-600">
            Mural da escola
          </p>
          <h2 className="mt-0.5 text-lg font-bold text-bordo">Comunicados da instituição</h2>
        </div>
      </div>

      {error ? (
        <p className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {error}
        </p>
      ) : null}

      <ul className="space-y-3">
        {items.map((it) => {
          const quando = formatQuando(it.data_hora_inicio)
          return (
            <li
              key={it.id}
              className="rounded-2xl border border-teal-200 bg-gradient-to-br from-teal-50 to-white px-4 py-3 shadow-soft"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="inline-flex rounded-full bg-teal-700 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">
                      Comunicado da Escola
                    </span>
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-teal-800">
                      {it.tipo_label || it.tipo}
                    </span>
                    {quando ? (
                      <span className="text-xs text-bordo-soft/90">{quando}</span>
                    ) : (
                      <span className="text-xs text-bordo-soft/80">Só no mural</span>
                    )}
                  </div>
                  <p className="mt-1.5 font-semibold text-bordo">{it.titulo}</p>
                  {it.descricao ? (
                    <p className="mt-1 text-sm leading-relaxed text-bordo-soft/90">
                      {it.descricao}
                    </p>
                  ) : null}
                </div>
                <button
                  type="button"
                  disabled={busyId === it.id}
                  onClick={() => void marcarCiencia(it.id)}
                  className="shrink-0 rounded-lg border border-teal-300 bg-white px-3 py-1.5 text-xs font-semibold text-teal-900 hover:bg-teal-50 disabled:opacity-60"
                >
                  {busyId === it.id ? '…' : 'Ciência'}
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
