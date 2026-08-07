import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { PageHeader } from "@/components/qm";
import { JourneyBar } from "@/components/navigation/JourneyBar";
import { AssessmentSectionNav } from "@/components/navigation/AssessmentSectionNav";
import { FieldCentral } from "@/components/fieldCentral/FieldCentral";
import { useFieldCentral } from "@/hooks/useFieldCentral";
import { AccessDeniedPanel, LoadingPanel } from "@/components/StatePanels";
import { ApiErrorBanner } from "@/components/ApiErrorBanner";
import { QmindApiError } from "@/api/qmindApi";
import { useRegisterAssistantContext } from "@/assistant/AssistantProvider";
import { baseAssessmentContext } from "@/assistant/contextBuilders";
import type { AssistantContext } from "@/assistant/types";
import { useOrganization } from "@/org/OrganizationProvider";

/**
 * Central operacional da execução em campo.
 * Agenda responde “quando”; aqui responde o que fazer agora.
 */
export function AssessmentWorkPage() {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const field = useFieldCentral(assessmentId);
  const org = useOrganization();

  const assistantCtx = useMemo((): AssistantContext | null => {
    if (!assessmentId || !field.model || !org.currentOrganizationId) return null;
    const model = field.model;
    const status = field.assessment.data?.status ?? "in_progress";
    const early =
      model.evidenceBuckets.find((b) => b.key === "early")?.count ?? 0;
    const pendingEv =
      (model.evidenceBuckets.find((b) => b.key === "pending")?.count ?? 0) +
      (model.evidenceBuckets.find((b) => b.key === "verifying")?.count ?? 0) +
      (model.evidenceBuckets.find((b) => b.key === "rejected")?.count ?? 0);
    return {
      ...baseAssessmentContext({
        organizationId: org.currentOrganizationId,
        organizationName: model.organizationName,
        assessmentId,
        assessmentType: field.assessment.data?.type ?? "diagnosis",
        status,
        roles: org.currentOrganization?.roles ?? [],
        canMutate: field.perms.canEditField,
        route: `/assessments/${assessmentId}/work`,
        page: "field_central",
        stage_title: "Central de Campo",
        stage_explanation:
          "Execute o dia: próxima ação, agenda de hoje, entrevistas e evidências — sem calendário completo aqui.",
        next_action: {
          label: model.nextAction.label,
          hint: model.nextAction.hint,
          href: model.nextAction.href,
          mutates: field.perms.canEditField,
        },
        pendencies: model.pendencies.map((p) => ({
          key: p.key,
          problem: p.problem,
          impact: p.impact,
          actionLabel: p.actionLabel,
          href: p.href,
        })),
        blockers: model.assistantContext.blockers,
        progress_summary: model.progress.summary,
      }),
      field: {
        currentActivityTitle:
          model.assistantContext.current_activity_title,
        earlyEvidenceCount: early,
        pendingEvidenceCount: pendingEv,
        closingPrepShow: model.closingPrep.show,
      },
    };
  }, [
    assessmentId,
    field.model,
    field.assessment.data,
    field.perms.canEditField,
    org.currentOrganizationId,
    org.currentOrganization?.roles,
  ]);

  useRegisterAssistantContext(assistantCtx);

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
