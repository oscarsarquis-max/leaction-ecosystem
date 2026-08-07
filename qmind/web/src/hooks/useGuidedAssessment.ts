import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { queryKeys } from "@/api/queryKeys";
import {
  completeGuidedAnswerEvidenceLink,
  fetchGuidedCatalog,
  fetchGuidedSessionState,
  isGuidedApiError,
  isGuidedUnavailableInPhase,
  linkGuidedAnswerEvidence,
  patchGuidedPosition,
  patchGuidedSession,
  unlinkGuidedAnswerEvidence,
  upsertGuidedAnswer,
  type GuidedSessionFetch,
} from "@/api/guidedApi";
import type {
  GuidedAnswerUpsert,
  GuidedContext,
  GuidedSession,
  GuidedStep,
} from "@/api/guidedTypes";

export function useGuidedCatalog(version?: string | null) {
  return useQuery({
    queryKey: queryKeys.guidedCatalog(version),
    queryFn: () => fetchGuidedCatalog(version),
    staleTime: 5 * 60_000,
  });
}

/**
 * Sessão guided com estado explícito:
 * - data = sessão quando existe
 * - unavailableInPhase = 409 guided_unavailable_in_phase (não é erro de UI)
 * - isError = falha real (rede, 403, etc.)
 */
export function useGuidedSession(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  const q = useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.guidedSession(currentOrganizationId, assessmentId)
        : ["org", "none", "guided"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: () => fetchGuidedSessionState(assessmentId!),
    retry: (count, err) => {
      if (isGuidedUnavailableInPhase(err)) return false;
      if (isGuidedApiError(err) && err.status === 404) return false;
      return count < 1;
    },
  });

  const fetch = q.data as GuidedSessionFetch | undefined;
  const session: GuidedSession | undefined =
    fetch?.kind === "session" ? fetch.session : undefined;
  const unavailableInPhase =
    fetch?.kind === "unavailable_in_phase"
      ? { message: fetch.message }
      : undefined;

  return {
    ...q,
    data: session,
    unavailableInPhase,
    /** true quando não há sessão porque a fase não cria/abre roteiro */
    isUnavailableInPhase: !!unavailableInPhase,
  };
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
      const wrapped: GuidedSessionFetch = { kind: "session", session: data };
      qc.setQueryData(
        queryKeys.guidedSession(currentOrganizationId, assessmentId),
        wrapped,
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
      const wrapped: GuidedSessionFetch = { kind: "session", session: data };
      qc.setQueryData(
        queryKeys.guidedSession(currentOrganizationId, assessmentId),
        wrapped,
      );
    },
  });
}

function useSetGuidedSession(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return (data: GuidedSession) => {
    if (!currentOrganizationId) return;
    const wrapped: GuidedSessionFetch = { kind: "session", session: data };
    qc.setQueryData(
      queryKeys.guidedSession(currentOrganizationId, assessmentId),
      wrapped,
    );
  };
}

export function useUpsertGuidedAnswer(assessmentId: string) {
  const setSession = useSetGuidedSession(assessmentId);
  return useMutation({
    mutationFn: (args: { questionId: string; body: GuidedAnswerUpsert }) =>
      upsertGuidedAnswer(assessmentId, args.questionId, args.body),
    onSuccess: setSession,
  });
}

export function useLinkGuidedEvidence(assessmentId: string) {
  const setSession = useSetGuidedSession(assessmentId);
  return useMutation({
    mutationFn: (args: { questionId: string; evidenceId: string }) =>
      linkGuidedAnswerEvidence(assessmentId, args.questionId, args.evidenceId),
    onSuccess: setSession,
  });
}

export function useUnlinkGuidedEvidence(assessmentId: string) {
  const setSession = useSetGuidedSession(assessmentId);
  return useMutation({
    mutationFn: (args: { questionId: string; evidenceId: string }) =>
      unlinkGuidedAnswerEvidence(
        assessmentId,
        args.questionId,
        args.evidenceId,
      ),
    onSuccess: setSession,
  });
}

export function useCompleteGuidedEvidence(assessmentId: string) {
  const setSession = useSetGuidedSession(assessmentId);
  return useMutation({
    mutationFn: (args: { questionId: string; evidenceId: string }) =>
      completeGuidedAnswerEvidenceLink(
        assessmentId,
        args.questionId,
        args.evidenceId,
      ),
    onSuccess: setSession,
  });
}

export function useRefreshGuidedSession(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return async () => {
    if (!currentOrganizationId) return;
    await qc.invalidateQueries({
      queryKey: queryKeys.guidedSession(currentOrganizationId, assessmentId),
    });
  };
}
