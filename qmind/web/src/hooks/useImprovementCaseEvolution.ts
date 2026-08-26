import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  getQmindClient,
  QmindApiError,
  withTenantGeneration,
  StaleTenantResponseError,
} from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import type {
  ExecutionIntelligenceRunOut,
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

export function useCreateExecutionIntelligenceRun(caseId: string | undefined) {
  const qc = useQueryClient();
  const { currentOrganizationId } = useOrganization();

  return useMutation({
    mutationFn: async () => {
      if (!caseId) throw new Error("caseId required");
      return guardTenant(async () => {
        const client = getQmindClient();
        const key =
          globalThis.crypto?.randomUUID?.() ??
          `ei-${Date.now()}-${Math.random().toString(16).slice(2)}`;
        const res =
          await client.api.createCurrentOrganizationImprovementCaseExecutionIntelligenceRun(
            {
              path: { case_id: caseId },
              headers: { "Idempotency-Key": key },
            },
          );
        if (!res.data?.id) throw new Error("Empty Execution Intelligence response");
        return res.data;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId || !caseId) return;
      await Promise.all([
        qc.invalidateQueries({
          queryKey: queryKeys.improvementCaseEvolution(
            currentOrganizationId,
            caseId,
          ),
        }),
        qc.invalidateQueries({
          queryKey: queryKeys.improvementCaseExecutionIntelligence(
            currentOrganizationId,
            caseId,
          ),
        }),
      ]);
    },
  });
}

export function useExecutionIntelligenceRuns(caseId: string | undefined) {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey:
      currentOrganizationId && caseId
        ? [
            ...queryKeys.improvementCaseExecutionIntelligence(
              currentOrganizationId,
              caseId,
            ),
            requestGeneration,
          ]
        : ["org", "none", "execution-intelligence"],
    enabled: !!currentOrganizationId && !!caseId,
    placeholderData: (previous) => previous,
    queryFn: async (): Promise<{
      latest: ExecutionIntelligenceRunOut | null;
      history: ExecutionIntelligenceRunOut[];
    }> => {
      if (!currentOrganizationId || !caseId) {
        return { latest: null, history: [] };
      }
      return guardTenant(async () => {
        const client = getQmindClient();
        const historyResponse =
          await client.api.listCurrentOrganizationImprovementCaseExecutionIntelligenceRuns(
            { path: { case_id: caseId }, query: { limit: 50 } },
          );
        const history = historyResponse.data ?? [];
        let latest: ExecutionIntelligenceRunOut | null = null;
        try {
          const latestResponse =
            await client.api.getLatestCurrentOrganizationImprovementCaseExecutionIntelligence(
              { path: { case_id: caseId } },
            );
          latest = latestResponse.data ?? null;
        } catch (error) {
          if (!(error instanceof QmindApiError) || error.status !== 404) throw error;
        }
        return { latest, history };
      });
    },
  });
}
