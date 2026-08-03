import { useMemo } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  canCollectEvidence,
  canEditAssessmentSetup,
  canEditFieldExecution,
  canMutateAssessments,
  canReadAssessments,
  canStartAssessment,
} from "@/lib/permissions";

export function useAssessmentPermissions(status?: string) {
  const { currentOrganization } = useOrganization();
  const roles = currentOrganization?.roles ?? [];

  return useMemo(
    () => ({
      roles,
      canRead: canReadAssessments(roles),
      canMutate: canMutateAssessments(roles),
      canEditSetup: canEditAssessmentSetup(roles, status),
      canStart: canStartAssessment(roles, status),
      canEditField: canEditFieldExecution(roles, status),
      canCollectEvidence: canCollectEvidence(roles, status),
    }),
    [roles, status],
  );
}
