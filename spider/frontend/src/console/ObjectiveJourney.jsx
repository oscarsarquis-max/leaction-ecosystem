import { useEffect, useMemo, useState } from "react";
import {
  projectObjectiveCapabilityDetail,
  projectObjectiveJourney,
  projectObjectivePhaseDetail,
} from "./projectObjectiveJourney";

function visualClass(status) {
  const value = String(status || "").toLowerCase();
  if (value === "succeeded" || value === "accepted" || value === "ready") return "succeeded";
  if (value === "partial" || value === "partially_available") return "waiting";
  if (
    value === "failed" ||
    value === "rejected" ||
    value === "policy_rejected" ||
    value === "not_authorized" ||
    value === "not_executable"
  ) {
    return "failed";
  }
  if (value === "missing_context" || value === "needs_information" || value === "ambiguous") {
    return "waiting";
  }
  if (value === "not_started") return "not_reached";
  return "active";
}

function displayValue(item) {
  if (item.unit === "ms") return `${Number(item.value).toLocaleString("pt-BR")} ms`;
  return String(item.value);
}

export default function ObjectiveJourney({
  preview,
  catalog,
  executionEvidence,
  operationalEvents,
  onRevealDataPlane,
}) {
  const projection = useMemo(
    () => projectObjectiveJourney({ preview, catalog, executionEvidence, operationalEvents }),
    [preview, catalog, executionEvidence, operationalEvents],
  );
  const [selectedId, setSelectedId] = useState("objective");

  useEffect(() => {
    setSelectedId(projection?.interrupt || "objective");
  }, [preview?.decisionId, projection?.interrupt]);

  if (!projection) return null;

  const selectedPhase =
    projection.phases.find((item) => item.id === selectedId) ||
    projection.phases.find((item) => item.id === selectedId.split(":")[0]);
  const selectedCapability =
    selectedId.startsWith("capability:")
      ? projection.capabilities.find((item) => item.stepId === selectedId.slice("capability:".length))
      : null;
  const phaseDetail = selectedCapability
    ? null
    : projectObjectivePhaseDetail(selectedPhase?.id, projection, catalog);
  const capabilityDetail = selectedCapability
    ? projectObjectiveCapabilityDetail(selectedCapability, projection, executionEvidence)
    : null;

  return (
    <section
      className="objective-journey"
      data-testid="objective-journey"
      aria-labelledby="objective-journey-title"
    >
      <header className="objective-journey-head">
        <p className="eyebrow">PLAN JOURNEY</p>
        <h5 id="objective-journey-title">Jornada do objetivo</h5>
        <p className="muted">
          O usuário declara objetivos. A IA os compreende. O Spider determina o plano, decompõe em
          capacidades e o ambiente decide onde executá-las. Cada fase projeta evidência real.
        </p>
        <p className="objective-journey-split muted">
          PLAN JOURNEY explica o que precisa ser feito. DATA PLANE JOURNEY explica como foi
          executado.
        </p>
      </header>

      <div className="journey-explainer">
        <ol className="journey-live" aria-label="Fases da jornada do objetivo">
          {projection.phases.map((phase) => {
            const selected = selectedId === phase.id || selectedId.startsWith(`${phase.id}:`);
            return (
              <li
                key={phase.id}
                className={`journey-live-step journey-vis-${visualClass(phase.status)} ${
                  selected && !selectedCapability ? "journey-step-selected" : ""
                }`}
                data-testid={`objective-phase-${phase.id}`}
                data-state={phase.status}
              >
                <button
                  type="button"
                  className="journey-step-button"
                  aria-pressed={selectedId === phase.id}
                  aria-controls="objective-journey-detail"
                  onClick={() => setSelectedId(phase.id)}
                >
                  <span className="journey-live-marker" aria-hidden="true">
                    {phase.marker}
                  </span>
                  <span className="journey-step-copy">
                    <strong>{phase.title}</strong>
                    <span className="muted">
                      <span className="journey-vis-label">{phase.status}</span>
                    </span>
                    <span className="journey-step-summary" data-testid={phase.id === "plan" ? "context-execution-plan" : undefined}>
                      {phase.summary}
                    </span>
                  </span>
                  <span className="journey-step-disclosure" aria-hidden="true">
                    ›
                  </span>
                </button>

                {phase.id === "capabilities" && projection.capabilities.length > 0 && (
                  <ol className="capability-plan-list" data-testid="context-capabilities">
                    {projection.capabilities.map((capability) => {
                      const capabilitySelected = selectedId === `capability:${capability.stepId}`;
                      return (
                        <li
                          key={capability.stepId}
                          data-status={capability.status}
                          data-visual={capability.visual.kind}
                        >
                          <button
                            type="button"
                            aria-pressed={capabilitySelected}
                            aria-controls="objective-journey-detail"
                            onClick={() => setSelectedId(`capability:${capability.stepId}`)}
                          >
                            <span aria-hidden="true">{capability.visual.marker}</span>
                            <span>
                              <strong>{capability.friendlyName}</strong>
                              <small>
                                {capability.capabilityId} · {capability.visual.label} ·{" "}
                                {capability.required ? "obrigatória" : "opcional"}
                              </small>
                            </span>
                          </button>
                        </li>
                      );
                    })}
                  </ol>
                )}
              </li>
            );
          })}
        </ol>

        <aside
          id="objective-journey-detail"
          className={`journey-step-detail journey-vis-${visualClass(
            selectedCapability?.visual?.kind === "executed"
              ? "SUCCEEDED"
              : selectedPhase?.status,
          )}`}
          data-testid={selectedCapability ? "context-capability-detail" : "objective-journey-detail"}
          aria-live="polite"
        >
          {capabilityDetail ? (
            <>
              <header className="journey-detail-head">
                <span className="journey-detail-marker" aria-hidden="true">
                  {capabilityDetail.visual.marker}
                </span>
                <div>
                  <h4>{capabilityDetail.friendlyName}</h4>
                  <p className="muted">
                    {capabilityDetail.capabilityId} · {capabilityDetail.visual.label}
                  </p>
                </div>
              </header>
              <p className="journey-detail-summary">{capabilityDetail.whatHappened}</p>
              <section>
                <h5>O que aconteceu?</h5>
                <p>{capabilityDetail.whatHappened}</p>
              </section>
              <section>
                <h5>Qual foi o resultado?</h5>
                <p>{capabilityDetail.decision}</p>
              </section>
              <section>
                <h5>Quais dados participaram?</h5>
                <dl className="journey-detail-list">
                  {[
                    { label: "Capability", value: capabilityDetail.capabilityId },
                    { label: "Descrição", value: capabilityDetail.description },
                    { label: "Por que é necessária", value: capabilityDetail.reason },
                    { label: "Obrigatoriedade", value: capabilityDetail.required ? "obrigatória" : "opcional" },
                    { label: "Input esperado", value: capabilityDetail.inputContract },
                    { label: "Output esperado", value: capabilityDetail.outputContract },
                    { label: "Disponibilidade", value: capabilityDetail.availability },
                    { label: "Resolução", value: capabilityDetail.resolutionStatus },
                    { label: "Execução", value: capabilityDetail.executionStatus },
                    { label: "Route", value: capabilityDetail.routeRef },
                    { label: "Adapter", value: capabilityDetail.adapterRef },
                    { label: "Target", value: capabilityDetail.target },
                  ]
                    .filter((item) => item.value)
                    .map((item) => (
                      <div key={item.label}>
                        <dt>{item.label}</dt>
                        <dd>{item.value}</dd>
                      </div>
                    ))}
                </dl>
              </section>
              <section>
                <h5>Qual foi a decisão?</h5>
                <p>{capabilityDetail.decision}</p>
              </section>
              <section>
                <h5>Qual o próximo passo?</h5>
                <p>{capabilityDetail.nextSteps}</p>
              </section>
              {capabilityDetail.executionId && onRevealDataPlane && (
                <p>
                  <button type="button" className="ghost" onClick={onRevealDataPlane}>
                    Ver Data Plane Journey
                  </button>
                </p>
              )}
              <details className="journey-related-events">
                <summary>Eventos relacionados ({capabilityDetail.relatedEvents.length})</summary>
                {capabilityDetail.relatedEvents.length > 0 ? (
                  <ul>
                    {capabilityDetail.relatedEvents.map((event) => (
                      <li key={event.id}>
                        <strong>{event.eventType}</strong>
                        <span>
                          {[event.source, event.outcome, event.occurredAt].filter(Boolean).join(" · ")}
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">Nenhum evento correlacionável exposto para esta capability.</p>
                )}
              </details>
            </>
          ) : (
            phaseDetail && (
              <>
                <header className="journey-detail-head">
                  <span className="journey-detail-marker" aria-hidden="true">
                    {selectedPhase.marker}
                  </span>
                  <div>
                    <h4>{phaseDetail.title}</h4>
                    <p className="muted">
                      <span className="journey-vis-label">{phaseDetail.status}</span>
                    </p>
                  </div>
                </header>
                <p className="journey-detail-summary">{phaseDetail.summary}</p>
                <section>
                  <h5>O que aconteceu?</h5>
                  <p>{phaseDetail.whatHappened}</p>
                </section>
                <section>
                  <h5>Qual foi o resultado?</h5>
                  <p>{phaseDetail.result}</p>
                </section>
                <section>
                  <h5>Quais dados participaram?</h5>
                  <dl className="journey-detail-list">
                    {phaseDetail.data.map((item) => (
                      <div key={`${item.label}-${item.value}`}>
                        <dt>{item.label}</dt>
                        <dd>{displayValue(item)}</dd>
                      </div>
                    ))}
                  </dl>
                  {selectedPhase.id === "plan" && (
                    <p className="muted">
                      {planCopy(projection)}
                    </p>
                  )}
                  {selectedPhase.id === "resolution" && (
                    <div className="objective-executor-table" data-testid="objective-resolution-table">
                      <h6>Onde o Spider vai executar</h6>
                      <table>
                        <thead>
                          <tr>
                            <th>Capability</th>
                            <th>Executor</th>
                          </tr>
                        </thead>
                        <tbody>
                          {projection.capabilities.map((capability) => (
                            <tr key={capability.stepId}>
                              <td>{capability.capabilityId}</td>
                              <td>{capability.resolution.executor}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  {selectedPhase.id === "result" && (
                    <div className="objective-result-summary" data-testid="objective-result">
                      <p>O Spider conseguiu:</p>
                      <ul>
                        {projection.result.achieved.map((item) => (
                          <li key={item} data-state="achieved">
                            ✓ {item}
                          </li>
                        ))}
                      </ul>
                      {projection.result.pending.length > 0 && (
                        <>
                          <p>Ainda não disponível:</p>
                          <ul>
                            {projection.result.pending.map((item) => (
                              <li key={item} data-state="pending">
                                ○ {item}
                              </li>
                            ))}
                          </ul>
                        </>
                      )}
                      <p>
                        <strong>Conclusão:</strong> {projection.result.conclusion}
                      </p>
                    </div>
                  )}
                </section>
                <section>
                  <h5>Qual foi a decisão?</h5>
                  <p>{phaseDetail.decision}</p>
                </section>
                <section>
                  <h5>Qual o próximo passo?</h5>
                  <p>{phaseDetail.nextSteps}</p>
                </section>
                {selectedPhase.id === "execution" && projection.executionId && onRevealDataPlane && (
                  <p>
                    <button type="button" className="ghost" onClick={onRevealDataPlane}>
                      Ver Data Plane Journey
                    </button>
                  </p>
                )}
                <details className="journey-related-events">
                  <summary>Eventos relacionados ({phaseDetail.relatedEvents.length})</summary>
                  {phaseDetail.relatedEvents.length > 0 ? (
                    <ul>
                      {phaseDetail.relatedEvents.map((event) => (
                        <li key={event.id}>
                          <strong>{event.eventType}</strong>
                          <span>
                            {[event.source, event.outcome, event.occurredAt]
                              .filter(Boolean)
                              .join(" · ")}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="muted">Nenhum evento correlacionável exposto para esta fase.</p>
                  )}
                </details>
                {phaseDetail.usedAi === false &&
                  ["plan", "capabilities", "resolution", "execution", "result"].includes(
                    selectedPhase.id,
                  ) && (
                    <p className="muted" data-testid="objective-no-ai">
                      Esta fase é determinística. A IA não participa de Plan Resolver, Capability
                      Resolver, Route Resolver, Adapter Resolver nem Data Plane.
                    </p>
                  )}
              </>
            )
          )}
        </aside>
      </div>
    </section>
  );
}

function planCopy(projection) {
  const plan = projection.plan;
  if (!plan) return "Plano não determinado.";
  return `${plan.planType} · ${plan.planId} · versão ${plan.schemaVersion || "—"}`;
}
