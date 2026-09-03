function confidenceLabel(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${Math.round(parsed * 100)}%` : "—";
}

function domainLabel(catalog, domain) {
  return catalog?.items?.find((item) => item.domain === domain)?.domainLabel || domain;
}

function operationLabel(constraints) {
  if (constraints?.readOnly === true && constraints?.mutationAllowed === false) {
    return "SOMENTE CONSULTA";
  }
  if (constraints?.mutationAllowed === true) {
    return "MUTAÇÃO PERMITIDA";
  }
  return "OPERAÇÃO RESTRITA";
}

function flowState(complete, available = true) {
  if (!available) return "unavailable";
  return complete ? "complete" : "pending";
}

export default function ContextIntelligence({
  catalog,
  loading,
  error,
  preview,
  busy,
  message,
  onInterpret,
  onExecute,
}) {
  if (!loading && (!catalog?.contextEnabled || !catalog?.uiEnabled)) {
    return null;
  }

  const contract = preview?.intentContract;
  const card = catalog?.items?.find((item) => item.intent === contract?.intent);
  const policyAccepted = preview?.decision === "ACCEPTED";
  const routeResolved = Boolean(preview?.route?.routeRef);
  const executable = preview?.route?.executable === true;
  const validationItems = preview
    ? [
        {
          label: "Intent válido",
          value: contract?.intent,
          accepted: Boolean(contract?.intent && policyAccepted),
        },
        {
          label: "Política aceita",
          value: [preview.decision, preview.policyRef].filter(Boolean).join(" · "),
          accepted: policyAccepted,
        },
        {
          label: "Rota determinada",
          value: preview.route?.routeRef,
          accepted: routeResolved,
        },
      ]
    : [];
  const understandingFlow = preview
    ? [
        { label: "Objetivo", state: flowState(Boolean(contract?.objective)) },
        { label: "Intent", state: flowState(Boolean(contract?.intent)) },
        { label: "Policy", state: flowState(policyAccepted) },
        { label: "Rota", state: flowState(routeResolved) },
        { label: "Executar", state: flowState(Boolean(message?.ok), executable) },
        { label: "Jornada", state: flowState(Boolean(message?.ok), executable) },
      ]
    : [];

  return (
    <section className="context-intelligence" aria-labelledby="context-title" data-testid="context-intelligence">
      <header className="context-heading">
        <div>
          <p className="eyebrow">CONTEXT INTELLIGENCE · DEMONSTRAÇÃO</p>
          <h3 id="context-title">O que você precisa resolver?</h3>
          <p className="muted">
            Selecione uma situação de negócio. O Spider formaliza o objetivo antes de determinar a
            rota.
          </p>
        </div>
        <span className="context-ai-off">IA — próxima etapa</span>
      </header>

      <label className="context-natural-language">
        <span>Interpretação em linguagem natural</span>
        <input
          type="text"
          disabled
          placeholder="Descreva uma situação ou objetivo..."
          aria-describedby="context-ai-note"
        />
      </label>
      <p id="context-ai-note" className="context-note muted">
        Escolha uma situação abaixo ou descreva seu objetivo. O Spider transforma o objetivo em uma
        intenção estruturada antes de determinar como executá-lo. A descrição em linguagem natural
        estará disponível em uma próxima etapa.
      </p>

      <div className="context-section-heading">
        <h4>Situações frequentes</h4>
        <span className="muted">Boundary MOCK_ONLY / SIMULATED_INFRASTRUCTURE</span>
      </div>

      {loading && <p className="muted">Carregando catálogo contextual…</p>}
      {error && <p className="error">{error.message}</p>}
      {catalog?.items?.length > 0 && (
        <div className="business-intent-grid" data-testid="business-intent-cards">
          {catalog.items.map((item) => (
            <article className="business-intent-card" key={item.intent}>
              <p className="business-intent-domain">{item.domainLabel}</p>
              <h5>{item.title}</h5>
              <p>{item.description}</p>
              <button
                type="button"
                className="ghost"
                disabled={busy}
                onClick={() => onInterpret(item)}
              >
                Investigar
              </button>
            </article>
          ))}
        </div>
      )}

      {preview && (
        <article className="intent-preview" data-testid="intent-preview" aria-labelledby="intent-preview-title">
          <header className="intent-preview-head">
            <div>
              <p className="eyebrow">INTENT CONTRACT · V1</p>
              <h4 id="intent-preview-title">SPIDER ENTENDEU</h4>
            </div>
            <span className={`intent-decision intent-decision-${preview.decision?.toLowerCase()}`}>
              {preview.decision}
            </span>
          </header>

          <ol className="context-understanding-flow" aria-label="Objetivo, Intent, Policy, Rota, Executar e Jornada">
            {understandingFlow.map((item, index) => (
              <li key={item.label} data-state={item.state}>
                <span className="context-flow-index" aria-hidden="true">
                  {item.state === "complete" ? "✓" : index + 1}
                </span>
                <strong>{item.label}</strong>
                {index < understandingFlow.length - 1 && (
                  <span className="context-flow-arrow" aria-hidden="true">
                    →
                  </span>
                )}
              </li>
            ))}
          </ol>

          <dl className="intent-preview-grid">
            <div className="intent-preview-objective">
              <dt>Objetivo</dt>
              <dd>{card?.description || contract?.objective}</dd>
            </div>
            <div>
              <dt>Intent</dt>
              <dd className="mono">{contract?.intent}</dd>
            </div>
            <div>
              <dt>Domínio</dt>
              <dd>{domainLabel(catalog, contract?.domain)}</dd>
            </div>
            <div>
              <dt>Origem</dt>
              <dd className="mono">{contract?.provenance?.source || "—"}</dd>
            </div>
            <div>
              <dt>Confiança</dt>
              <dd>{confidenceLabel(contract?.confidence)}</dd>
            </div>
            <div>
              <dt>Operação</dt>
              <dd>{operationLabel(contract?.constraints)}</dd>
            </div>
            <div>
              <dt>Policy result</dt>
              <dd className="mono">
                {[preview.decision, preview.policyRef].filter(Boolean).join(" · ") || "—"}
              </dd>
            </div>
            <div>
              <dt>Capability</dt>
              <dd className="mono">{preview.route?.capabilityRef || "—"}</dd>
            </div>
            <div data-testid="context-route-resolution">
              <dt>Rota determinada</dt>
              <dd className="mono">{preview.route?.routeRef || "Não resolvida"}</dd>
            </div>
            <div>
              <dt>Estado da capacidade</dt>
              <dd>
                {executable
                  ? "Disponível ponta a ponta"
                  : "Preview disponível · execução ainda não habilitada"}
              </dd>
            </div>
          </dl>

          <section className="intent-validation" aria-labelledby="intent-validation-title">
            <h5 id="intent-validation-title">Validação</h5>
            <ul>
              {validationItems.map((item) => (
                <li key={item.label} data-state={item.accepted ? "accepted" : "rejected"}>
                  <span aria-hidden="true">{item.accepted ? "✓" : "✕"}</span>
                  <div>
                    <strong>{item.label}</strong>
                    <small>{item.value || "Sem evidência"}</small>
                  </div>
                </li>
              ))}
            </ul>
          </section>

          <footer className="intent-preview-actions">
            {!executable && (
              <p className="muted">
                A compreensão está disponível. A execução ponta a ponta de CTX-001 está habilitada
                inicialmente para Crédito.
              </p>
            )}
            {policyAccepted && executable && (
              <button type="button" className="cta" disabled={busy} onClick={() => onExecute(preview)}>
                {busy ? "Executando…" : "Executar"}
              </button>
            )}
          </footer>
        </article>
      )}

      {message && (
        <p className={message.ok ? "ok" : "error"} role="status">
          {message.text}
        </p>
      )}
    </section>
  );
}
