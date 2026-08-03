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

export type FindingType =
  | "conformity"
  | "nonconformity"
  | "opportunity"
  | "observation";

export type FindingDraftInput = {
  finding_type: FindingType;
  title: string;
  body: string;
  severity?: string | null;
  requirement_ids: string[];
  evidence_ids: string[];
  insufficient_evidence: boolean;
  insufficient_evidence_rationale?: string | null;
};

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

function isConflictOrStale(error: unknown): boolean {
  return error instanceof QmindApiError && (error.status === 409 || error.status === 422);
}

async function invalidateFindings(
  qc: ReturnType<typeof useQueryClient>,
  organizationId: string,
  assessmentId: string,
  findingId?: string,
) {
  const jobs = [
    qc.invalidateQueries({
      queryKey: queryKeys.assessmentFindings(organizationId, assessmentId),
    }),
  ];
  if (findingId) {
    jobs.push(
      qc.invalidateQueries({
        queryKey: queryKeys.finding(organizationId, findingId),
      }),
    );
  }
  await Promise.all(jobs);
}

export function useAssessmentFindings(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentFindings(currentOrganizationId, assessmentId)
        : ["org", "none", "findings"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.listFindings({
          query: { assessment_id: assessmentId! },
        });
        return res.data ?? [];
      });
    },
  });
}

export function useCreateFinding(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: FindingDraftInput) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.createFinding({
          body: {
            assessment_id: assessmentId,
            finding_type: input.finding_type,
            title: input.title,
            body: input.body,
            severity: input.severity ?? null,
            requirement_ids: input.requirement_ids,
            evidence_ids: input.evidence_ids,
            insufficient_evidence: input.insufficient_evidence,
            insufficient_evidence_rationale:
              input.insufficient_evidence_rationale ?? null,
          },
          headers: { "Idempotency-Key": newIdempotencyKey("finding-create") },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateFindings(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateFindings(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useUpdateFinding(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { findingId: string; input: FindingDraftInput }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.updateFinding({
          path: { finding_id: payload.findingId },
          body: {
            finding_type: payload.input.finding_type,
            title: payload.input.title,
            body: payload.input.body,
            severity: payload.input.severity ?? null,
            requirement_ids: payload.input.requirement_ids,
            evidence_ids: payload.input.evidence_ids,
            insufficient_evidence: payload.input.insufficient_evidence,
            insufficient_evidence_rationale:
              payload.input.insufficient_evidence_rationale ?? null,
          },
        });
        return res.data!;
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      await invalidateFindings(qc, currentOrganizationId, assessmentId, data.id);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateFindings(qc, currentOrganizationId, assessmentId);
    },
  });
}

type Transition =
  | { kind: "submit" }
  | { kind: "approve" }
  | { kind: "reject"; reason: string }
  | { kind: "rework" }
  | { kind: "discard"; reason?: string }
  | { kind: "withdraw"; reason: string };

export function useFindingTransition(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { findingId: string; transition: Transition }) => {
      const client = getQmindClient();
      const id = payload.findingId;
      return guardTenant(async () => {
        switch (payload.transition.kind) {
          case "submit":
            return (await client.api.submitFinding({ path: { finding_id: id } })).data!;
          case "approve":
            return (await client.api.approveFinding({ path: { finding_id: id } })).data!;
          case "reject":
            return (
              await client.api.rejectFinding({
                path: { finding_id: id },
                body: { reason: payload.transition.reason },
              })
            ).data!;
          case "rework":
            return (await client.api.reworkFinding({ path: { finding_id: id } })).data!;
          case "discard":
            return (
              await client.api.discardFinding({
                path: { finding_id: id },
                body: { reason: payload.transition.reason ?? null },
              })
            ).data!;
          case "withdraw":
            return (
              await client.api.withdrawFinding({
                path: { finding_id: id },
                body: { reason: payload.transition.reason },
              })
            ).data!;
        }
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      const fid = data.finding?.id ?? data.preserved_finding_id ?? undefined;
      await invalidateFindings(
        qc,
        currentOrganizationId,
        assessmentId,
        typeof fid === "string" ? fid : undefined,
      );
      // Rework from withdrawn creates a new draft — refresh list covers it.
      await invalidateFindings(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateFindings(qc, currentOrganizationId, assessmentId);
    },
  });
}
