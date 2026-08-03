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

export type ActionKind = "correction" | "corrective_action" | "improvement";

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

function isConflictOrStale(error: unknown): boolean {
  return error instanceof QmindApiError && (error.status === 409 || error.status === 422);
}

async function invalidatePlans(
  qc: ReturnType<typeof useQueryClient>,
  organizationId: string,
  assessmentId: string,
  planId?: string,
) {
  const jobs = [
    qc.invalidateQueries({
      queryKey: queryKeys.assessmentActionPlans(organizationId, assessmentId),
    }),
    qc.invalidateQueries({
      queryKey: queryKeys.assessment(organizationId, assessmentId),
    }),
  ];
  if (planId) {
    jobs.push(
      qc.invalidateQueries({
        queryKey: queryKeys.actionPlanItems(organizationId, planId),
      }),
    );
  }
  await Promise.all(jobs);
}

export function useActionPlans(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentActionPlans(currentOrganizationId, assessmentId)
        : ["org", "none", "action-plans"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.listActionPlans({
          query: { assessment_id: assessmentId! },
        });
        return res.data ?? [];
      });
    },
  });
}

export function useActionPlanItems(planId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && planId
        ? queryKeys.actionPlanItems(currentOrganizationId, planId)
        : ["org", "none", "action-items"],
    enabled: !!currentOrganizationId && !!planId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.listActionItems({
          path: { plan_id: planId! },
        });
        return res.data ?? [];
      });
    },
  });
}

export function useCreateActionPlan(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (empty_plan_rationale?: string | null) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.createActionPlan({
          body: {
            assessment_id: assessmentId,
            empty_plan_rationale: empty_plan_rationale ?? null,
          },
          headers: { "Idempotency-Key": newIdempotencyKey("action-plan") },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidatePlans(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidatePlans(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useCreateActionItem(assessmentId: string, planId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: {
      finding_id?: string | null;
      action_kind: ActionKind;
      description: string;
      owner_membership_id: string;
      due_at: string;
      efficacy_required?: boolean | null;
    }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.createActionItem({
          path: { plan_id: planId },
          body: {
            finding_id: input.finding_id ?? null,
            action_kind: input.action_kind,
            description: input.description,
            owner_membership_id: input.owner_membership_id,
            due_at: input.due_at,
            efficacy_required: input.efficacy_required ?? null,
          },
          headers: { "Idempotency-Key": newIdempotencyKey("action-item") },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidatePlans(qc, currentOrganizationId, assessmentId, planId);
    },
  });
}

export function useOpenAssessmentActions(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.openAssessmentActions({
          path: { assessment_id: assessmentId },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidatePlans(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidatePlans(qc, currentOrganizationId, assessmentId);
    },
  });
}

type PlanTransition = "activate" | "complete" | "cancel";

export function useActionPlanTransition(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { planId: string; kind: PlanTransition }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const path = { plan_id: payload.planId };
        if (payload.kind === "activate") {
          return (await client.api.activateActionPlan({ path })).data!;
        }
        if (payload.kind === "complete") {
          return (await client.api.completeActionPlan({ path })).data!;
        }
        return (await client.api.cancelActionPlan({ path })).data!;
      });
    },
    onSuccess: async (_data, vars) => {
      if (!currentOrganizationId) return;
      await invalidatePlans(qc, currentOrganizationId, assessmentId, vars.planId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidatePlans(qc, currentOrganizationId, assessmentId);
    },
  });
}

type ItemTransition =
  | { kind: "start" }
  | { kind: "mark_implemented" }
  | { kind: "validate" }
  | { kind: "reject_implementation"; reason: string }
  | { kind: "confirm_efficacy" }
  | { kind: "fail_efficacy"; reason: string }
  | { kind: "reopen" }
  | { kind: "close_ineffective" }
  | { kind: "cancel"; reason: string };

export function useActionItemTransition(assessmentId: string, planId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { itemId: string; transition: ItemTransition }) => {
      const client = getQmindClient();
      const path = { item_id: payload.itemId };
      return guardTenant(async () => {
        switch (payload.transition.kind) {
          case "start":
            return (await client.api.startActionItem({ path })).data!;
          case "mark_implemented":
            return (await client.api.markActionItemImplemented({ path })).data!;
          case "validate":
            return (await client.api.validateActionItem({ path })).data!;
          case "reject_implementation":
            return (
              await client.api.rejectActionItemImplementation({
                path,
                body: { reason: payload.transition.reason },
              })
            ).data!;
          case "confirm_efficacy":
            return (await client.api.confirmActionItemEfficacy({ path })).data!;
          case "fail_efficacy":
            return (
              await client.api.failActionItemEfficacy({
                path,
                body: { reason: payload.transition.reason },
              })
            ).data!;
          case "reopen":
            return (await client.api.reopenActionItem({ path })).data!;
          case "close_ineffective":
            return (await client.api.closeIneffectiveActionItem({ path })).data!;
          case "cancel":
            return (
              await client.api.cancelActionItem({
                path,
                body: { reason: payload.transition.reason },
              })
            ).data!;
        }
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidatePlans(qc, currentOrganizationId, assessmentId, planId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidatePlans(qc, currentOrganizationId, assessmentId, planId);
    },
  });
}
