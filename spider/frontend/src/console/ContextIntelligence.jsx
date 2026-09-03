import { useState } from "react";

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

function aiStateLabel(state) {
  if (state === "ACTIVE") return "ATIVA";
  if (state === "UNAVAILABLE") return "INDISPONÍVEL";
  return "DESABILITADA";
}

function missingQuestion(key) {
  const questions = {
    proposalId: "Qual é o número da proposta?",
    collectionId: "Qual é o identificador da cobrança?",
    invoiceId: "Qual é o identificador do faturamento?",
    customerId: "Qual é o identificador do cliente?",
    serviceRequestId: "Qual é o número da solicitação?",
    incidentId: "Qual é o identificador do incidente?",
  };
  return questions[key] || `Informe o dado obrigatório: ${key}.`;
}

export default function ContextIntelligence({
  catalog,
  loading,
  error,
  preview,
  busy,
  message,
  onInterpret,
  onInterpretText,
  onExecute,
}) {
  const [objectiveText, setObjectiveText] = useState("");

  if (!loading && (!catalog?.contextEnabled || !catalog?.uiEnabled)) {
    return null;
  }

  const contract = preview?.intentContract;
  const card = catalog?.items?.find((item) => item.intent === contract?.intent);
  const policyAccepted = preview?.decision === "ACCEPTED";
  const routeResolved = Boolean(preview?.route?.routeRef);
  const executable = preview?.route?.executable === true;
  const interpretation = preview?.interpretation;
  const isNaturalLanguage = Boolean(interpretation || preview?.requestedObjective);
  const missingContext = interpretation?.missingContext || [];
  const candidateIntents = interpretation?.candidateIntents || [];
  const intentRecognized = Boolean(contract?.intent);
  const contextSufficient = intentRecognized && missingContext.length === 0;
  const aiState = catalog?.aiState || (catalog?.aiEnabled ? "UNAVAILABLE" : "DISABLED");
  const aiAvailable = catalog?.aiEnabled && aiState === "ACTIVE";
  const validationItems = preview
    ? isNaturalLanguage
      ? [
          {
            label: "Intent reconhecido",
            value: contract?.intent,
            accepted: intentRecognized,
          },
          {
            label: "Contexto suficiente",
            value: contextSufficient
              ? "Nenhuma informação obrigatória ausente"
              : missingContext.join(", "),
            accepted: contextSufficient,
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
      : [
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
        {
          label: "Objetivo",
          state: flowState(Boolean(contract?.objective || preview?.requestedObjective)),
        },
        ...(isNaturalLanguage
          ? [{ label: "IA", state: flowState(Boolean(interpretation)) }]
          : []),
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
            Descreva uma necessidade empresarial ou selecione uma situação frequente. As duas
            entradas convergem para o mesmo Intent Contract.
          </p>
        </div>
        <span
          className={`context-ai-state context-ai-${aiState.toLowerCase()}`}
          data-testid="context-ai-state"
        >
          IA CONTEXTUAL — {aiStateLabel(aiState)}
        </span>
      </header>

      <form
        className="context-natural-language"
        onSubmit={(event) => {
          event.preventDefault();
          if (aiAvailable && objectiveText.trim()) {
            onInterpretText(objectiveText.trim());
          }
        }}
      >
        <label htmlFor="context-objective">Interpretação em linguagem natural</label>
        <textarea
          id="context-objective"
          value={objectiveText}
          disabled={!aiAvailable || busy}
          placeholder="Descreva uma situação ou objetivo..."
          aria-describedby="context-ai-note"
          rows={3}
          onChange={(event) => setObjectiveText(event.target.value)}
        />
        <button
          type="submit"
          className="cta"
          disabled={!aiAvailable || busy || !objectiveText.trim()}
        >
          {busy ? "Interpretando…" : "Interpretar"}
        </button>
      </form>
      <p id="context-ai-note" className="context-note muted">
        {aiAvailable
          ? "Descreva uma necessidade empresarial. A IA produz uma intenção estruturada; o Guard e o Router continuam responsáveis pela decisão."
          : "A interpretação em linguagem natural está indisponível neste ambiente. As situações frequentes continuam operacionais pelo caminho determinístico."}
      </p>

      <div className="context-or" aria-hidden="true">
        <span>OU</span>
      </div>

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
              <p className="eyebrow">
                {contract ? "INTENT CONTRACT · V1" : "INTERPRETAÇÃO CONTEXTUAL"}
              </p>
              <h4 id="intent-preview-title">SPIDER ENTENDEU</h4>
            </div>
            <span className={`intent-decision intent-decision-${preview.decision?.toLowerCase()}`}>
              {preview.decision}
            </span>
          </header>

          {preview.requestedObjective && (
            <section className="intent-requested-objective" aria-label="Objetivo informado">
              <span>Você pediu</span>
              <blockquote>{preview.requestedObjective}</blockquote>
            </section>
          )}

          <ol
            className="context-understanding-flow"
            aria-label={
              isNaturalLanguage
                ? "Objetivo, IA, Intent, Policy, Rota, Executar e Jornada"
                : "Objetivo, Intent, Policy, Rota, Executar e Jornada"
            }
            style={{ "--context-flow-count": understandingFlow.length }}
          >
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

          {contract ? (
            <>
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
                  : missingContext.length > 0
                    ? "Bloqueada · contexto obrigatório ausente"
                    : isNaturalLanguage
                      ? "Sem autorização de execução"
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

              {missingContext.length > 0 && (
                <section className="intent-clarification" data-testid="missing-context">
                  <h5>Falta uma informação</h5>
                  {missingContext.map((key) => (
                    <p key={key}>{missingQuestion(key)}</p>
                  ))}
                </section>
              )}

              <footer className="intent-preview-actions">
                {!executable && (
                  <p className="muted">
                    {preview.interpretationMessage ||
                      "A compreensão está disponível. A execução ponta a ponta de CTX-001 está habilitada inicialmente para Crédito."}
                  </p>
                )}
                {policyAccepted && executable && (
                  <button
                    type="button"
                    className="cta"
                    disabled={busy}
                    onClick={() => onExecute(preview)}
                  >
                    {busy ? "Executando…" : "Executar"}
                  </button>
                )}
              </footer>
            </>
          ) : (
            <section className="intent-interpretation-blocked" data-testid="interpretation-blocked">
              <h5>
                {preview.interpretationStatus === "AMBIGUOUS"
                  ? "Preciso entender melhor o objetivo"
                  : "Objetivo não suportado"}
              </h5>
              <p>{preview.interpretationMessage}</p>
              {candidateIntents.length > 0 && (
                <ul>
                  {candidateIntents.map((intent) => {
                    const option = catalog?.items?.find((item) => item.intent === intent);
                    return <li key={intent}>{option?.title || intent}</li>;
                  })}
                </ul>
              )}
              <p className="muted">Nenhuma rota foi determinada e nenhuma execução foi iniciada.</p>
            </section>
          )}
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
