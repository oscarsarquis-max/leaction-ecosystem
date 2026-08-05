type Props = {
  title: string;
  description: string;
  actionText: string;
  onClick: () => void;
};

/**
 * CTA principal da tela — próximo passo evidente (componente de apresentação).
 */
export function NextBestAction({
  title,
  description,
  actionText,
  onClick,
}: Props) {
  return (
    <section
      className="rounded-qmind border border-qmind-semantic-current bg-qmind-surface p-5 shadow-qmind transition-[var(--qmind-transition-subtle)] sm:p-6"
      data-testid="next-best-action"
    >
      <p className="text-xs font-bold uppercase tracking-[0.12em] text-qmind-semantic-current">
        Próxima etapa
      </p>
      <h2 className="mt-2 text-xl font-bold text-qmind-main">{title}</h2>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-qmind-text-muted">
        {description}
      </p>
      <button
        type="button"
        onClick={onClick}
        className="mt-5 inline-flex items-center justify-center rounded-qmind bg-qmind-semantic-info px-4 py-2.5 text-sm font-semibold text-white transition-[var(--qmind-transition-subtle)] hover:brightness-95"
      >
        {actionText}
      </button>
    </section>
  );
}
