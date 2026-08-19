import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  getQmindClient,
  withTenantGeneration,
  StaleTenantResponseError,
} from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import type {
  ActionItemOut,
  FindingActionCreate,
  ImprovementCaseActionsOut,
} from "@qmind/api-client";

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

export function useImprovementCaseActions(caseId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey:
      currentOrganizationId && caseId
        ? [
            ...queryKeys.improvementCaseActions(currentOrganizationId, caseId),
            requestGeneration,
          ]
        : ["org", "none", "improvement-case-actions"],
    enabled: !!currentOrganizationId && !!caseId,
    queryFn: async (): Promise<ImprovementCaseActionsOut> => {
      const orgId = currentOrganizationId;
      if (!orgId || !caseId) return { plan: null, items: [] };
      try {
        return await guardTenant(async () => {
          const client = getQmindClient();
          const res =
            await client.api.listCurrentOrganizationImprovementCaseActions({
              path: { case_id: caseId },
            });
          const data = res.data;
          if (!data) return { plan: null, items: [] };
          if (data.plan && data.plan.organization_id !== orgId) {
            return { plan: null, items: [] };
          }
          return {
            plan: data.plan ?? null,
            items: (data.items ?? []).filter((i) => i.organization_id === orgId),
          };
        });
      } catch (e) {
        if (e instanceof StaleTenantResponseError) {
          return { plan: null, items: [] };
        }
        throw e;
      }
    },
  });
}

export function useCreateActionFromFinding(caseId: string | undefined) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();

  return useMutation({
    mutationFn: async (args: {
      runId: string;
      findingCode: string;
      body: FindingActionCreate;
    }) => {
      if (!caseId) throw new Error("caseId required");
      return guardTenant(async () => {
        const client = getQmindClient();
        const res = await client.api.createActionFromImprovementCaseFinding({
          path: {
            case_id: caseId,
            run_id: args.runId,
            finding_code: args.findingCode,
          },
          body: args.body,
        });
        const data =
          res && typeof res === "object" && "data" in res
            ? (res as { data?: ActionItemOut }).data
            : (res as ActionItemOut | undefined);
        if (!data?.id) throw new Error("Empty action create response");
        return data;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId || !caseId) return;
      await Promise.all([
        qc.invalidateQueries({
          queryKey: queryKeys.improvementCaseActions(
            currentOrganizationId,
            caseId,
          ),
        }),
        qc.invalidateQueries({
          queryKey: queryKeys.improvementCaseAnalysisRuns(
            currentOrganizationId,
            caseId,
          ),
        }),
      ]);
    },
  });
}
