const RANKING_META = {
  encaixe_direto: {
    label: 'Opção 1 · Encaixe Direto',
    hint: 'A mais tradicional',
  },
  encaixe_alternativo: {
    label: 'Opção 2 · Encaixe Alternativo',
    hint: 'Mudança de dinâmica',
  },
  adaptacao_hibrida: {
    label: 'Opção 3 · Adaptação Híbrida',
    hint: 'Teoria + caso do mundo real',
  },
}

function metaFor(caminho, index) {
  const key =
    caminho?.tipo_ranking ||
    ['encaixe_direto', 'encaixe_alternativo', 'adaptacao_hibrida'][index]
  return RANKING_META[key] || {
    label: `Opção ${index + 1}`,
    hint: '',
  }
}

export default function StepHipoteses({
  caminhos,
  selectedId,
  onSelect,
  hipotese,
  onGerarPlano,
  busy,
}) {
  return (
    <section className="mx-auto max-w-5xl animate-fade-in">
      <div className="mb-8 text-center">
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-brand-600">
          Etapa 3
        </p>
        <h1 className="font-display text-3xl font-bold text-bordo-deep sm:text-4xl">
          Ranking de Adequação
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-bordo-soft sm:text-base">
          Três vias ancoradas nas Metodologias Inov-Ativas. Escolha uma e receba a
          Hipótese de Aprendizado com plano EduScrum.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {(caminhos || []).map((caminho, index) => {
          const active = selectedId === caminho.id
          const meta = metaFor(caminho, index)
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
              <div className="mb-3 flex items-start justify-between gap-2">
                <span
                  className={[
                    'inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold',
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

              <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-brand-600">
                {meta.label}
              </p>
              {meta.hint ? (
                <p className="mt-0.5 text-xs text-bordo-soft">{meta.hint}</p>
              ) : null}

              {caminho.metodologia ? (
                <p className="mt-3 text-xs font-semibold text-bordo">
                  {caminho.metodologia}
                  {caminho.quadrante ? (
                    <span className="font-normal text-bordo-soft"> · {caminho.quadrante}</span>
                  ) : null}
                </p>
              ) : null}

              <h2 className="mt-2 font-display text-lg font-bold text-bordo-deep">
                {caminho.titulo}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-bordo-soft">
                {caminho.por_que_usar || caminho.resumo}
              </p>

              {caminho.dinamica_sala ? (
                <p className="mt-3 border-t border-brand-100 pt-3 text-xs leading-relaxed text-bordo-soft">
                  <span className="font-semibold text-bordo">Em sala: </span>
                  {caminho.dinamica_sala}
                </p>
              ) : null}

              {caminho.tipo_ranking === 'adaptacao_hibrida' && caminho.ancoragem_de_para ? (
                <p className="mt-2 text-xs leading-relaxed text-bordo/80">
                  <span className="font-semibold">De/Para: </span>
                  {caminho.ancoragem_de_para}
                </p>
              ) : null}
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
