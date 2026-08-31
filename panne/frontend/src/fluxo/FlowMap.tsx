import type { MapStepView } from "./criticalPath";

function situationTone(label: string): "sucesso" | "atencao" | "erro" | "info" | "neutro" {
  switch (label) {
    case "Você está aqui":
      return "info";
    case "Requer atenção":
      return "atencao";
    case "Sem acesso":
      return "erro";
    case "Não se aplica":
      return "neutro";
    case "Pronto":
      return "sucesso";
    case "Não iniciado":
      return "neutro";
    default:
      return "neutro";
  }
}

function statusIcon(label: string): string {
  switch (label) {
    case "Você está aqui":
      return "●";
    case "Pronto":
      return "✓";
    case "Requer atenção":
      return "!";
    case "Não se aplica":
      return "–";
    case "Sem acesso":
      return "✕";
    default:
      return "○";
  }
}

export function FlowMap({
  steps,
  focusId,
  onSelect,
}: {
  steps: MapStepView[];
  focusId: MapStepView["def"]["id"];
  onSelect: (id: MapStepView["def"]["id"]) => void;
}) {
  const focusStep = steps.find((row) => row.def.id === focusId) ?? steps[0];
  const total = steps.length;

  return (
    <nav className="flow-map" aria-label="Etapas do fluxo produtivo">
      <p className="flow-map__caption" id="flow-map-caption">
        Mapa do caminho crítico
        {focusStep ? (
          <>
            {" · "}
            <span>
              Etapa {focusStep.def.id} de {total}
            </span>
          </>
        ) : null}
      </p>
      <ol className="flow-map__track" aria-describedby="flow-map-caption">
        {steps.map((row, index) => {
          const tone = situationTone(row.mapLabel);
          const classes = [
            "flow-map__node",
            `tone-${tone}`,
            row.isCriticalPosition ? "is-here" : "",
            row.isFocus ? "is-focus" : "",
            row.profileEmphasis ? "is-emphasis" : "",
            !row.hasAccess ? "is-disabled" : "",
            !row.applicable || row.situation === "Não se aplica" ? "is-na" : "",
          ]
            .filter(Boolean)
            .join(" ");

          return (
            <li key={row.def.id} className="flow-map__item">
              {index > 0 ? <span className="flow-map__connector" aria-hidden="true" /> : null}
              <button
                type="button"
                className={classes}
                aria-current={row.isFocus ? "step" : undefined}
                aria-pressed={row.isFocus}
                disabled={!row.hasAccess && row.situation === "Sem acesso"}
                onClick={() => onSelect(row.def.id)}
              >
                <span className="flow-map__icon" aria-hidden="true">
                  {statusIcon(row.mapLabel)}
                </span>
                <span className="flow-map__num">{row.def.id}</span>
                <span className="flow-map__title">{row.def.title}</span>
                <span className="flow-map__state">{row.mapLabel}</span>
                {row.isFocus && !row.isCriticalPosition ? (
                  <span className="flow-map__focus-tag">Em foco para consulta</span>
                ) : null}
                {row.isCriticalPosition && row.isFocus ? (
                  <span className="flow-map__focus-tag">Posição e foco</span>
                ) : null}
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
