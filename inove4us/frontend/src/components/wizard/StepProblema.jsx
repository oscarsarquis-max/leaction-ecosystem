import DictationField from '../DictationField'

export default function StepProblema({
  problema,
  contexto,
  onProblemaChange,
  onContextoChange,
  onSubmit,
  busy,
  error,
}) {
  return (
    <section className="mx-auto max-w-2xl animate-fade-in">
      <div className="mb-8 text-center">
        <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-brand-600">
          Etapa 1
        </p>
        <h1 className="font-display text-3xl font-bold text-bordo-deep sm:text-4xl">
          O Problema
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-bordo-soft sm:text-base">
          Declare a dor real da sua turma. Iremos estruturar o seu problema, sugerir
          melhorias e ajudar a implementá-las de forma ágil. Você também pode ditar pelo
          microfone.
        </p>
      </div>

      <div className="space-y-5 rounded-2xl border border-brand-200 bg-white/90 p-6 shadow-soft">
        <div>
          <label htmlFor="problema" className="field-label">
            Declaração do problema
          </label>
          <DictationField
            as="textarea"
            id="problema"
            rows={5}
            className="field-input resize-y"
            placeholder="Ex.: Os alunos se distraem com o celular e não conseguem sustentar atenção nas atividades em grupo…"
            value={problema}
            onChange={onProblemaChange}
          />
        </div>

        <div>
          <label htmlFor="contexto" className="field-label">
            Localização / contexto
          </label>
          <DictationField
            id="contexto"
            type="text"
            className="field-input"
            placeholder="Ex.: 8º ano B · Matemática · turno manhã"
            value={contexto}
            onChange={onContextoChange}
          />
        </div>

        {error && (
          <p className="rounded-xl border border-brand-300 bg-brand-50 px-3 py-2 text-sm text-bordo">
            {error}
          </p>
        )}

        <button
          type="button"
          className="btn-primary w-full sm:w-auto"
          disabled={busy || problema.trim().length < 12}
          onClick={onSubmit}
        >
          {busy ? (
            <>
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
              Estruturando…
            </>
          ) : (
            <>
              <i className="fa-solid fa-wand-magic-sparkles" />
              Estruturar com IA
            </>
          )}
        </button>
      </div>
    </section>
  )
}
