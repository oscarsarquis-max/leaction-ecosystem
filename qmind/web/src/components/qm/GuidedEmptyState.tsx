import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type Action =
  | { label: string; onClick: () => void }
  | { label: string; to: string };

type Props = {
  title: string;
  why: string;
  example: string;
  howToStart: string;
  action?: Action;
  children?: ReactNode;
};

export function GuidedEmptyState({
  title,
  why,
  example,
  howToStart,
  action,
  children,
}: Props) {
  return (
    <div className="qm-panel qm-panel--dashed px-6 py-8" data-testid="guided-empty-state">
      <h2 className="font-display text-xl text-[var(--qm-ink)]">{title}</h2>
      <dl className="mt-4 space-y-3 text-sm">
        <div>
          <dt className="font-semibold text-[var(--qm-ink)]">Por que isso é necessário</dt>
          <dd className="mt-1 text-[var(--qm-muted)]">{why}</dd>
        </div>
        <div>
          <dt className="font-semibold text-[var(--qm-ink)]">Exemplo do que será criado</dt>
          <dd className="mt-1 text-[var(--qm-muted)]">{example}</dd>
        </div>
        <div>
          <dt className="font-semibold text-[var(--qm-ink)]">Como começar</dt>
          <dd className="mt-1 text-[var(--qm-muted)]">{howToStart}</dd>
        </div>
      </dl>
      {children}
      {action ? (
        "to" in action ? (
          <Link to={action.to} className="qm-btn-primary mt-5 inline-flex">
            {action.label}
          </Link>
        ) : (
          <button type="button" className="qm-btn-primary mt-5" onClick={action.onClick}>
            {action.label}
          </button>
        )
      ) : null}
    </div>
  );
}
