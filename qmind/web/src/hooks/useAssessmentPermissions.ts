import { useMemo } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  canCollectEvidence,
  canCreateFindings,
  canEditAssessmentSetup,
  canEditFieldExecution,
  canElaborateMaturity,
  canMutateAssessments,
  canReadAssessments,
  canReviewFindings,
  canReviewMaturity,
  canStartAssessment,
  canWorkFindingsOnAssessment,
  canWorkMaturityOnAssessment,
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
    }),
    [roles, status, membershipId],
  );
}
