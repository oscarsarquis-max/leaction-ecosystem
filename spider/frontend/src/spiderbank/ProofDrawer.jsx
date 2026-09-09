import { useEffect } from "react";

function formatWhen(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString("pt-BR");
  } catch {
    return String(value);
  }
}

function Step({ step }) {
  return (
    <li data-testid={`provenance-step-${step.code}`}>
      <p className="sb-step-label">
        {step.order}. {step.label}
      </p>
      <p className="sb-step-meta">
        {step.status} · {formatWhen(step.occurredAt)}
      </p>
      {step.detail ? <p className="sb-step-detail">{step.detail}</p> : null}
    </li>
  );
}

const CHECKS = [
  { key: "link", label: "Link genérico" },
  { key: "click", label: "Clique" },
  { key: "clickId", label: "Click ID" },
  { key: "origin", label: "Origem identificada" },
  { key: "page", label: "Página adquirida" },
  { key: "fp", label: "Fingerprint" },
  { key: "ctx", label: "Context ID" },
];

export default function ProofDrawer({ open, onClose, payload, click, page, ctx }) {
  useEffect(() => {
    if (!open) return undefined;
    function onKey(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="sb-drawer-layer" data-testid="provenance-panel">
      <button type="button" className="sb-drawer-backdrop" aria-label="Fechar prova" onClick={onClose} />
      <aside className="sb-drawer" role="dialog" aria-modal="true" aria-labelledby="proof-title">
        <header className="sb-drawer-head">
          <h2 id="proof-title">Como este contexto nasceu?</h2>
          <button type="button" className="sb-ghost" onClick={onClose}>
            Fechar
          </button>
        </header>
        <p className="sb-drawer-lead">Prova da apresentação. Não faz parte da conversa com o cliente.</p>
        <ul className="sb-checks">
          {CHECKS.map((item) => (
            <li key={item.key}>
              <span aria-hidden="true">✓</span> {item.label}
            </li>
          ))}
        </ul>
        <div className="sb-grid">
          <article data-testid="before-click">
            <h3>Antes do clique</h3>
            <dl>
              <dt>Link</dt>
              <dd data-testid="before-link">{payload?.gatewayUrl || "http://127.0.0.1:8080/go"}</dd>
              <dt>Context ID</dt>
              <dd>INEXISTENTE</dd>
              <dt>Click ID</dt>
              <dd>INEXISTENTE</dd>
            </dl>
          </article>
          <article data-testid="after-click">
            <h3>Depois do clique</h3>
            <dl>
              <dt>Click ID</dt>
              <dd data-testid="click-id">{click.clickId || "INEXISTENTE"}</dd>
              <dt>Context ID</dt>
              <dd data-testid="context-id">{click.contextId || ctx || "INEXISTENTE"}</dd>
              <dt>Origem</dt>
              <dd data-testid="proof-origin">{payload?.partnerPublicName || "—"}</dd>
              <dt>Reportagem</dt>
              <dd data-testid="source-title">{page.sourceTitle || "não adquirida"}</dd>
              <dt>Created At</dt>
              <dd data-testid="created-at">{formatWhen(click.createdAt)}</dd>
              <dt>Página</dt>
              <dd data-testid="source-url">{page.sourceUrl || page.sourceOrigin || "indisponível"}</dd>
              <dt>Fingerprint</dt>
              <dd data-testid="fingerprint">{page.contentFingerprint || "não calculado"}</dd>
            </dl>
          </article>
        </div>
        <ol className="sb-steps">
          {(payload?.provenance || []).map((step) => (
            <Step key={step.code} step={step} />
          ))}
        </ol>
      </aside>
    </div>
  );
}
