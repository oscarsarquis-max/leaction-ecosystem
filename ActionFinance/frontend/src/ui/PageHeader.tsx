import type { ReactNode } from "react";

export function PageHeader({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-head">
      <div>
        <h1 id="page-title" tabIndex={-1}>
          {title}
        </h1>
        {hint ? <p className="hint">{hint}</p> : null}
      </div>
      {action}
    </div>
  );
}
