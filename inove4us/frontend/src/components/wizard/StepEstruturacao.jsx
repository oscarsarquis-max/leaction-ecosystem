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

export default function StepEstruturacao({ loading, causas, referencial, onNext, fallback }) {
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
            ? 'Estamos cruzando o seu relato com a base de problemas da inove4us…'
            : 'Causas ocultas identificadas a partir do seu problema e da base de referência.'}
        </p>
      </div>

      {loading ? (
        <div className="rounded-2xl border border-brand-200 bg-white/90 p-6 shadow-soft">
          <div className="mb-6 flex flex-col items-center gap-3">
            <div className="relative h-14 w-14">
              <div className="absolute inset-0 animate-ping rounded-full bg-brand-400/30" />
              <div className="absolute inset-0 animate-spin rounded-full border-[3px] border-brand-100 border-t-brand-600" />
            </div>
            <p className="text-sm font-semibold text-brand-600">Analisando causas ocultas…</p>
          </div>
          <SkeletonLines />
        </div>
      ) : (
        <div className="space-y-5">
          {referencial?.categoria_prob && (
            <div className="rounded-xl border border-bordo/20 bg-bordo/5 px-4 py-3 text-sm text-bordo">
              <span className="font-semibold">Âncora na base:</span>{' '}
              {referencial.grupo_prob} › {referencial.categoria_prob}
              {fallback ? (
                <span className="ml-2 text-xs text-bordo-soft">(modo local)</span>
              ) : null}
            </div>
          )}

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

          <div className="flex justify-end pt-2">
            <button type="button" className="btn-primary" onClick={onNext}>
              Avançar para Hipóteses
              <i className="fa-solid fa-arrow-right" />
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
