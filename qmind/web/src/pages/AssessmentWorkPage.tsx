import { Link, useParams } from "react-router-dom";
import { AssessmentDetailPage } from "@/pages/AssessmentDetailPage";
import { PageHeader } from "@/components/qm";
import { JourneyBar } from "@/components/navigation/JourneyBar";
import { useAuditDashboard } from "@/hooks/useAuditDashboard";
import { JOURNEY_PHASES, phaseForStatus } from "@/lib/auditJourney";
import { LoadingPanel } from "@/components/StatePanels";

/**
 * Espaço de trabalho orientado (campo → análise → ações → relatório).
 * Reutiliza o painel operacional existente, com mapa e orientação no topo.
 */
export function AssessmentWorkPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const dash = useAuditDashboard(assessmentId);

  if (!assessmentId || dash.loading) {
    return <LoadingPanel title="Abrindo a etapa da avaliação…" />;
  }

  const phase = JOURNEY_PHASES.find(
    (p) =>
      p.id ===
      phaseForStatus(dash.status, { preparationReady: dash.preparationReady }),
  )!;

  return (
    <div className="space-y-6" data-testid="audit-work">
      <JourneyBar
        status={dash.status}
        percent={dash.percent}
        pendingCount={dash.pending.length}
        pending={dash.pending}
        assessmentId={assessmentId}
        preparationReady={dash.preparationReady}
      />

      <p className="text-sm text-[var(--qm-muted)]">
        <Link to="/assessments" className="hover:underline">
          Minhas avaliações
        </Link>
        {" / "}
        <Link to={`/assessments/${assessmentId}`} className="hover:underline">
          Mapa
        </Link>
        {" / "}
        {phase.label}
      </p>

      <PageHeader
        title={phase.label}
        explanation={phase.objective}
        expectedResult={phase.expectedResult}
        progress={`${dash.percent}% do percurso`}
        nextStep={
          dash.pending[0] ?? "Concluir as atividades desta fase e revisar o mapa"
        }
      />

      {dash.counts.evidences === 0 && dash.status === "in_progress" ? (
        <div className="rounded-md border border-[var(--qm-line)] bg-[var(--qm-surface-soft)] px-4 py-3 text-sm text-[var(--qm-muted)]">
          <p className="font-semibold text-[var(--qm-ink)]">Por que evidências?</p>
          <p className="mt-1">
            Elas comprovam o que foi observado nas entrevistas. Exemplo: ata de
            reunião, procedimento resumido ou registro de reclamação. Comece por
            uma entrevista ou anexe após responder uma pergunta.
          </p>
        </div>
      ) : null}

      <AssessmentDetailPage />
    </div>
  );
}
