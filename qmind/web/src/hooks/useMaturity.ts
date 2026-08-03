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

export type Applicability = "applicable" | "not_applicable" | "insufficient_info";

export type ScoreDraft = {
  criterion_id: string;
  applicability: Applicability;
  level: number | null;
  na_rationale: string | null;
  rationale: string | null;
  evidence_ids: string[];
};

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

function isConflictOrStale(error: unknown): boolean {
  return error instanceof QmindApiError && (error.status === 409 || error.status === 422);
}

async function invalidateMaturity(
  qc: ReturnType<typeof useQueryClient>,
  organizationId: string,
  assessmentId: string,
  packageId?: string,
) {
  const jobs = [
    qc.invalidateQueries({
      queryKey: queryKeys.assessmentMaturity(organizationId, assessmentId),
    }),
  ];
  if (packageId) {
    jobs.push(
      qc.invalidateQueries({
        queryKey: queryKeys.maturityPackage(organizationId, packageId),
      }),
    );
  }
  await Promise.all(jobs);
}

export function useMaturityPackages(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentMaturity(currentOrganizationId, assessmentId)
        : ["org", "none", "maturity"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.listMaturityAssessments({
          query: { assessment_id: assessmentId! },
        });
        return res.data ?? [];
      });
    },
  });
}

/** Create-or-open current draft/in_review package. */
export function useOpenMaturityPackage(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.createMaturityAssessment({
          body: { assessment_id: assessmentId },
          headers: { "Idempotency-Key": newIdempotencyKey("maturity-open") },
        });
        return res.data!;
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      await invalidateMaturity(qc, currentOrganizationId, assessmentId, data.id);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateMaturity(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useUpsertMaturityScores(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { packageId: string; scores: ScoreDraft[] }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        // Never send global_score / dimension_scores — server authority only.
        const res = await client.api.upsertMaturityScores({
          path: { package_id: payload.packageId },
          body: {
            scores: payload.scores.map((s) => ({
              criterion_id: s.criterion_id,
              applicability: s.applicability,
              level: s.level,
              na_rationale: s.na_rationale,
              rationale: s.rationale,
              evidence_ids: s.evidence_ids,
            })),
          },
        });
        return res.data!;
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      await invalidateMaturity(qc, currentOrganizationId, assessmentId, data.id);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateMaturity(qc, currentOrganizationId, assessmentId);
    },
  });
}

type MaturityTransition =
  | { kind: "submit" }
  | { kind: "approve" }
  | { kind: "reject"; reason: string }
  | { kind: "rework" }
  | { kind: "discard"; reason?: string }
  | { kind: "supersede"; reason: string };

export function useMaturityTransition(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { packageId: string; transition: MaturityTransition }) => {
      const client = getQmindClient();
      const id = payload.packageId;
      return guardTenant(async () => {
        switch (payload.transition.kind) {
          case "submit":
            return (
              await client.api.submitMaturityAssessment({ path: { package_id: id } })
            ).data!;
          case "approve":
            return (
              await client.api.approveMaturityAssessment({ path: { package_id: id } })
            ).data!;
          case "reject":
            return (
              await client.api.rejectMaturityAssessment({
                path: { package_id: id },
                body: { reason: payload.transition.reason },
              })
            ).data!;
          case "rework":
            return (
              await client.api.reworkMaturityAssessment({ path: { package_id: id } })
            ).data!;
          case "discard":
            return (
              await client.api.discardMaturityAssessment({
                path: { package_id: id },
                body: { reason: payload.transition.reason ?? null },
              })
            ).data!;
          case "supersede":
            return (
              await client.api.supersedeMaturityAssessment({
                path: { package_id: id },
                body: { reason: payload.transition.reason },
              })
            ).data!;
        }
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      await invalidateMaturity(
        qc,
        currentOrganizationId,
        assessmentId,
        data.package?.id ?? data.new_package_id ?? undefined,
      );
      await invalidateMaturity(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateMaturity(qc, currentOrganizationId, assessmentId);
    },
  });
}
