type Props = {
  title: string;
  nextStepText: string;
  onContinue: () => void;
};

/**
 * Celebração discreta ao concluir uma etapa (sem confetes / gamificação infantil).
 */
export function MilestoneCelebration({
  title,
  nextStepText,
  onContinue,
}: Props) {
  return (
    <section
      className="rounded-qmind-md border border-qmind-future bg-qmind-surface p-5 shadow-qmind-card"
      style={{ borderTopWidth: 4, borderTopColor: "var(--qmind-semantic-success)" }}
      data-testid="milestone-celebration"
    >
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-qmind-semantic-success">
        Etapa concluída
      </p>
      <h2 className="mt-2 text-lg font-semibold text-qmind-main">{title}</h2>
      <p className="mt-2 text-sm text-qmind-text-muted">{nextStepText}</p>
      <button
        type="button"
        onClick={onContinue}
        className="mt-4 inline-flex items-center justify-center rounded-qmind-md bg-qmind-semantic-info px-4 py-2.5 text-sm font-semibold text-white transition-[var(--qmind-transition-subtle)] hover:brightness-95"
      >
        Continuar
      </button>
    </section>
  );
}
