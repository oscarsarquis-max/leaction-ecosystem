import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  getQmindClient,
  withTenantGeneration,
  StaleTenantResponseError,
  QmindApiError,
} from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import { newIdempotencyKey } from "@/lib/idempotency";

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

function isConflictOrStale(error: unknown): boolean {
  return (
    error instanceof QmindApiError && (error.status === 409 || error.status === 422)
  );
}

async function invalidateMap(
  qc: ReturnType<typeof useQueryClient>,
  organizationId: string,
  assessmentId: string,
) {
  await Promise.all([
    qc.invalidateQueries({
      queryKey: queryKeys.assessmentEvolutionMap(organizationId, assessmentId),
    }),
    qc.invalidateQueries({
      queryKey: queryKeys.assessmentActionPlans(organizationId, assessmentId),
    }),
    qc.invalidateQueries({
      queryKey: queryKeys.assessment(organizationId, assessmentId),
    }),
  ]);
}

export function useEvolutionMap(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentEvolutionMap(currentOrganizationId, assessmentId)
        : ["org", "none", "evolution-map"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.getAssessmentEvolutionMap({
          path: { assessment_id: assessmentId! },
        });
        return res.data ?? null;
      });
    },
  });
}

export function useGenerateEvolutionMap(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input?: { mode?: "preliminary" | "analysis_ready" | null }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.generateAssessmentEvolutionMap({
          path: { assessment_id: assessmentId },
          body: { mode: input?.mode ?? null },
          headers: { "Idempotency-Key": newIdempotencyKey("evo-gen") },
        });
        return res.data!;
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      qc.setQueryData(
        queryKeys.assessmentEvolutionMap(currentOrganizationId, assessmentId),
        data,
      );
      await invalidateMap(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateMap(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useAcceptEvolutionSuggestion(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (suggestionId: string) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.acceptEvolutionSuggestion({
          path: { suggestion_id: suggestionId },
          headers: { "Idempotency-Key": newIdempotencyKey("evo-accept") },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateMap(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useDismissEvolutionSuggestion(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: { suggestionId: string; reason: string }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.dismissEvolutionSuggestion({
          path: { suggestion_id: input.suggestionId },
          body: { reason: input.reason },
          headers: { "Idempotency-Key": newIdempotencyKey("evo-dismiss") },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateMap(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useInvestigateEvolutionSuggestion(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      suggestionId: string;
      missing_information: string;
    }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.investigateEvolutionSuggestion({
          path: { suggestion_id: input.suggestionId },
          body: { missing_information: input.missing_information },
          headers: { "Idempotency-Key": newIdempotencyKey("evo-invest") },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateMap(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useConvertEvolutionSuggestion(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      suggestionId: string;
      action_plan_id?: string | null;
      create_plan_if_missing?: boolean;
      action_kind: "correction" | "corrective_action" | "improvement";
      description: string;
      owner_membership_id: string;
      due_at: string;
      efficacy_required?: boolean | null;
      title?: string | null;
    }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.convertEvolutionSuggestionToAction({
          path: { suggestion_id: input.suggestionId },
          body: {
            action_plan_id: input.action_plan_id ?? null,
            create_plan_if_missing: input.create_plan_if_missing ?? false,
            action_kind: input.action_kind,
            description: input.description,
            owner_membership_id: input.owner_membership_id,
            due_at: input.due_at,
            efficacy_required: input.efficacy_required ?? null,
            title: input.title ?? null,
          },
          headers: { "Idempotency-Key": newIdempotencyKey("evo-convert") },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateMap(qc, currentOrganizationId, assessmentId);
    },
  });
}
