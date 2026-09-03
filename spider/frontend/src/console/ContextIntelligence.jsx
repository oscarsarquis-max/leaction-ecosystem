import { useState } from "react";
import ObjectiveJourney from "./ObjectiveJourney";
import {
  confidenceLabel,
  domainLabel,
  missingQuestion,
  operationLabel,
  purposeLabel,
  amountLabel,
} from "./projectObjectiveJourney";

function aiStateLabel(state) {
  if (state === "ACTIVE") return "ATIVA";
  if (state === "UNAVAILABLE") return "INDISPONÍVEL";
  return "DESABILITADA";
}

export default function ContextIntelligence({
  catalog,
  loading,
  error,
  preview,
  busy,
  message,
  executionEvidence,
  operationalEvents,
  onInterpret,
  onInterpretText,
  onExecute,
  onRevealDataPlane,
}) {
  const [objectiveText, setObjectiveText] = useState("");

  if (!loading && (!catalog?.contextEnabled || !catalog?.uiEnabled)) {
    return null;
  }

  const contract = preview?.intentContract;
  const plan = preview?.executionPlan;
  const capabilities = preview?.capabilities || [];
  const card = catalog?.items?.find((item) => item.intent === contract?.intent);
  const policyAccepted = preview?.decision === "ACCEPTED";
  const planResolved = Boolean(plan?.planId);
  const capabilitiesResolved = planResolved && capabilities.length === plan?.steps?.length;
  const executable = plan?.status === "READY" && preview?.route?.executable === true;
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
            label: "Plano determinado",
            value: [plan?.planType, plan?.status].filter(Boolean).join(" · "),
            accepted: planResolved,
          },
          {
            label: "Capabilities avaliadas",
            value: `${capabilities.length} capability(s)`,
            accepted: capabilitiesResolved,
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
            label: "Plano determinado",
            value: [plan?.planType, plan?.status].filter(Boolean).join(" · "),
            accepted: planResolved,
          },
          {
            label: "Capabilities avaliadas",
            value: `${capabilities.length} capability(s)`,
            accepted: capabilitiesResolved,
          },
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
          ? "Descreva uma necessidade empresarial. A IA produz somente a intenção; Guard, Plan Resolver e Capability Resolver permanecem determinísticos."
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

          <ObjectiveJourney
            preview={preview}
            catalog={catalog}
            executionEvidence={executionEvidence}
            operationalEvents={operationalEvents}
            onRevealDataPlane={onRevealDataPlane}
          />

          {contract ? (
            <>
              <section className="context-answer-block" aria-labelledby="context-want-title">
                <p className="context-question">O QUE EU QUERO?</p>
                <h5 id="context-want-title">Intent e contexto econômico</h5>
                <dl className="intent-preview-grid">
                  <div className="intent-preview-objective">
                    <dt>Objetivo</dt>
                    <dd>
                      {preview.requestedObjective || card?.description || contract?.objective}
                    </dd>
                  </div>
                  <div>
                    <dt>Intent</dt>
                    <dd className="mono">{contract?.intent}</dd>
                  </div>
                  <div>
                    <dt>Domínio</dt>
                    <dd>{domainLabel(catalog, contract?.domain)}</dd>
                  </div>
                  {(contract?.intent === "SEEK_WORKING_CAPITAL" || contract?.entities?.purpose) && (
                    <>
                      <div>
                        <dt>Finalidade</dt>
                        <dd>{purposeLabel(contract?.entities?.purpose)}</dd>
                      </div>
                      <div>
                        <dt>Valor</dt>
                        <dd>{amountLabel(contract?.entities?.amount)}</dd>
                      </div>
                      <div className="intent-preview-objective">
                        <dt>Situação empresarial</dt>
                        <dd className="mono">
                          {contract?.entities?.businessSituation || "Não informada"}
                        </dd>
                      </div>
                    </>
                  )}
                  <div>
                    <dt>Origem</dt>
                    <dd className="mono">{contract?.provenance?.source || "—"}</dd>
                  </div>
                  <div>
                    <dt>Confiança</dt>
                    <dd>{confidenceLabel(contract?.confidence)}</dd>
                  </div>
                  <div>
                    <dt>Política</dt>
                    <dd>{operationLabel(contract?.constraints, contract?.intent)}</dd>
                  </div>
                  <div>
                    <dt>Policy result</dt>
                    <dd className="mono">
                      {[preview.decision, preview.policyRef].filter(Boolean).join(" · ") || "—"}
                    </dd>
                  </div>
                </dl>
              </section>

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
                      (plan?.status === "PARTIALLY_AVAILABLE"
                        ? "Plano parcial: capabilities indisponíveis não serão simuladas nem executadas."
                        : plan?.status === "NOT_EXECUTABLE"
                          ? "Plano não executável neste boundary. Nenhuma capability inexistente será simulada."
                          : "A compreensão está disponível, mas não há rota executável para este plano.")}
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
