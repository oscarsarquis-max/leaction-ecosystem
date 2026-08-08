import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { TAB_ACTIVE, TAB_INACTIVE } from '../lib/tabs'
import TeacherCardPreview from './TeacherCardPreview'

/**
 * Espelho da Mesa (abas Mesa do Professor + Diário de bordo).
 * Extraído do Radar para reuso na Equipe — mesmo endpoint e comportamento.
 */
export default function LessonMirrorModal({ planoId, instituicaoId, onClose }) {
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('mesa')

  useEffect(() => {
    if (!planoId || !instituicaoId) return undefined
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const res = await fetch(
          `/api/instituicoes/${instituicaoId}/planos-espelhados/${planoId}`,
          { credentials: 'include' },
        )
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(body.error || 'Falha ao carregar espelho')
        if (!cancelled) setDetail(body)
      } catch (err) {
        if (!cancelled) setError(err.message || 'Erro')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [planoId, instituicaoId])

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = prev
    }
  }, [])

  if (typeof document === 'undefined') return null

  const diario = Array.isArray(detail?.diario_bordo) ? detail.diario_bordo : []

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center overflow-y-auto bg-ink/50 p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose?.()
      }}
    >
      <div className="my-2 w-full max-w-5xl rounded-2xl border border-slate-200 bg-panel shadow-panel sm:my-4">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 bg-white px-4 py-3 sm:px-5">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-school-700">
              Espelho da Mesa
            </p>
            <h2 className="mt-0.5 text-lg font-semibold text-ink">
              {detail?.turma_nome || 'Aula'}
              {detail?.metodologia_nome ? ` · ${detail.metodologia_nome}` : ''}
            </h2>
            {detail?.has_sugestao_curadoria ? (
              <p className="mt-1 text-xs font-semibold text-violet-700">
                Esta aula gerou insumo para a matriz curricular.
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-semibold text-muted hover:bg-slate-50"
          >
            Fechar
          </button>
        </div>

        <div className="flex gap-1 border-b border-slate-100 bg-white px-3 pt-2">
          {[
            { id: 'mesa', label: 'Mesa do Professor' },
            { id: 'diario', label: 'Diário de bordo' },
          ].map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={[
                'rounded-t-lg px-3 py-2 text-sm font-semibold',
                tab === t.id ? TAB_ACTIVE : TAB_INACTIVE,
              ].join(' ')}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="max-h-[min(78vh,820px)] overflow-y-auto p-3 sm:p-4">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted">Carregando espelho…</p>
          ) : error ? (
            <p className="py-10 text-center text-sm text-red-700">{error}</p>
          ) : tab === 'mesa' ? (
            <TeacherCardPreview
              mesa={detail?.mesa}
              meta={detail || {}}
              avisos={detail?.avisos_formados}
            />
          ) : (
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <h3 className="text-sm font-semibold text-ink">
                Anotações de transição de estado
              </h3>
              <p className="mt-1 text-xs text-muted">
                Diário de bordo registrado pelo professor nas movimentações dos cards.
              </p>
              {diario.length ? (
                <ul className="mt-4 space-y-2">
                  {diario.map((e, i) => (
                    <li
                      key={`${e.card}-${i}`}
                      className="rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2.5"
                    >
                      <p className="text-[10px] font-bold uppercase tracking-wide text-muted">
                        {e.card}
                        {e.de || e.para
                          ? ` · ${e.de || '?'} → ${e.para || '?'}`
                          : ''}
                      </p>
                      <p className="mt-1 whitespace-pre-wrap text-sm text-ink">{e.nota}</p>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-4 text-sm text-muted">
                  Nenhuma anotação de transição sincronizada ainda.
                </p>
              )}
              {detail?.texto_sugestao ? (
                <div className="mt-4 rounded-lg border border-violet-200 bg-violet-50 px-3 py-3">
                  <p className="text-[10px] font-bold uppercase tracking-wide text-violet-700">
                    Sugestão à coordenação (fechamento)
                  </p>
                  <p className="mt-1 text-sm text-ink">{detail.texto_sugestao}</p>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
