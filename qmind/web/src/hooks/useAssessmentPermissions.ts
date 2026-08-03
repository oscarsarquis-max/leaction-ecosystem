import { useMemo } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  canBeginAssessmentReport,
  canCloseAssessment,
  canCollectEvidence,
  canConfirmActionEfficacy,
  canCreateFindings,
  canEditAssessmentSetup,
  canEditFieldExecution,
  canElaborateMaturity,
  canElaborateReports,
  canManageActionPlans,
  canMutateAssessments,
  canReadAssessments,
  canReopenAssessment,
  canReviewFindings,
  canReviewMaturity,
  canReviewReports,
  canStartAssessment,
  canValidateActionItems,
  canWorkActionPlansOnAssessment,
  canWorkFindingsOnAssessment,
  canWorkMaturityOnAssessment,
  canWorkReportsOnAssessment,
} from "@/lib/permissions";

export function useAssessmentPermissions(status?: string) {
  const { currentOrganization } = useOrganization();
  const roles = currentOrganization?.roles ?? [];
  const membershipId = currentOrganization?.id ?? null;

  return useMemo(
    () => ({
      roles,
      membershipId,
      canRead: canReadAssessments(roles),
      canMutate: canMutateAssessments(roles),
      canEditSetup: canEditAssessmentSetup(roles, status),
      canStart: canStartAssessment(roles, status),
      canEditField: canEditFieldExecution(roles, status),
      canCollectEvidence: canCollectEvidence(roles, status),
      canWorkFindings: canWorkFindingsOnAssessment(status),
      canCreateFindings: canCreateFindings(roles, status),
      canReviewFindings: canReviewFindings(roles),
      canWorkMaturity: canWorkMaturityOnAssessment(status),
      canElaborateMaturity: canElaborateMaturity(roles, status),
      canReviewMaturity: canReviewMaturity(roles),
      canWorkActionPlans: canWorkActionPlansOnAssessment(status),
      canManageActionPlans: canManageActionPlans(roles, status),
      canValidateActionItems: canValidateActionItems(roles),
      canConfirmActionEfficacy: canConfirmActionEfficacy(roles),
      canWorkReports: canWorkReportsOnAssessment(status),
      canElaborateReports: canElaborateReports(roles, status),
      canReviewReports: canReviewReports(roles),
      canBeginReport: canBeginAssessmentReport(roles, status),
      canCloseAssessment: canCloseAssessment(roles, status),
      canReopenAssessment: canReopenAssessment(roles, status),
    }),
    [roles, status, membershipId],
  );
}
