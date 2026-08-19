import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  getQmindClient,
  withTenantGeneration,
  StaleTenantResponseError,
} from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import type {
  ImprovementCaseEvolutionOut,
  OutcomeObservationCreate,
  OutcomeObservationOut,
} from "@qmind/api-client";

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

export function useImprovementCaseEvolution(caseId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey:
      currentOrganizationId && caseId
        ? [
            ...queryKeys.improvementCaseEvolution(
              currentOrganizationId,
              caseId,
            ),
            requestGeneration,
          ]
        : ["org", "none", "improvement-case-evolution"],
    enabled: !!currentOrganizationId && !!caseId,
    queryFn: async (): Promise<ImprovementCaseEvolutionOut | null> => {
      const orgId = currentOrganizationId;
      if (!orgId || !caseId) return null;
      try {
        return await guardTenant(async () => {
          const client = getQmindClient();
          const res =
            await client.api.getCurrentOrganizationImprovementCaseEvolution({
              path: { case_id: caseId },
            });
          const data = res.data;
          if (!data?.case || data.case.organization_id !== orgId) return null;
          if (data.case.id !== caseId) return null;
          return data;
        });
      } catch (e) {
        if (e instanceof StaleTenantResponseError) return null;
        throw e;
      }
    },
  });
}

export function useCreateOutcomeObservation(caseId: string | undefined) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();

  return useMutation({
    mutationFn: async (payload: OutcomeObservationCreate) => {
      if (!caseId) throw new Error("caseId required");
      return guardTenant(async () => {
        const client = getQmindClient();
        const res =
          await client.api.createCurrentOrganizationImprovementCaseOutcomeObservation(
            {
              path: { case_id: caseId },
              body: payload,
            },
          );
        const data = res.data as OutcomeObservationOut | undefined;
        if (!data?.id) throw new Error("Empty observation response");
        return data;
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.improvementCaseEvolution(
          currentOrganizationId,
          data.improvement_case_id,
        ),
      });
      await qc.invalidateQueries({
        queryKey: queryKeys.improvementCase(
          currentOrganizationId,
          data.improvement_case_id,
        ),
      });
    },
  });
}
