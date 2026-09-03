import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { projectExecutionJourney, JOURNEY_MARKERS } from "./projectExecutionJourney";
import {
  chooseAutomaticJourneyStage,
  projectJourneyStepDetail,
} from "./projectJourneyStepDetail";

function stateLabel(state) {
  switch (state) {
    case "SUCCEEDED":
      return "SUCCEEDED";
    case "FAILED":
      return "FAILED";
    case "REJECTED":
      return "REJECTED";
    case "WAITING":
      return "WAITING";
    case "RETRYING":
      return "RETRYING";
    case "DELAYED":
      return "DELAYED";
    case "ACTIVE":
      return "ACTIVE";
    default:
      return "NOT REACHED";
  }
}

function displayValue(detail) {
  if (detail.unit === "ms") {
    return `${Number(detail.value).toLocaleString("pt-BR")} ms`;
  }
  return String(detail.value);
}

export default function ExecutionJourney({
  summary,
  timeline,
  steps,
  waitInfo,
  callback,
  operationalEvents,
  contextJourney,
  heading = "Jornada da execução",
}) {
  const projection = projectExecutionJourney({
    summary,
    timeline,
    steps,
    waitInfo,
    callback,
    operationalEvents,
    contextJourney,
  });
  const detailInput = useMemo(
    () => ({ summary, timeline, steps, waitInfo, callback, operationalEvents, contextJourney }),
    [summary, timeline, steps, waitInfo, callback, operationalEvents, contextJourney],
  );
  const stageDetails = useMemo(
    () =>
      Object.fromEntries(
        projection.stages.map((stage) => [
          stage.id,
          projectJourneyStepDetail(stage, detailInput, projection.stages),
        ]),
      ),
    [detailInput, projection.executionId, projection.state, projection.stages],
  );
  const [selectedStageId, setSelectedStageId] = useState(null);
  const manualSelection = useRef(false);

  useEffect(() => {
    manualSelection.current = false;
    setSelectedStageId(chooseAutomaticJourneyStage(projection.stages, projection.state));
  }, [projection.executionId]);

  useEffect(() => {
    const selectionStillExists = projection.stages.some((item) => item.id === selectedStageId);
    if (!manualSelection.current || !selectionStillExists) {
      setSelectedStageId(chooseAutomaticJourneyStage(projection.stages, projection.state));
    }
  }, [projection.stages, projection.state, selectedStageId]);

  const selectedStage =
    projection.stages.find((item) => item.id === selectedStageId) || projection.stages[0];
  const selectedDetail = selectedStage ? stageDetails[selectedStage.id] : null;

  function selectStage(id) {
    manualSelection.current = true;
    setSelectedStageId(id);
  }

  if (!projection.executionId) {
    return (
      <section className="execution-journey" aria-labelledby="journey-title">
        <h3 id="journey-title">{heading}</h3>
        <p className="muted">Selecione ou inicie uma execução para projetar o caminho real.</p>
      </section>
    );
  }

  return (
    <section className="execution-journey" aria-labelledby="journey-title" data-testid="execution-journey">
      <h3 id="journey-title">{heading}</h3>
      <p className="muted">
        Projeção do Context Plane e do Data Plane — somente etapas com evidência. Sem timers e sem
        simulação de progresso.
      </p>
      <div className="journey-explainer">
        <ol className="journey-live" aria-label="Etapas da jornada">
          {projection.stages.map((item, index) => {
            const detail = stageDetails[item.id];
            const selected = item.id === selectedStage?.id;
            const zone = item.zone || "DATA";
            const previousZone =
              index > 0 ? projection.stages[index - 1].zone || "DATA" : null;
            return (
              <Fragment key={item.id}>
                {zone !== previousZone && (
                  <li
                    className={`journey-zone-label journey-zone-${zone.toLowerCase()}`}
                    data-testid={`journey-zone-${zone.toLowerCase()}`}
                  >
                    <span>
                      {zone === "CONTEXT" ? "CONTEXTO" : zone === "PLAN" ? "PLANO" : "DATA PLANE"}
                    </span>
                    <small>
                      {zone === "CONTEXT"
                        ? "O que o usuário pretende e qual plano foi determinado."
                        : zone === "PLAN"
                          ? "Quais capabilities foram resolvidas e quais routes estão disponíveis."
                        : "Como o Spider efetivamente executou a operação."}
                    </small>
                  </li>
                )}
                <li
                  className={`journey-live-step journey-vis-${item.state.toLowerCase()} ${
                    selected ? "journey-step-selected" : ""
                  }`}
                  data-testid={`journey-stage-${item.id}`}
                  data-state={item.state}
                  data-layer={item.layer}
                  data-zone={zone}
                >
                  <button
                    type="button"
                    className="journey-step-button"
                    aria-pressed={selected}
                    aria-controls="journey-step-detail"
                    onClick={() => selectStage(item.id)}
                  >
                    <span className="journey-live-marker" aria-hidden="true">
                      {item.marker || JOURNEY_MARKERS[item.state]}
                    </span>
                    <span className="journey-step-copy">
                      <strong>{item.title}</strong>
                      <span className="muted">
                        {item.layer} ·{" "}
                        <span className="journey-vis-label">{stateLabel(item.state)}</span>
                      </span>
                      <span className="journey-step-summary">{detail?.summary}</span>
                    </span>
                    <span className="journey-step-disclosure" aria-hidden="true">
                      ›
                    </span>
                  </button>
                </li>
              </Fragment>
            );
          })}
        </ol>
        {selectedStage && selectedDetail && (
          <aside
            id="journey-step-detail"
            className={`journey-step-detail journey-vis-${selectedStage.state.toLowerCase()}`}
            data-testid="journey-step-detail"
            aria-live="polite"
          >
            <header className="journey-detail-head">
              <span className="journey-detail-marker" aria-hidden="true">
                {selectedStage.marker || JOURNEY_MARKERS[selectedStage.state]}
              </span>
              <div>
                <h4>{selectedStage.title}</h4>
                <p className="muted">
                  {selectedStage.layer} ·{" "}
                  <span className="journey-vis-label">{stateLabel(selectedStage.state)}</span>
                </p>
              </div>
            </header>
            <p className="journey-detail-summary">{selectedDetail.summary}</p>

            <section>
              <h5>O que aconteceu</h5>
              <p>{selectedDetail.whatHappened}</p>
            </section>

            {selectedDetail.technicalDetails.length > 0 && (
              <section>
                <h5>Detalhes técnicos</h5>
                <dl className="journey-detail-list">
                  {selectedDetail.technicalDetails.map((detail) => (
                    <div key={detail.label}>
                      <dt>{detail.label}</dt>
                      <dd>{displayValue(detail)}</dd>
                    </div>
                  ))}
                </dl>
                <p className="journey-redaction-note">
                  Apenas dados seguros do read model; credenciais e payloads protegidos não são
                  exibidos.
                </p>
              </section>
            )}

            {selectedDetail.nextSteps && (
              <section>
                <h5>Próximos passos</h5>
                <p>{selectedDetail.nextSteps}</p>
              </section>
            )}

            <details className="journey-related-events">
              <summary>Eventos relacionados ({selectedDetail.relatedEvents.length})</summary>
              {selectedDetail.relatedEvents.length > 0 ? (
                <ul>
                  {selectedDetail.relatedEvents.map((event) => (
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
                <p className="muted">Nenhum evento correlacionável exposto para esta etapa.</p>
              )}
            </details>
          </aside>
        )}
      </div>
    </section>
  );
}
