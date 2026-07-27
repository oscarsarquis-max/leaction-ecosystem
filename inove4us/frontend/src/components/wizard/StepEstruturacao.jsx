import { useMemo, useState } from 'react'

function SkeletonLines() {
  return (
    <div className="space-y-4">
      {[0, 1, 2].map((i) => (
        <div key={i} className="overflow-hidden rounded-xl border border-brand-100 bg-brand-50/80 p-4">
          <div className="mb-3 h-3 w-1/3 animate-pulse rounded bg-brand-200" />
          <div className="space-y-2">
            <div className="h-2.5 w-full animate-pulse rounded bg-brand-100" />
            <div className="h-2.5 w-5/6 animate-pulse rounded bg-brand-100" />
            <div className="h-2.5 w-2/3 animate-pulse rounded bg-brand-100" />
          </div>
        </div>
      ))}
    </div>
  )
}

export default function StepEstruturacao({
  loading,
  causas,
  resumoAnalise,
  referencial,
  onNext,
  fallback,
  onComplementar,
  complementBusy,
}) {
  const [complemento, setComplemento] = useState('')
  const pendente = useMemo(
    () => (causas || []).find((c) => c?.precisa_complemento),
    [causas],
  )

  return (
    <section className="mx-auto max-w-3xl animate-fade-in">
      <div className="mb-8 text-center">
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-brand-600">
          Etapa 2
        </p>
        <h1 className="font-display text-3xl font-bold text-bordo-deep sm:text-4xl">
          A Estruturação
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-bordo-soft sm:text-base">
          {loading
            ? 'Lendo o seu relato e preparando caminhos metodológicos para a turma (cerca de 1 minuto)…'
            : 'Causas e hipóteses a partir do seu problema, para orientar a escolha do caminho.'}
        </p>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-brand-200 bg-white/90 p-6 shadow-soft">
          <div className="mb-6 flex flex-col items-center gap-3">
            <div className="relative h-14 w-14">
              <div className="absolute inset-0 animate-ping rounded-full bg-brand-400/30" />
              <div className="absolute inset-0 animate-spin rounded-full border-[3px] border-brand-100 border-t-brand-600" />
            </div>
            <p className="text-sm font-semibold text-brand-600">
              Organizando causas e hipóteses…
            </p>
            <p className="text-xs text-bordo-soft">
              Em seguida você verá três opções de caminho — costuma levar cerca de 1 minuto.
            </p>
          </div>
          <SkeletonLines />
        </div>
      ) : (
        <div className="space-y-5">
          {referencial?.categoria_prob && (
            <div className="rounded-xl border border-bordo/20 bg-bordo/5 px-4 py-3 text-sm text-bordo">
              <span className="font-semibold">Casos semelhantes na nossa base:</span>{' '}
              {referencial.grupo_prob} › {referencial.categoria_prob}
              {fallback ? (
                <span className="ml-2 text-xs text-bordo-soft">(sugestão local)</span>
              ) : null}
            </div>
          )}

          {resumoAnalise ? (
            <div className="rounded-2xl border border-brand-200 bg-white/95 p-5 shadow-soft">
              <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-brand-600">
                Resumo da análise
              </p>
              <p className="text-sm leading-relaxed text-bordo-deep">{resumoAnalise}</p>
            </div>
          ) : null}

          <ul className="space-y-3">
            {(causas || []).map((causa, idx) => (
              <li
                key={`${causa.titulo}-${idx}`}
                className="rounded-2xl border border-brand-200 bg-white/95 p-5 shadow-soft"
              >
                <div className="mb-2 flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
                    {idx + 1}
                  </span>
                  <h2 className="font-display text-lg font-bold text-bordo-deep">
                    {causa.titulo}
                  </h2>
                </div>
                <p className="text-sm leading-relaxed text-bordo-soft">{causa.descricao}</p>
              </li>
            ))}
          </ul>

          {pendente ? (
            <div className="rounded-2xl border border-dashed border-brand-400 bg-brand-50/60 p-5">
              <p className="mb-1 text-xs font-bold uppercase tracking-[0.16em] text-brand-700">
                Complemento opcional
              </p>
              <p className="mb-3 text-sm leading-relaxed text-bordo-deep">
                {pendente.pergunta_complemento ||
                  'Quer acrescentar um detalhe observável para aprofundar esta hipótese?'}
              </p>
              <textarea
                className="field-input min-h-[88px] w-full resize-y"
                value={complemento}
                onChange={(e) => setComplemento(e.target.value)}
                placeholder="Ex.: no diagnóstico de campo o 6º ano B notou cheiro forte perto de um bueiro…"
                disabled={complementBusy}
              />
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <p className="text-xs text-bordo-soft">
                  Soma ao relato original e gera uma nova análise (1 desafio).
                </p>
                <button
                  type="button"
                  className="btn-primary"
                  disabled={complementBusy || complemento.trim().length < 12}
                  onClick={() => onComplementar?.(complemento.trim())}
                >
                  {complementBusy ? 'Reestruturando…' : 'Complementar e reestruturar'}
                </button>
              </div>
            </div>
          ) : null}

          <div className="flex justify-end pt-2">
            <button
              type="button"
              className="btn-primary"
              onClick={onNext}
              disabled={complementBusy}
            >
              Avançar para Hipóteses
              <i className="fa-solid fa-arrow-right" />
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
