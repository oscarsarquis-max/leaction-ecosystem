import type { AssistantContext } from "@/assistant/types";
import { labelAssessmentStatus, labelAssessmentType } from "@/lib/labels";
import { JOURNEY_PHASES, phaseForStatus } from "@/lib/auditJourney";

export function assessmentAllowedLinks(assessmentId: string): string[] {
  return [
    "/assessments",
    "/assessments/new",
    `/assessments/${assessmentId}`,
    `/assessments/${assessmentId}/guided`,
    `/assessments/${assessmentId}/audit-plan`,
    `/assessments/${assessmentId}/work`,
    `/assessments/${assessmentId}/advanced`,
  ];
}

export function phaseLabelForStatus(
  status: string | null | undefined,
  preparationReady = true,
): string | null {
  if (!status) return null;
  const id = phaseForStatus(status, { preparationReady });
  return JOURNEY_PHASES.find((p) => p.id === id)?.label ?? labelAssessmentStatus(status);
}

export function baseAssessmentContext(input: {
  organizationId: string;
  organizationName: string;
  assessmentId: string;
  assessmentType: string;
  status: string;
  roles: string[];
  canMutate: boolean;
  route: string;
  page: AssistantContext["page"];
  stage_title: string;
  stage_explanation: string;
  preparationReady?: boolean;
  next_action: AssistantContext["next_action"];
  pendencies?: AssistantContext["pendencies"];
  blockers?: string[];
  progress_summary?: string | null;
}): Omit<AssistantContext, "wizard" | "plan" | "field"> {
  return {
    organization_id: input.organizationId,
    organization_name: input.organizationName,
    assessment_id: input.assessmentId,
    assessment_label: labelAssessmentType(input.assessmentType),
    route: input.route,
    page: input.page,
    phase_label: phaseLabelForStatus(
      input.status,
      input.preparationReady ?? true,
    ),
    assessment_status: input.status,
    user_roles: input.roles,
    can_mutate: input.canMutate,
    next_action: input.next_action,
    pendencies: input.pendencies ?? [],
    blockers: input.blockers ?? [],
    progress_summary: input.progress_summary ?? null,
    allowed_links: assessmentAllowedLinks(input.assessmentId),
    stage_title: input.stage_title,
    stage_explanation: input.stage_explanation,
  };
}
