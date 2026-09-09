import { useEffect } from "react";

function formatSources(sources) {
  if (!sources || sources.length === 0) return "AUSENTE";
  return sources.join(" + ");
}

export default function UnderstandingDrawer({ open, onClose, understanding }) {
  useEffect(() => {
    if (!open) return undefined;
    function onKey(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open || !understanding) return null;
  const technical = understanding.technical || {};
  const crop = technical.economicContext === "CROP_FAILURE";

  return (
    <div className="sb-drawer-layer" data-testid="understanding-panel">
      <button type="button" className="sb-drawer-backdrop" aria-label="Fechar prova" onClick={onClose} />
      <aside className="sb-drawer" role="dialog" aria-modal="true" aria-labelledby="understanding-title">
        <header className="sb-drawer-head">
          <h2 id="understanding-title">Como o Spider entendeu?</h2>
          <button type="button" className="sb-ghost" onClick={onClose}>
            Fechar
          </button>
        </header>
        <p className="sb-drawer-lead">
          Prova técnica. O Contextual Link fornece contexto de origem, mas não define a intenção.
        </p>
        <dl className="sb-grid">
          <article>
            <h3>Objetivo declarado</h3>
            <p data-testid="proof-objective">{understanding.human?.objective || "—"}</p>
          </article>
          <article>
            <h3>Página usada</h3>
            <p data-testid="proof-page-used">
              {technical.pageUsed ? technical.pageTitle || "sim" : "não — entrada direta ou página ausente"}
            </p>
          </article>
          <article data-testid="crop-failure-proof">
            <h3>CROP_FAILURE</h3>
            <dl>
              <dt>Valor</dt>
              <dd data-testid="economic-context">{crop ? "CROP_FAILURE" : "AUSENTE"}</dd>
              <dt>Fonte</dt>
              <dd data-testid="crop-failure-source">{formatSources(technical.economicContextSources)}</dd>
              <dt>Fonte adicional</dt>
              <dd data-testid="crop-failure-extra-source">
                {(technical.economicContextSources || []).includes("USER_OBJECTIVE")
                  ? "USER_OBJECTIVE"
                  : "NENHUMA"}
              </dd>
              <dt>Veio do link?</dt>
              <dd data-testid="crop-from-link">{technical.cropFailureFromLink ? "SIM" : "NÃO"}</dd>
            </dl>
          </article>
          <article>
            <h3>Contrato</h3>
            <dl>
              <dt>Intent</dt>
              <dd data-testid="proof-intent">{technical.intent || "—"}</dd>
              <dt>Domínio</dt>
              <dd>{technical.domain || "—"}</dd>
              <dt>Finalidade</dt>
              <dd data-testid="proof-purpose">{technical.purpose || "—"}</dd>
              <dt>Confidence</dt>
              <dd>{technical.confidence ?? "—"}</dd>
              <dt>Policy</dt>
              <dd data-testid="proof-policy">
                {technical.policyDecision || "—"} · {technical.policyReason || "—"}
              </dd>
              <dt>decisionId</dt>
              <dd data-testid="proof-decision">{technical.decisionId || "—"}</dd>
              <dt>planId</dt>
              <dd data-testid="proof-plan">{technical.planId || "—"}</dd>
              <dt>Provenance da intenção</dt>
              <dd>{technical.intentProvenance || "—"}</dd>
              <dt>Context provenance</dt>
              <dd data-testid="context-provenance">{technical.contextProvenance || "—"}</dd>
            </dl>
          </article>
        </dl>
        <p className="sb-drawer-lead" data-testid="demo-principle">
          {understanding.principle}
        </p>
      </aside>
    </div>
  );
}
