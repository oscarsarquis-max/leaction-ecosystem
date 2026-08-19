import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  getQmindClient,
  withTenantGeneration,
  StaleTenantResponseError,
} from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import type {
  ImprovementCaseCreate,
  ImprovementCaseOut,
  ImprovementCasePatch,
} from "@qmind/api-client";

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

export function useImprovementCases() {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey: currentOrganizationId
      ? [...queryKeys.improvementCases(currentOrganizationId), requestGeneration]
      : ["org", "none", "improvement-cases"],
    enabled: !!currentOrganizationId,
    queryFn: async (): Promise<ImprovementCaseOut[]> => {
      const orgId = currentOrganizationId;
      if (!orgId) return [];
      try {
        return await guardTenant(async () => {
          const client = getQmindClient();
          const res = await client.api.listCurrentOrganizationImprovementCases();
          const rows = res.data ?? [];
          return rows.filter((c) => c.organization_id === orgId);
        });
      } catch (e) {
        if (e instanceof StaleTenantResponseError) return [];
        throw e;
      }
    },
  });
}

export function useImprovementCase(caseId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey:
      currentOrganizationId && caseId
        ? [
            ...queryKeys.improvementCase(currentOrganizationId, caseId),
            requestGeneration,
          ]
        : ["org", "none", "improvement-case"],
    enabled: !!currentOrganizationId && !!caseId,
    queryFn: async (): Promise<ImprovementCaseOut | null> => {
      const orgId = currentOrganizationId;
      if (!orgId || !caseId) return null;
      try {
        return await guardTenant(async () => {
          const client = getQmindClient();
          const res = await client.api.getCurrentOrganizationImprovementCase({
            path: { case_id: caseId },
          });
          const data = res.data;
          if (!data || data.organization_id !== orgId) return null;
          return data;
        });
      } catch (e) {
        if (e instanceof StaleTenantResponseError) return null;
        throw e;
      }
    },
  });
}

export function useCreateImprovementCase() {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();

  return useMutation({
    mutationFn: async (body: ImprovementCaseCreate) => {
      return guardTenant(async () => {
        const client = getQmindClient();
        const res = await client.api.createCurrentOrganizationImprovementCase({
          body,
        });
        const data =
          res && typeof res === "object" && "data" in res
            ? (res as { data?: ImprovementCaseOut }).data
            : (res as ImprovementCaseOut | undefined);
        if (!data?.id) throw new Error("Empty create response");
        return data;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.improvementCases(currentOrganizationId),
      });
    },
  });
}

export function usePatchImprovementCase(caseId: string | undefined) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();

  return useMutation({
    mutationFn: async (body: ImprovementCasePatch) => {
      if (!caseId) throw new Error("caseId required");
      return guardTenant(async () => {
        const client = getQmindClient();
        const res = await client.api.patchCurrentOrganizationImprovementCase({
          path: { case_id: caseId },
          body,
        });
        const data =
          res && typeof res === "object" && "data" in res
            ? (res as { data?: ImprovementCaseOut }).data
            : (res as ImprovementCaseOut | undefined);
        if (!data?.id) throw new Error("Empty patch response");
        return data;
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      await Promise.all([
        qc.invalidateQueries({
          queryKey: queryKeys.improvementCases(currentOrganizationId),
        }),
        qc.invalidateQueries({
          queryKey: queryKeys.improvementCase(currentOrganizationId, data.id),
        }),
        qc.invalidateQueries({
          queryKey: queryKeys.improvementCaseAnalysisRuns(
            currentOrganizationId,
            data.id,
          ),
        }),
      ]);
    },
  });
}
