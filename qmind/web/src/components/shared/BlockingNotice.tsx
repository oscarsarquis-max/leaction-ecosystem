type Props = {
  title: string;
  reason: string;
  missingItem: string;
  actionText: string;
  onResolve: () => void;
};

/**
 * Explica por que uma fase está bloqueada e como desbloquear (só apresentação).
 */
export function BlockingNotice({
  title,
  reason,
  missingItem,
  actionText,
  onResolve,
}: Props) {
  return (
    <aside
      className="rounded-qmind-md border border-qmind-semantic-future bg-qmind-app p-5"
      style={{
        borderLeftWidth: 4,
        borderLeftColor: "var(--qmind-semantic-danger)",
      }}
      data-testid="blocking-notice"
      role="status"
    >
      <div className="flex items-start gap-3">
        <span
          className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-qmind-semantic-future text-sm font-bold text-qmind-semantic-danger"
          aria-hidden
        >
          !
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-qmind-main">{title}</h3>
          <p className="mt-2 text-sm text-qmind-text-muted">{reason}</p>
          <p className="mt-2 text-sm text-qmind-text-muted">{missingItem}</p>
          <button
            type="button"
            onClick={onResolve}
            className="mt-4 text-sm font-medium text-qmind-semantic-info transition-[var(--qmind-transition-subtle)] hover:underline"
          >
            {actionText}
          </button>
        </div>
      </div>
    </aside>
  );
}
