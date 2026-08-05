import type { ReactNode } from "react";

type Props = {
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
};

export function ResultCard({ title, children, footer }: Props) {
  return (
    <div className="qm-panel p-5 sm:p-6" data-testid="result-card">
      {title ? (
        <h2 className="font-display text-xl text-[var(--qm-ink)]">{title}</h2>
      ) : null}
      <div className={title ? "mt-4" : undefined}>{children}</div>
      {footer ? <div className="mt-5">{footer}</div> : null}
    </div>
  );
}
