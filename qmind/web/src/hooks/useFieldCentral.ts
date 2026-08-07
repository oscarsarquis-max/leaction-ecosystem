import { useMemo } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import { useAssessment, useAssessmentScopes } from "@/hooks/useAssessmentDetail";
import { useAuditPlan } from "@/hooks/useAuditPlan";
import { useAuditPlanSchedule } from "@/hooks/useAuditPlanSchedule";
import {
  useAssessmentEvidences,
  useAssessmentInterviews,
} from "@/hooks/useFieldExecution";
import { useAssessmentPermissions } from "@/hooks/useAssessmentPermissions";
import { buildFieldCentralModel } from "@/lib/fieldCentral";

export function useFieldCentral(assessmentId: string | undefined) {
  const { currentOrganizationId, currentOrganization } = useOrganization();
  const assessment = useAssessment(assessmentId);
  const scopes = useAssessmentScopes(assessmentId);
  const plan = useAuditPlan(assessmentId);
  const schedule = useAuditPlanSchedule(assessmentId);
  const interviews = useAssessmentInterviews(assessmentId);
  const evidences = useAssessmentEvidences(assessmentId);
  const perms = useAssessmentPermissions(assessment.data?.status);

  const loading =
    assessment.isLoading ||
    (plan.isLoading && !plan.isError) ||
    (schedule.isLoading && !schedule.isError) ||
    (interviews.isLoading && !interviews.isError) ||
    (evidences.isLoading && !evidences.isError);

  const model = useMemo(() => {
    if (!assessment.data || !currentOrganizationId) return null;
    const scopeLabels = (scopes.data ?? []).map(
      (s) => s.label || "Item de escopo",
    );
    return buildFieldCentralModel({
      organizationId: currentOrganizationId,
      organizationName:
        currentOrganization?.organizationName?.trim() || "Organização",
      assessment: assessment.data,
      plan: plan.data,
      schedule: schedule.data,
      interviews: interviews.data ?? [],
      evidences: (evidences.data ?? []).map((e) => ({
        id: e.id,
        status: e.status,
        created_at: e.created_at,
        // Origem/fase de coleta substituem interview_id na API atual.
        interview_id: null,
        question_id: null,
        collected_phase: e.collected_phase ?? null,
        collection_origin: e.collection_origin ?? null,
      })),
      scopeLabels,
      roles: currentOrganization?.roles ?? [],
      canMutate: perms.canMutate,
    });
  }, [
    assessment.data,
    scopes.data,
    plan.data,
    schedule.data,
    interviews.data,
    evidences.data,
    currentOrganizationId,
    currentOrganization,
    perms.canMutate,
  ]);

  return {
    loading,
    model,
    assessment,
    plan,
    schedule,
    interviews,
    evidences,
    perms,
    error:
      assessment.error ||
      (!plan.isLoading && plan.error) ||
      (!schedule.isLoading && schedule.error) ||
      (!interviews.isLoading && interviews.error) ||
      (!evidences.isLoading && evidences.error) ||
      null,
  };
}
