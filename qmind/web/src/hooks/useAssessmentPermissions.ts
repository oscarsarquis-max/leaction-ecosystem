import { useMemo } from "react";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  canEditAssessmentSetup,
  canMutateAssessments,
  canReadAssessments,
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
    }),
    [roles, status],
  );
}
