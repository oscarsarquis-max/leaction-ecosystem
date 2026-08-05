export type ChecklistItem = {
  id: string;
  label: string;
  done: boolean;
};

type Props = {
  title?: string;
  items: ChecklistItem[];
  pending?: string[];
  resolveHint?: string;
};

export function GuidedChecklist({
  title = "Nesta fase",
  items,
  pending = [],
  resolveHint,
}: Props) {
  return (
    <aside className="qm-panel p-5" data-testid="guided-checklist">
      <h2 className="font-display text-xl text-[var(--qm-ink)]">{title}</h2>
      <ul className="mt-3 space-y-2 text-sm">
        {items.map((item) => (
          <li key={item.id} className="flex gap-2 text-[var(--qm-muted)]">
            <span
              className={item.done ? "text-[var(--qm-success)]" : undefined}
              aria-hidden
            >
              {item.done ? "✓" : "○"}
            </span>
            <span className={item.done ? "text-[var(--qm-ink)]" : undefined}>
              {item.label}
            </span>
          </li>
        ))}
      </ul>
      {pending.length > 0 ? (
        <div className="mt-4">
          <p className="text-sm font-semibold text-[var(--qm-ink)]">Pendências</p>
          <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
            {pending.slice(0, 5).map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
          {resolveHint ? (
            <p className="mt-2 text-sm text-[var(--qm-muted)]">{resolveHint}</p>
          ) : null}
        </div>
      ) : (
        <p className="mt-4 text-sm text-[var(--qm-muted)]">
          Nada crítico pendente — bom momento para avançar.
        </p>
      )}
    </aside>
  );
}
