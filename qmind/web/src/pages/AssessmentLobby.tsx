import { JourneyBar } from "@/components/navigation/JourneyBar";
import { NextBestAction } from "@/components/shared/NextBestAction";
import { BlockingNotice } from "@/components/shared/BlockingNotice";

export type AssessmentLobbyProps = {
  status?: string | null;
  preparationReady?: boolean;
  percent?: number;
  pendingCount?: number;
  pending?: string[];
  assessmentId?: string;
  /** Fallback preview estático (lobby-preview sem assessment). */
  currentPhaseIndex?: number;
  highestPhaseReached?: number;
  modalityLabel?: string;
  assessmentName?: string;
  organizationName?: string;
  progressLabel?: string;
  nextTitle?: string;
  nextDescription?: string;
  nextActionText?: string;
  blockers?: string[];
  onContinue?: () => void;
  onResolveBlocker?: () => void;
};

/**
 * Abertura visual da avaliação (camada de apresentação).
 */
export function AssessmentLobby({
  status,
  preparationReady = false,
  percent,
  pendingCount = 0,
  pending = [],
  assessmentId,
  currentPhaseIndex = 1,
  highestPhaseReached = 1,
  modalityLabel = "Modalidade",
  assessmentName = "Avaliação ISO 9001:2015",
  organizationName = "Organização",
  progressLabel = "Progresso geral —",
  nextTitle = "Continuar para o Plano da Auditoria",
  nextDescription = "Você já iniciou a preparação. O próximo passo é elaborar o Plano da Auditoria — propósito, programação e pessoas.",
  nextActionText = "Abrir Plano da Auditoria",
  blockers = [],
  onContinue,
  onResolveBlocker,
}: AssessmentLobbyProps) {
  return (
    <div
      className="-mx-4 -mt-8 min-h-[70vh] bg-qmind-app pb-10 sm:-mx-0 sm:rounded-qmind"
      data-testid="assessment-lobby"
    >
      <JourneyBar
        status={status}
        preparationReady={preparationReady}
        percent={percent}
        pendingCount={pendingCount}
        pending={pending}
        assessmentId={assessmentId}
        currentPhaseIndex={currentPhaseIndex}
        highestPhaseReached={highestPhaseReached}
      />

      <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
        <header className="rounded-qmind border border-qmind-future bg-qmind-surface p-5 shadow-qmind sm:p-6">
          <span className="inline-flex rounded-qmind-sm bg-qmind-app px-2.5 py-1 text-xs font-semibold text-qmind-muted">
            {modalityLabel}
          </span>
          <h1 className="mt-3 text-2xl font-bold tracking-tight text-qmind-main sm:text-3xl">
            {assessmentName}
          </h1>
          <p className="mt-2 text-sm text-qmind-muted">
            {organizationName}
            <span className="mx-2 text-qmind-disabled">·</span>
            {progressLabel}
          </p>
        </header>

        {blockers.length > 0 ? (
          <BlockingNotice
            title="Ainda não é possível avançar"
            reason="Há itens em aberto que impedem seguir para a próxima etapa."
            missingItem={blockers.slice(0, 4).join(" · ")}
            actionText="Ver o que falta e continuar"
            onResolve={() => {
              (onResolveBlocker ?? onContinue)?.();
            }}
          />
        ) : null}

        <NextBestAction
          title={nextTitle}
          description={nextDescription}
          actionText={nextActionText}
          onClick={() => {
            onContinue?.();
          }}
        />
      </div>
    </div>
  );
}
