export function SectionFrame({ id, testId, variant = "chapter", children }) {
  return (
    <section className={`sx-chapter sx-chapter-${variant}`} id={id} data-testid={testId}>
      <div className="sx-container">{children}</div>
    </section>
  );
}

export function SectionEyebrow({ children }) {
  return <p className="sx-kicker">{children}</p>;
}

export function SectionHeading({ as: Tag = "h2", testId, children }) {
  return (
    <Tag className={Tag === "h1" ? "sx-display" : "sx-heading"} data-testid={testId}>
      {children}
    </Tag>
  );
}

export function NarrativeGrid({ template, children }) {
  return <div className={`sx-grid sx-grid-${template}`}>{children}</div>;
}

export function EvidencePanel({ label, children }) {
  return (
    <aside className="sx-evidence-panel">
      {label ? <p className="sx-label">{label}</p> : null}
      {children}
    </aside>
  );
}

export function FlowNode({
  active,
  dimmed,
  kind,
  interactive,
  selected,
  status,
  onClick,
  testId,
  children,
}) {
  const className = [
    "sx-flow-node",
    kind ? `sx-node-${kind}` : "",
    active || selected ? "is-on" : "",
    dimmed ? "is-dim" : "",
    interactive ? "is-interactive" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const body = (
    <>
      {status ? <span className="sx-node-eye">{status}</span> : null}
      <span className="sx-node-label">{children}</span>
    </>
  );
  if (interactive) {
    return (
      <button
        type="button"
        className={className}
        aria-pressed={!!selected}
        onClick={onClick}
        data-testid={testId}
      >
        {body}
      </button>
    );
  }
  return (
    <span className={className} data-testid={testId}>
      {body}
    </span>
  );
}

export function StatusIndicator({ tone = "done", children }) {
  return <span className={`sx-status-dot sx-status-dot-${tone}`}>{children}</span>;
}

export function Callout({ testId, children }) {
  return (
    <aside className="sx-callout" data-testid={testId}>
      {children}
    </aside>
  );
}

export function ExpandableDetail({ open, label, onToggle, children, testId }) {
  return (
    <div className="sx-expand">
      <button
        type="button"
        className="sx-btn sx-btn-secondary"
        aria-expanded={open}
        onClick={onToggle}
        data-testid={testId}
      >
        {label}
      </button>
      {open ? <div className="sx-expand-panel">{children}</div> : null}
    </div>
  );
}
