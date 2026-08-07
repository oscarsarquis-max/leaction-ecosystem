import { Link, useParams } from "react-router-dom";
import { PageHeader } from "@/components/qm";
import { JourneyBar } from "@/components/navigation/JourneyBar";
import { AssessmentSectionNav } from "@/components/navigation/AssessmentSectionNav";
import { FieldCentral } from "@/components/fieldCentral/FieldCentral";
import { useFieldCentral } from "@/hooks/useFieldCentral";
import { AccessDeniedPanel, LoadingPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { QmindApiError } from "@/api/qmindApi";

/**
 * Central operacional da execução em campo.
 * Agenda responde “quando”; aqui responde o que fazer agora.
 */
export function AssessmentWorkPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const field = useFieldCentral(assessmentId);

  if (!assessmentId || field.loading) {
    return <LoadingPanel title="Abrindo a Central de Campo…" />;
  }

  if (field.error instanceof QmindApiError && (field.error.status === 401 || field.error.status === 403)) {
    return <AccessDeniedPanel message={field.error.message} />;
  }

  if (!field.model) {
    return (
      <ApiErrorBanner
        title="Não foi possível montar a Central de Campo"
        error={field.error ?? new Error("Modelo indisponível")}
      />
    );
  }

  const model = field.model;
  const status = field.assessment.data?.status;

  return (
    <div className="space-y-6" data-testid="audit-work">
      <JourneyBar
        status={status}
        pendingCount={model.pendencies.length}
        pending={model.pendencies.map((p) => p.problem)}
        assessmentId={assessmentId}
        preparationReady={model.planReady}
      />

      <AssessmentSectionNav assessmentId={assessmentId} />

      <p className="text-sm text-[var(--qm-muted)]">
        <Link to="/assessments" className="hover:underline">
          Minhas avaliações
        </Link>
        {" / "}
        <Link to={`/assessments/${assessmentId}`} className="hover:underline">
          Visão geral
        </Link>
        {" / "}
        Central de Campo
      </p>

      <PageHeader
        eyebrow={`${model.organizationName} · ${model.todayLabel}`}
        title="Central de Campo"
        explanation={`${model.assessmentLabel} · ${model.modalityLabel}. Fase: ${model.phaseLabel}. ${model.scopeSummary}`}
        progress={model.progress.summary}
        nextStep={model.nextAction.label}
      />

      <FieldCentral
        assessmentId={assessmentId}
        model={model}
        canEditField={field.perms.canEditField}
        canCollectEvidence={field.perms.canCollectEvidence}
      />
    </div>
  );
}
