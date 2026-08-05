type Props = {
  title: string;
  explanation: string;
  example: string;
  actionText: string;
  onAction: () => void;
};

/**
 * Estado vazio orientado — explica o que fazer e como começar (apresentação).
 */
export function GuidedEmptyState({
  title,
  explanation,
  example,
  actionText,
  onAction,
}: Props) {
  return (
    <div
      className="flex flex-col items-center rounded-qmind border border-qmind-semantic-current bg-qmind-surface px-6 py-10 text-center shadow-qmind"
      data-testid="guided-empty-state"
    >
      <div className="w-full max-w-md">
        <h2 className="text-xl font-bold text-qmind-main">{title}</h2>
        <p className="mt-3 text-sm leading-relaxed text-qmind-text-muted">
          {explanation}
        </p>
        <p className="mt-4 rounded-qmind-sm border border-qmind-semantic-current bg-qmind-app px-4 py-3 text-left text-sm leading-relaxed text-qmind-text-main">
          <span className="font-semibold text-qmind-main">Exemplo: </span>
          {example}
        </p>
        <button
          type="button"
          onClick={onAction}
          className="mt-6 inline-flex items-center justify-center rounded-qmind bg-qmind-info px-4 py-2.5 text-sm font-semibold text-white transition-[var(--qmind-transition-subtle)] hover:brightness-95"
        >
          {actionText}
        </button>
      </div>
    </div>
  );
}
