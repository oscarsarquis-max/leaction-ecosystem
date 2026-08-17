import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { StaleTenantResponseError } from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import {
  analyzeOrganizationIntelligence,
  fetchLatestIntelligenceRun,
  type OrganizationIntelligenceRun,
} from "@/api/organizationalIntelligenceApi";

/**
 * Latest organizational intelligence run for the current tenant.
 * Keys include organizationId + requestGeneration for tenant-switch safety.
 */
export function useLatestOrganizationalIntelligence() {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey: currentOrganizationId
      ? [
          ...queryKeys.orgIntelligenceLatest(currentOrganizationId),
          requestGeneration,
        ]
      : ["org", "none", "intelligence", "latest"],
    enabled: !!currentOrganizationId,
    queryFn: async (): Promise<OrganizationIntelligenceRun | null> => {
      const orgId = currentOrganizationId;
      if (!orgId) return null;
      try {
        const run = await fetchLatestIntelligenceRun();
        if (!run) return null;
        if (run.organization_id !== orgId) return null;
        if (run.insights.core_organization_id !== orgId) return null;
        return run;
      } catch (e) {
        if (e instanceof StaleTenantResponseError) {
          return null;
        }
        throw e;
      }
    },
  });
}

export function useAnalyzeOrganizationalIntelligence() {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();

  return useMutation({
    mutationFn: () => analyzeOrganizationIntelligence(),
    onSuccess: async (envelope) => {
      if (!currentOrganizationId) return;
      if (envelope.core_organization_id !== currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.orgIntelligenceLatest(currentOrganizationId),
      });
    },
  });
}
