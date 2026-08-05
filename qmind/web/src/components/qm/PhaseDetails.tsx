import {
  blockReason,
  continueHref,
  JOURNEY_PHASES,
  phaseForStatus,
  visualStateForPhase,
  type JourneyPhaseDef,
} from "@/lib/auditJourney";
import { BlockingNotice } from "@/components/shared/BlockingNotice";
import { NextBestAction } from "@/components/qm/NextBestAction";
import { StatusBadge } from "@/components/qm/StatusBadge";

type Props = {
  phase: JourneyPhaseDef;
  status: string | undefined | null;
  assessmentId?: string;
  realPending?: string[];
  preparationReady?: boolean;
  onClose: () => void;
};

function stateLabel(
  phase: JourneyPhaseDef,
  status: string | undefined | null,
  options?: { preparationReady?: boolean },
) {
  const state = visualStateForPhase(phase, status, options);
  switch (state) {
    case "completed":
      return { label: "Concluída", tone: "done" as const };
    case "current":
      return { label: "Fase atual", tone: "progress" as const };
    case "available":
      return { label: "Próxima etapa", tone: "info" as const };
    default:
      return { label: "Bloqueada", tone: "risk" as const };
  }
}

export function PhaseDetails({
  phase,
  status,
  assessmentId,
  realPending = [],
  preparationReady = false,
  onClose,
}: Props) {
  const opts = { preparationReady };
  const badge = stateLabel(phase, status, opts);
  const state = visualStateForPhase(phase, status, opts);
  const block = blockReason(phase, status, opts);
  const action =
    assessmentId && (state === "current" || state === "available")
      ? continueHref(assessmentId, status, { preparationReady })
      : null;

  return (
    <div
      className="journey-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby={`phase-${phase.id}`}
      data-testid="journey-phase-panel"
    >
      <div className="journey-panel__card">
        <header className="flex items-start justify-between gap-3">
          <div>
            <StatusBadge label={badge.label} tone={badge.tone} />
            <h2
              id={`phase-${phase.id}`}
              className="mt-2 font-display text-2xl text-[var(--qm-ink)]"
            >
              {phase.label}
            </h2>
            <p className="mt-1 text-sm text-[var(--qm-muted)]">
              Tempo estimado: {phase.effortHint}
            </p>
          </div>
          <button
            type="button"
            className="qm-btn-secondary"
            onClick={onClose}
            data-testid="journey-phase-back"
          >
            Voltar
          </button>
        </header>

        <dl className="mt-5 space-y-4 text-sm">
          <div>
            <dt className="font-semibold text-[var(--qm-ink)]">Objetivo</dt>
            <dd className="mt-1 text-[var(--qm-muted)]">{phase.objective}</dd>
          </div>
          <div>
            <dt className="font-semibold text-[var(--qm-ink)]">Atividades esperadas</dt>
            <dd className="mt-1 text-[var(--qm-muted)]">
              <ul className="list-disc space-y-1 pl-5">
                {phase.activities.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-[var(--qm-ink)]">Resultado produzido</dt>
            <dd className="mt-1 text-[var(--qm-muted)]">{phase.expectedResult}</dd>
          </div>
          <div>
            <dt className="font-semibold text-[var(--qm-ink)]">Critérios para avançar</dt>
            <dd className="mt-1 text-[var(--qm-muted)]">{phase.advanceCriteria}</dd>
          </div>
        </dl>

        {state === "current" && realPending.length > 0 ? (
          <div className="mt-4">
            <p className="text-sm font-semibold text-[var(--qm-ink)]">Pendências reais</p>
            <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-[var(--qm-muted)]">
              {realPending.slice(0, 6).map((p) => (
                <li key={p}>{p}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {block ? (
          <div className="mt-4">
            <BlockingNotice
              title={`${phase.label} bloqueada`}
              reason={`A fase “${phase.label}” só é liberada após a conclusão da etapa anterior.`}
              missingItem={block}
              actionText={`Voltar para ${JOURNEY_PHASES.find((p) => p.id === phaseForStatus(status, opts))?.label ?? "a fase atual"}`}
              onResolve={onClose}
            />
          </div>
        ) : null}

        {action ? (
          <div className="mt-5">
            <NextBestAction
              href={action.href}
              label={
                state === "current"
                  ? "Continuar avaliação"
                  : `Ir para ${phase.label}`
              }
              hint="Ação recomendada para esta fase"
            />
          </div>
        ) : null}

        <div className="mt-6 flex justify-end border-t border-[var(--qm-line)] pt-4">
          <button
            type="button"
            className="qm-btn-secondary"
            onClick={onClose}
            data-testid="journey-phase-back-footer"
          >
            Voltar
          </button>
        </div>
      </div>
      <button
        type="button"
        className="journey-panel__backdrop"
        aria-label="Voltar ao percurso"
        onClick={onClose}
      />
    </div>
  );
}
