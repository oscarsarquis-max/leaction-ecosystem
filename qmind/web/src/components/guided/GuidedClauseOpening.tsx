import type { ConsultiveOpening } from "@/lib/guidedNarrative";

type Props = {
  opening: ConsultiveOpening;
  onStart: () => void;
};

export function GuidedClauseOpening({ opening, onStart }: Props) {
  return (
    <div className="space-y-6" data-testid="guided-clause-opening">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--qm-muted)]">
          Etapa {opening.major} · Antes das perguntas
        </p>
        <h3 className="font-display text-2xl text-[var(--qm-ink)] sm:text-3xl">
          {opening.businessName}
        </h3>
        <p className="text-base leading-relaxed text-[var(--qm-muted)]">
          {opening.whatIsEvaluated}
        </p>
      </header>

      <section className="rounded-qmind-sm border border-[var(--qm-line)] bg-[var(--qm-app)]/50 px-4 py-4">
        <h4 className="text-sm font-semibold text-[var(--qm-ink)]">
          Objetivo desta etapa
        </h4>
        <p className="mt-1.5 text-sm leading-relaxed text-[var(--qm-muted)]">
          {opening.objective}
        </p>
      </section>

      <section className="space-y-2">
        <h4 className="text-sm font-semibold text-[var(--qm-ink)]">
          Por que isso importa
        </h4>
        <p className="text-sm leading-relaxed text-[var(--qm-muted)]">
          {opening.whyItMatters}
        </p>
      </section>

      <div className="grid gap-4 sm:grid-cols-2">
        <section>
          <h4 className="text-sm font-semibold text-[var(--qm-ink)]">
            Benefícios esperados
          </h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
            {opening.expectedBenefits.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </section>
        <section>
          <h4 className="text-sm font-semibold text-[var(--qm-ink)]">
            Problemas que esta etapa ajuda a evitar
          </h4>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
            {opening.problemsAvoided.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </section>
      </div>

      <section className="rounded-qmind-sm bg-[var(--qm-surface-soft)] px-4 py-3">
        <h4 className="text-sm font-semibold text-[var(--qm-ink)]">
          Resultado esperado ao final
        </h4>
        <p className="mt-1 text-sm leading-relaxed text-[var(--qm-muted)]">
          {opening.expectedResult}
        </p>
      </section>

      <p className="text-xs text-[var(--qm-muted)]">
        Linguagem de negócio — não é cópia da norma. Responda com o que a
        empresa faz de verdade.
      </p>

      <button
        type="button"
        className="qm-btn-primary"
        data-testid="clause-opening-start"
        onClick={onStart}
      >
        Começar esta etapa
      </button>
    </div>
  );
}
