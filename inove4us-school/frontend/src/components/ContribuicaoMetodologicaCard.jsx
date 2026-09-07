import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

/**
 * Contribuição metodológica — saiu do topo do Radar e vive no Editor Pedagógico
 * (aba Metodologias), junto da curadoria. Agregado anônimo do recorte semanal.
 */
export default function ContribuicaoMetodologicaCard() {
  const [contribuicao, setContribuicao] = useState(null)
  const [periodo, setPeriodo] = useState(null)

  useEffect(() => {
    let cancelled = false
    const now = new Date()
    const diff = (now.getDay() + 6) % 7
    const ini = new Date(now.getFullYear(), now.getMonth(), now.getDate() - diff)
    const fim = new Date(ini.getFullYear(), ini.getMonth(), ini.getDate() + 6)
    const iso = (d) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    const q = new URLSearchParams({
      data_inicio: iso(ini),
      data_fim: iso(fim),
    })
    ;(async () => {
      try {
        const res = await fetch(`/api/pedagogico/calendario-pedagogico/resumo?${q}`, {
          credentials: 'include',
        })
        const body = await res.json().catch(() => ({}))
        if (cancelled) return
        if (res.ok) {
          setContribuicao(body.contribuicao || null)
          setPeriodo({ inicio: iso(ini), fim: iso(fim) })
        } else {
          setContribuicao(null)
        }
      } catch {
        if (!cancelled) setContribuicao(null)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const fmt = (iso) => {
    const p = String(iso || '').slice(0, 10).split('-')
    if (p.length !== 3) return iso || ''
    return `${p[2]}/${p[1]}`
  }

  return (
    <section className="rounded-xl border border-violet-200 bg-violet-50/50 p-4 shadow-panel">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-violet-800">
            Curadoria · agregado da escola
          </p>
          <h2 className="mt-1 text-base font-semibold text-ink">Contribuição metodológica</h2>
        </div>
        <p className="text-xs text-muted">
          Semana {periodo ? `${fmt(periodo.inicio)}–${fmt(periodo.fim)}` : ''} · sem identificação
          de professores.{' '}
          <Link to="/" className="font-semibold text-violet-800 underline">
            Ver no Radar
          </Link>
        </p>
      </div>
      {contribuicao && contribuicao.aulas_com_carimbo > 0 ? (
        <div className="mt-3 grid gap-3 sm:grid-cols-3">
          <article className="rounded-lg border border-violet-200 bg-white p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-violet-800">
              Roteiro-base
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-ink">
              {contribuicao.percentual_roteiro_base ?? 0}%
            </p>
            <p className="mt-1 text-xs text-muted">
              {contribuicao.aulas_canonica} aula
              {contribuicao.aulas_canonica === 1 ? '' : 's'} sem personalização
            </p>
          </article>
          <article className="rounded-lg border border-violet-200 bg-white p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-violet-800">
              Com personalização
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-ink">
              {contribuicao.percentual_personalizacao ?? 0}%
            </p>
            <p className="mt-1 text-xs text-muted">
              {contribuicao.aulas_personalizada} aula
              {contribuicao.aulas_personalizada === 1 ? '' : 's'} com edição ou card próprio
            </p>
          </article>
          <article className="rounded-lg border border-violet-200 bg-white p-3">
            <p className="text-[10px] font-bold uppercase tracking-wide text-violet-800">
              Sugestões incorporadas
            </p>
            <p className="mt-1 text-2xl font-semibold tabular-nums text-ink">
              {contribuicao.sugestoes_incorporadas ?? 0}
            </p>
            <p className="mt-1 text-xs text-muted">Propostas validadas neste período</p>
          </article>
        </div>
      ) : (
        <p className="mt-3 text-sm text-muted">
          Ainda não há aulas com carimbo de contribuição nesta semana.
          {contribuicao?.sugestoes_incorporadas
            ? ` ${contribuicao.sugestoes_incorporadas} sugestão${
                contribuicao.sugestoes_incorporadas === 1 ? '' : 'ões'
              } incorporada${
                contribuicao.sugestoes_incorporadas === 1 ? '' : 's'
              } no período.`
            : ''}
        </p>
      )}
    </section>
  )
}
