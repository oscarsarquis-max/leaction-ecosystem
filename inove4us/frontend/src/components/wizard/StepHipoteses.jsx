export default function StepHipoteses({
  caminhos,
  selectedId,
  onSelect,
  hipotese,
  onGerarPlano,
  busy,
}) {
  return (
    <section className="mx-auto max-w-4xl animate-fade-in">
      <div className="mb-8 text-center">
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-brand-600">
          Etapa 3
        </p>
        <h1 className="font-display text-3xl font-bold text-bordo-deep sm:text-4xl">
          Hipóteses e Testes
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-bordo-soft sm:text-base">
          Nós propomos dois caminhos. Escolha um e receba a Hipótese de Aprendizado.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {(caminhos || []).map((caminho) => {
          const active = selectedId === caminho.id
          return (
            <button
              key={caminho.id}
              type="button"
              onClick={() => onSelect(caminho)}
              className={[
                'rounded-2xl border p-5 text-left transition shadow-soft',
                active
                  ? 'border-brand-600 bg-brand-50 ring-2 ring-brand-300'
                  : 'border-brand-200 bg-white/95 hover:border-brand-400',
              ].join(' ')}
            >
              <div className="mb-3 flex items-center justify-between gap-2">
                <span
                  className={[
                    'inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold',
                    active ? 'bg-brand-600 text-white' : 'bg-brand-100 text-bordo',
                  ].join(' ')}
                >
                  {caminho.id}
                </span>
                {active && (
                  <span className="text-xs font-bold uppercase tracking-wide text-brand-600">
                    Selecionado
                  </span>
                )}
              </div>
              <h2 className="font-display text-xl font-bold text-bordo-deep">
                {caminho.titulo}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-bordo-soft">{caminho.resumo}</p>
            </button>
          )
        })}
      </div>

      {hipotese && (
        <div className="mt-6 rounded-2xl border border-bordo/25 bg-gradient-to-br from-white to-brand-50 p-6 shadow-soft">
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.18em] text-bordo">
            Hipótese de Aprendizado
          </p>
          <p className="font-display text-lg leading-snug text-bordo-deep sm:text-xl">
            “{hipotese}”
          </p>
        </div>
      )}

      <div className="mt-6 flex justify-end">
        <button
          type="button"
          className="btn-primary"
          disabled={!selectedId || busy}
          onClick={onGerarPlano}
        >
          {busy ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Gerando…
            </>
          ) : (
            <>
              <i className="fa-solid fa-chalkboard-user" />
              Gerar Plano de Aula (EduScrum)
            </>
          )}
        </button>
      </div>
    </section>
  )
}
