import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { queryKeys } from "@/api/queryKeys";
import {
  concludeAuditPlanning,
  getOrCreateAuditPlan,
  isAuditPlanApiError,
  markAuditPlanReady,
  patchAuditPlan,
  refreshAuditPlanFromPreparation,
  startAuditFieldExecution,
} from "@/api/auditPlanApi";
import type { AuditPlanPatch } from "@/api/auditPlanTypes";

export function useAuditPlan(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.auditPlan(currentOrganizationId, assessmentId)
        : ["org", "none", "audit-plan"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: () => getOrCreateAuditPlan(assessmentId!),
    retry: (count, err) => {
      if (isAuditPlanApiError(err) && (err.status === 404 || err.status === 403))
        return false;
      return count < 1;
    },
  });
}

function useSetPlan(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return (data: unknown) => {
    if (!currentOrganizationId) return;
    qc.setQueryData(
      queryKeys.auditPlan(currentOrganizationId, assessmentId),
      data,
    );
  };
}

export function usePatchAuditPlan(assessmentId: string) {
  const setPlan = useSetPlan(assessmentId);
  return useMutation({
    mutationFn: (body: AuditPlanPatch) => patchAuditPlan(assessmentId, body),
    onSuccess: setPlan,
  });
}

export function useMarkAuditPlanReady(assessmentId: string) {
  const setPlan = useSetPlan(assessmentId);
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (expectedUpdatedAt?: string) =>
      markAuditPlanReady(assessmentId, expectedUpdatedAt),
    onSuccess: (data) => {
      setPlan(data);
      if (currentOrganizationId) {
        void qc.invalidateQueries({
          queryKey: queryKeys.assessment(currentOrganizationId, assessmentId),
        });
      }
    },
  });
}

function useInvalidateHandoff(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return async () => {
    if (!currentOrganizationId) return;
    await Promise.all([
      qc.invalidateQueries({
        queryKey: queryKeys.assessment(currentOrganizationId, assessmentId),
      }),
      qc.invalidateQueries({
        queryKey: queryKeys.auditPlan(currentOrganizationId, assessmentId),
      }),
      qc.invalidateQueries({
        queryKey: queryKeys.auditPlanSchedule(currentOrganizationId, assessmentId),
      }),
      qc.invalidateQueries({
        queryKey: queryKeys.assessments(currentOrganizationId),
      }),
    ]);
  };
}

export function useConcludeAuditPlanning(assessmentId: string) {
  const setPlan = useSetPlan(assessmentId);
  const invalidate = useInvalidateHandoff(assessmentId);
  return useMutation({
    mutationFn: (body?: {
      expected_updated_at?: string;
      mark_ready_if_needed?: boolean;
    }) => concludeAuditPlanning(assessmentId, body),
    onSuccess: async (data) => {
      setPlan(data.plan);
      await invalidate();
    },
  });
}

export function useStartAuditFieldExecution(assessmentId: string) {
  const invalidate = useInvalidateHandoff(assessmentId);
  return useMutation({
    mutationFn: () => startAuditFieldExecution(assessmentId),
    onSuccess: async () => {
      await invalidate();
    },
  });
}

export function useRefreshAuditPlan(assessmentId: string) {
  const setPlan = useSetPlan(assessmentId);
  return useMutation({
    mutationFn: (confirmOverwrite?: boolean) =>
      refreshAuditPlanFromPreparation(assessmentId, confirmOverwrite ?? false),
    onSuccess: setPlan,
  });
}
