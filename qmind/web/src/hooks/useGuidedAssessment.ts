import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { queryKeys } from "@/api/queryKeys";
import {
  fetchGuidedCatalog,
  getOrCreateGuidedSession,
  isGuidedApiError,
  patchGuidedPosition,
  patchGuidedSession,
  upsertGuidedAnswer,
} from "@/api/guidedApi";
import type {
  GuidedAnswerUpsert,
  GuidedContext,
  GuidedStep,
} from "@/api/guidedTypes";

export function useGuidedCatalog() {
  return useQuery({
    queryKey: queryKeys.guidedCatalog,
    queryFn: fetchGuidedCatalog,
    staleTime: 5 * 60_000,
  });
}

export function useGuidedSession(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.guidedSession(currentOrganizationId, assessmentId)
        : ["org", "none", "guided"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: () => getOrCreateGuidedSession(assessmentId!),
    // 404 = roteiro ainda não iniciado (fases posteriores sem sessão).
    retry: (count, err) => {
      if (isGuidedApiError(err) && err.status === 404) return false;
      return count < 1;
    },
  });
}

export function usePatchGuidedSession(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      context?: GuidedContext;
      current_step?: GuidedStep;
      current_question_id?: string | null;
    }) =>
      patchGuidedSession(assessmentId, {
        context: body.context as unknown as Record<string, unknown>,
        current_step: body.current_step,
        current_question_id: body.current_question_id,
      }),
    onSuccess: (data) => {
      if (!currentOrganizationId) return;
      qc.setQueryData(
        queryKeys.guidedSession(currentOrganizationId, assessmentId),
        data,
      );
    },
  });
}

export function usePatchGuidedPosition(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      current_step: GuidedStep;
      current_question_id?: string | null;
    }) => patchGuidedPosition(assessmentId, body),
    onSuccess: (data) => {
      if (!currentOrganizationId) return;
      qc.setQueryData(
        queryKeys.guidedSession(currentOrganizationId, assessmentId),
        data,
      );
    },
  });
}

export function useUpsertGuidedAnswer(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { questionId: string; body: GuidedAnswerUpsert }) =>
      upsertGuidedAnswer(assessmentId, args.questionId, args.body),
    onSuccess: (data) => {
      if (!currentOrganizationId) return;
      qc.setQueryData(
        queryKeys.guidedSession(currentOrganizationId, assessmentId),
        data,
      );
    },
  });
}
