import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { StaleTenantResponseError } from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import {
  fetchOrganizationProfile,
  patchOrganizationProfile,
  type OrganizationProfile,
  type OrganizationProfilePatch,
} from "@/api/orgProfileApi";

/**
 * Reads persistent Organization Profile for the current tenant.
 * Keys include organizationId + requestGeneration so tenant switch never
 * leaves another org's profile visible.
 */
export function useOrgProfile() {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey: currentOrganizationId
      ? [...queryKeys.orgProfile(currentOrganizationId), requestGeneration]
      : ["org", "none", "profile"],
    enabled: !!currentOrganizationId,
    queryFn: async (): Promise<OrganizationProfile | null> => {
      const orgId = currentOrganizationId;
      if (!orgId) return null;
      try {
        const data = await fetchOrganizationProfile();
        if (data.organization_id !== orgId) {
          return null;
        }
        return data;
      } catch (e) {
        if (e instanceof StaleTenantResponseError) {
          return null;
        }
        throw e;
      }
    },
  });
}

export function usePatchOrgProfile() {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();

  return useMutation({
    mutationFn: (payload: OrganizationProfilePatch) =>
      patchOrganizationProfile(payload),
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      if (data.organization_id !== currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.orgProfile(currentOrganizationId),
      });
    },
  });
}
