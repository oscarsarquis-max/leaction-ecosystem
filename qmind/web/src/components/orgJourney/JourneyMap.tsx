import type { OrgPhaseCard } from "@/lib/orgJourneyPhases";

type Props = {
  cards: OrgPhaseCard[];
  onSelectPhase: (phaseId: string) => void;
  emptyMode?: boolean;
};

function glyph(ui: OrgPhaseCard["uiState"]): string {
  switch (ui) {
    case "completed":
      return "✓";
    case "current":
      return "●";
    case "pending":
      return "!";
    case "blocked":
      return "✕";
    default:
      return "○";
  }
}

export function JourneyMap({ cards, onSelectPhase, emptyMode }: Props) {
  return (
    <div className="org-journey__map" data-testid="org-journey-map">
      <figure className="org-journey__figure">
        <img
          src="/assets/qmind-journey-map.png"
          alt="Ilustração do percurso da avaliação, da preparação à conclusão"
          width={1600}
          height={630}
          decoding="async"
          className="org-journey__art"
        />
        <figcaption className="sr-only">
          Imagem decorativa do caminho. Os estados reais estão na lista de fases
          abaixo.
        </figcaption>
      </figure>

      <ol className="org-journey__phases" aria-label="Fases do percurso">
        {cards.map((card) => {
          const current = card.uiState === "current";
          return (
            <li key={card.phase.id} className="org-journey__phase-item">
              <button
                type="button"
                className={`org-journey__phase org-journey__phase--${card.uiState}`}
                aria-current={current ? "step" : undefined}
                data-testid={`journey-phase-${card.phase.id}`}
                onClick={() => onSelectPhase(card.phase.id)}
              >
                <span className="org-journey__phase-glyph" aria-hidden>
                  {glyph(card.uiState)}
                </span>
                <span className="org-journey__phase-body">
                  <span className="org-journey__phase-label">
                    {card.phase.label}
                  </span>
                  <span className="org-journey__phase-state">
                    {card.stateLabel}
                    {current && !emptyMode ? " — Você está aqui" : ""}
                    {card.pendingCount > 0
                      ? ` · ${card.pendingCount} pendência(s)`
                      : ""}
                    {card.reliablePercent != null
                      ? ` · ${card.reliablePercent}% do roteiro`
                      : ""}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
