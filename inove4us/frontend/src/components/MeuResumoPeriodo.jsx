import { useEffect, useState } from 'react'
import { api } from '../lib/api'

/**
 * Retrospectiva sob demanda — o professor abre quando quer.
 * Sem ranking, sem comparação com colegas, sem alerta de mudança de faixa.
 */
export default function MeuResumoPeriodo({ open, onClose }) {
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState('')
  const [resumo, setResumo] = useState(null)

  useEffect(() => {
    if (!open) {
      setResumo(null)
      setErro('')
      return undefined
    }
    let cancelled = false
    setLoading(true)
    setErro('')
    api
      .getMeuResumoPeriodo()
      .then((data) => {
        if (!cancelled) setResumo(data)
      })
      .catch((err) => {
        if (!cancelled) setErro(err?.message || 'Não foi possível abrir o resumo.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [open])

  if (!open) return null

  const selos = Array.isArray(resumo?.selos) ? resumo.selos : []

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-bordo-deep/50 p-4 sm:items-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="meu-resumo-titulo"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.()
      }}
    >
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-brand-200 bg-white p-6 shadow-soft sm:p-7">
        <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-brand-600">
          Retrospectiva
        </p>
        <h2
          id="meu-resumo-titulo"
          className="mt-2 font-display text-2xl font-bold leading-snug text-bordo-deep"
        >
          Meu resumo do período
        </h2>
        {resumo?.periodo?.rotulo ? (
          <p className="mt-1 text-sm text-bordo-soft">{resumo.periodo.rotulo}</p>
        ) : null}

        {loading ? (
          <p className="mt-6 text-sm text-bordo-soft">Montando seu retrato…</p>
        ) : null}
        {erro ? (
          <p className="mt-6 text-sm text-rose-800">{erro}</p>
        ) : null}

        {!loading && !erro && resumo ? (
          <div className="mt-5 space-y-4">
            {resumo.faixa_rotulo ? (
              <div className="rounded-2xl border border-brand-100 bg-brand-50/80 px-4 py-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-brand-600">
                  Sua faixa
                </p>
                <p className="mt-1 font-display text-xl font-bold text-bordo-deep">
                  {resumo.faixa_rotulo}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-bordo">
                  {resumo.faixa_texto}
                </p>
              </div>
            ) : (
              <p className="text-sm leading-relaxed text-bordo">{resumo.faixa_texto}</p>
            )}

            <div className="rounded-2xl border border-brand-100 bg-white px-4 py-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-brand-600">
                Em relação ao seu histórico
              </p>
              <p className="mt-2 text-sm leading-relaxed text-bordo">
                {resumo.evolucao_texto}
              </p>
            </div>

            {selos.length ? (
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-brand-600">
                  Selos desbloqueados
                </p>
                <ul className="mt-2 flex flex-wrap gap-2">
                  {selos.map((s) => (
                    <li
                      key={s.id}
                      className="rounded-full border border-violet-300 bg-violet-50 px-3 py-1 text-sm font-semibold text-violet-900"
                    >
                      {s.rotulo}
                    </li>
                  ))}
                </ul>
                {selos.some((s) => s.id === 'voz_ativa') ? (
                  <p className="mt-2 text-xs leading-relaxed text-bordo-soft">
                    Voz Ativa reconhece uma proposta sua que a escola incorporou ao
                    padrão — não só o volume de edições.
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="mt-6 flex justify-end">
          <button type="button" className="btn-primary !px-4 !py-2.5 text-sm" onClick={onClose}>
            Fechar
          </button>
        </div>
      </div>
    </div>
  )
}
