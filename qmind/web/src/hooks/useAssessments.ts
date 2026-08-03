import { useQuery } from "@tanstack/react-query";
import type { AssessmentOut } from "@qmind/api-client";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  getQmindClient,
  withTenantGeneration,
  StaleTenantResponseError,
} from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";

export function useAssessments() {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey: currentOrganizationId
      ? [...queryKeys.assessments(currentOrganizationId), requestGeneration]
      : ["org", "none", "assessments"],
    enabled: !!currentOrganizationId,
    queryFn: async (): Promise<AssessmentOut[]> => {
      const orgId = currentOrganizationId;
      if (!orgId) return [];
      const client = getQmindClient();
      try {
        const data = await withTenantGeneration(async () => {
          const res = await client.api.listAssessments();
          return res.data ?? [];
        });
        // Hard isolation: never render rows from another tenant
        return data.filter((a) => a.organization_id === orgId);
      } catch (e) {
        if (e instanceof StaleTenantResponseError) {
          return [];
        }
        throw e;
      }
    },
  });
}
