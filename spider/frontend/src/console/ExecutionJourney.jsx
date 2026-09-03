import { projectExecutionJourney, JOURNEY_MARKERS } from "./projectExecutionJourney";

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

export default function ExecutionJourney({
  summary,
  timeline,
  steps,
  waitInfo,
  callback,
  operationalEvents,
  heading = "Jornada da execução",
}) {
  const projection = projectExecutionJourney({
    summary,
    timeline,
    steps,
    waitInfo,
    callback,
    operationalEvents,
  });

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
        Projeção do Data Plane — somente etapas com evidência. Sem timers e sem simulação de
        progresso.
      </p>
      <ol className="journey-live" aria-label="Jornada visual da execução">
        {projection.stages.map((item) => (
          <li
            key={item.id}
            className={`journey-live-step journey-vis-${item.state.toLowerCase()}`}
            data-testid={`journey-stage-${item.id}`}
            data-state={item.state}
            data-layer={item.layer}
          >
            <span className="journey-live-marker" aria-hidden="true">
              {item.marker || JOURNEY_MARKERS[item.state]}
            </span>
            <div>
              <strong>{item.title}</strong>
              <div className="muted">
                {item.layer} · <span className="journey-vis-label">{stateLabel(item.state)}</span>
              </div>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
