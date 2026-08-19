import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  getQmindClient,
  withTenantGeneration,
  StaleTenantResponseError,
} from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import type { ImprovementCaseAnalysisRunOut } from "@qmind/api-client";

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

function unwrapRun(
  res: unknown,
): ImprovementCaseAnalysisRunOut | undefined {
  if (res && typeof res === "object" && "data" in res) {
    return (res as { data?: ImprovementCaseAnalysisRunOut }).data;
  }
  return res as ImprovementCaseAnalysisRunOut | undefined;
}

export function useImprovementCaseAnalysisRuns(caseId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey:
      currentOrganizationId && caseId
        ? [
            ...queryKeys.improvementCaseAnalysisRuns(
              currentOrganizationId,
              caseId,
            ),
            requestGeneration,
          ]
        : ["org", "none", "improvement-case-analysis-runs"],
    enabled: !!currentOrganizationId && !!caseId,
    queryFn: async (): Promise<ImprovementCaseAnalysisRunOut[]> => {
      const orgId = currentOrganizationId;
      if (!orgId || !caseId) return [];
      try {
        return await guardTenant(async () => {
          const client = getQmindClient();
          const res =
            await client.api.listCurrentOrganizationImprovementCaseAnalysisRuns(
              { path: { case_id: caseId }, query: { limit: 50 } },
            );
          const rows = res.data ?? [];
          return rows.filter(
            (r) =>
              r.organization_id === orgId &&
              r.improvement_case_id === caseId,
          );
        });
      } catch (e) {
        if (e instanceof StaleTenantResponseError) return [];
        throw e;
      }
    },
  });
}

export function useCreateImprovementCaseAnalysisRun(caseId: string | undefined) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();

  return useMutation({
    mutationFn: async () => {
      if (!caseId) throw new Error("caseId required");
      return guardTenant(async () => {
        const client = getQmindClient();
        const res =
          await client.api.createCurrentOrganizationImprovementCaseAnalysisRun({
            path: { case_id: caseId },
          });
        const data = unwrapRun(res);
        if (!data?.id) throw new Error("Empty analysis run response");
        return data;
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.improvementCaseAnalysisRuns(
          currentOrganizationId,
          data.improvement_case_id,
        ),
      });
    },
  });
}
