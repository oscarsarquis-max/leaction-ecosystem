import { useState } from "react";
import {
  JOURNEY_PHASES,
  journeyDisplayIndex,
  phaseForStatus,
  visualStateForPhase,
  type JourneyPhaseDef,
  type PhaseVisualState,
} from "@/lib/auditJourney";
import { PhaseDetails } from "@/components/qm/PhaseDetails";

export const JOURNEY_PHASE_LABELS = JOURNEY_PHASES.map((p) => p.label);

type Props = {
  /** Status real da avaliação — fonte preferida da barra. */
  status?: string | null;
  preparationReady?: boolean;
  percent?: number;
  pendingCount?: number;
  pending?: string[];
  assessmentId?: string;
  /**
   * Fallback só para preview estático (sem assessment).
   * Ignorado quando `status` é informado.
   */
  currentPhaseIndex?: number;
  highestPhaseReached?: number;
};

type ChipStatus = "completed" | "current" | "available" | "blocked";

function toChip(state: PhaseVisualState): ChipStatus {
  if (state === "available") return "available";
  if (state === "completed") return "completed";
  if (state === "current") return "current";
  return "blocked";
}

/**
 * Única barra de percurso da aplicação — sticky, mesma lógica e visual em mapa,
 * preparação e trabalho.
 */
export function JourneyBar({
  status,
  preparationReady = false,
  percent,
  pendingCount = 0,
  pending = [],
  assessmentId,
  currentPhaseIndex,
  highestPhaseReached,
}: Props) {
  const [open, setOpen] = useState<JourneyPhaseDef | null>(null);
  const opts = { preparationReady };
  const hasStatus = status !== undefined && status !== null && status !== "";

  const displayIndex = hasStatus
    ? journeyDisplayIndex(status, opts)
    : Math.max(0, currentPhaseIndex ?? 0);

  const ceiling = hasStatus
    ? Math.max(displayIndex + 1, displayIndex)
    : highestPhaseReached === undefined
      ? displayIndex
      : highestPhaseReached;

  const current = JOURNEY_PHASES[displayIndex];
  const interactive = !!assessmentId && hasStatus;

  return (
    <nav
      className="sticky top-0 z-50 border-b border-qmind-semantic-future bg-qmind-surface/95 shadow-qmind backdrop-blur"
      aria-label="Percurso da avaliação"
      data-testid="journey-bar"
    >
      {(percent !== undefined || pendingCount > 0 || current) && (
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-3 pt-2 sm:px-4">
          <p className="text-xs font-semibold text-qmind-muted">
            Fase atual:{" "}
            <span className="text-qmind-main">{current?.label ?? "—"}</span>
          </p>
          {percent !== undefined ? (
            <p className="text-xs text-qmind-muted" data-testid="journey-percent">
              {percent}% do percurso
              {pendingCount > 0 ? ` · ${pendingCount} pendência(s)` : ""}
            </p>
          ) : null}
        </div>
      )}

      <ol className="qmind-scrollbar-none mx-auto flex max-w-5xl items-center gap-1 overflow-x-auto px-3 py-2.5 sm:px-4">
        {JOURNEY_PHASES.map((phase, index) => {
          const chip = hasStatus
            ? toChip(visualStateForPhase(phase, status, opts))
            : resolveIndexChip(index, displayIndex, ceiling);

          const body = (
            <>
              <span className="mr-1.5 inline-flex" aria-hidden>
                {chip === "completed"
                  ? "✓"
                  : chip === "blocked"
                    ? "#"
                    : index + 1}
              </span>
              {phase.label}
            </>
          );

          return (
            <li key={phase.id} className="flex shrink-0 items-center gap-1">
              {index > 0 ? (
                <span
                  className="px-1 text-sm font-semibold text-qmind-semantic-disabled"
                  aria-hidden
                >
                  ›
                </span>
              ) : null}
              {interactive ? (
                <button
                  type="button"
                  className={phaseClass(chip)}
                  aria-current={chip === "current" ? "step" : undefined}
                  title={
                    chip === "blocked"
                      ? "Fase bloqueada — toque para ver o motivo"
                      : phase.label
                  }
                  onClick={() => setOpen(phase)}
                >
                  {body}
                </button>
              ) : (
                <span
                  className={phaseClass(chip)}
                  aria-current={chip === "current" ? "step" : undefined}
                >
                  {body}
                </span>
              )}
            </li>
          );
        })}
      </ol>

      {open && hasStatus ? (
        <PhaseDetails
          phase={open}
          status={status}
          assessmentId={assessmentId}
          realPending={pending}
          preparationReady={preparationReady}
          onClose={() => setOpen(null)}
        />
      ) : null}
    </nav>
  );
}

function resolveIndexChip(
  index: number,
  currentPhaseIndex: number,
  highestPhaseReached: number,
): ChipStatus {
  if (index < currentPhaseIndex) return "completed";
  if (index === currentPhaseIndex) return "current";
  if (index === currentPhaseIndex + 1 && index <= highestPhaseReached + 1) {
    return "available";
  }
  if (index > highestPhaseReached) return "blocked";
  return "available";
}

function phaseClass(status: ChipStatus): string {
  const base =
    "inline-flex items-center rounded-qmind-sm px-2.5 py-1.5 text-xs font-semibold whitespace-nowrap transition-[var(--qmind-transition-subtle)] sm:text-sm";
  if (status === "current") {
    return `${base} bg-qmind-semantic-current font-bold text-white`;
  }
  /* Demais fases: sem fundo (ou branco) + texto verde escuro */
  return `${base} bg-qmind-surface text-qmind-semantic-current`;
}

/** Helper exportado para páginas que montam o header da fase. */
export function currentJourneyLabel(
  status: string | undefined | null,
  preparationReady = false,
): string {
  return (
    JOURNEY_PHASES.find((p) => p.id === phaseForStatus(status, { preparationReady }))
      ?.label ?? "—"
  );
}
