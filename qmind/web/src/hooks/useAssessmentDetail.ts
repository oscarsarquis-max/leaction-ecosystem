import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { AssessmentCreate, AssessmentOut } from "@qmind/api-client";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  getQmindClient,
  withTenantGeneration,
  StaleTenantResponseError,
  QmindApiError,
} from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import { newIdempotencyKey } from "@/lib/idempotency";
import { buildScopeItem, isUuid, type ScopeKind } from "@/lib/validation";
import {
  ensureAssessmentScopes,
  listOrgMembers,
  listScopeOptions,
} from "@/api/scopeTeamApi";

type AssessmentType =
  | NonNullable<AssessmentCreate["type"]>
  | "external_audit"
  | "certification_prep";
type ScopeItem = NonNullable<AssessmentCreate["scope"]>[number];

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

function isConflictOrStale(error: unknown): boolean {
  return error instanceof QmindApiError && (error.status === 409 || error.status === 422);
}

export function useAssessment(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();

  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessment(currentOrganizationId, assessmentId)
        : ["org", "none", "assessment"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async (): Promise<AssessmentOut> => {
      const orgId = currentOrganizationId!;
      const id = assessmentId!;
      const client = getQmindClient();
      const data = await guardTenant(async () => {
        const res = await client.api.getAssessment({
          path: { assessment_id: id },
        });
        return res.data!;
      });
      if (data.organization_id !== orgId) {
        throw new QmindApiError(404, {
          code: "not_found",
          message: "Assessment not in current organization",
          correlation_id: "",
        });
      }
      return data;
    },
  });
}

export type AssessmentScopeRow = {
  id: string;
  assessment_id: string;
  org_process_id: string | null;
  requirement_id: string | null;
  created_at: string;
  label?: string | null;
};

export function useAssessmentScopes(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();

  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentScopes(currentOrganizationId, assessmentId)
        : ["org", "none", "scopes"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async (): Promise<AssessmentScopeRow[]> => {
      const client = getQmindClient();
      return guardTenant(async () => {
        // raw: preserva `label` humano (cliente OpenAPI gerado ainda não tipa o campo).
        const res = await client.raw.get({
          url: `/api/v1/assessments/${assessmentId}/scopes`,
          security: [{ scheme: "bearer", type: "http" }],
        });
        return (res.data as AssessmentScopeRow[]) ?? [];
      });
    },
  });
}

export function useAssessmentTeam(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();

  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentTeam(currentOrganizationId, assessmentId)
        : ["org", "none", "team"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.listAssessmentTeam({
          path: { assessment_id: assessmentId! },
        });
        return res.data ?? [];
      });
    },
  });
}

async function invalidateAssessmentBundle(
  qc: ReturnType<typeof useQueryClient>,
  organizationId: string,
  assessmentId: string,
) {
  await Promise.all([
    qc.invalidateQueries({
      queryKey: queryKeys.assessment(organizationId, assessmentId),
    }),
    qc.invalidateQueries({
      queryKey: queryKeys.assessments(organizationId),
    }),
    qc.invalidateQueries({
      queryKey: queryKeys.assessmentScopes(organizationId, assessmentId),
    }),
    qc.invalidateQueries({
      queryKey: queryKeys.assessmentTeam(organizationId, assessmentId),
    }),
  ]);
}

export type CreateAssessmentInput = {
  assessment_model_id: string;
  standard_version_id: string;
  type: AssessmentType;
  requirement_id?: string;
  org_process_id?: string;
};

export function validateCreateAssessmentInput(
  input: CreateAssessmentInput,
): string | null {
  if (!isUuid(input.assessment_model_id)) {
    return "O ID do modelo de avaliação deve ser um UUID";
  }
  if (!isUuid(input.standard_version_id)) {
    return "O ID da versão da norma deve ser um UUID";
  }
  if (input.requirement_id && input.org_process_id) {
    return "Informe exatamente um: requisito ou processo";
  }
  if (input.requirement_id && !isUuid(input.requirement_id)) {
    return "O ID do requisito deve ser um UUID";
  }
  if (input.org_process_id && !isUuid(input.org_process_id)) {
    return "O ID do processo deve ser um UUID";
  }
  return null;
}

export function useCreateAssessment() {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (input: CreateAssessmentInput) => {
      if (!currentOrganizationId) throw new Error("Nenhuma organização selecionada");
      const validationError = validateCreateAssessmentInput(input);
      if (validationError) {
        throw new QmindApiError(422, {
          code: "validation_error",
          message: validationError,
          correlation_id: "",
        });
      }
      // Tenant authority is X-Organization-Id from the active client — never body.
      const scope: ScopeItem[] = [];
      if (input.requirement_id) {
        scope.push({ requirement_id: input.requirement_id });
      } else if (input.org_process_id) {
        scope.push({ org_process_id: input.org_process_id });
      }
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.createAssessment({
          body: {
            assessment_model_id: input.assessment_model_id,
            standard_version_id: input.standard_version_id,
            // Novos tipos (external_audit / certification_prep) até regenerar OpenAPI.
            type: input.type as AssessmentCreate["type"],
            scope,
          },
          headers: { "Idempotency-Key": newIdempotencyKey("assess-create") },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessments(currentOrganizationId),
      });
    },
  });
}

export function useScopeOptions(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentScopeOptions(currentOrganizationId, assessmentId)
        : ["org", "none", "scope-options"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: () => listScopeOptions(assessmentId!),
  });
}

export function useOrgMembers() {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey: currentOrganizationId
      ? queryKeys.orgMembers(currentOrganizationId)
      : ["org", "none", "members"],
    enabled: !!currentOrganizationId,
    queryFn: () => listOrgMembers(),
  });
}

export function useEnsureScopes(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => ensureAssessmentScopes(assessmentId),
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentScopes(currentOrganizationId, assessmentId),
      });
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentScopeOptions(
          currentOrganizationId,
          assessmentId,
        ),
      });
    },
  });
}

export function useAddScope(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { kind: ScopeKind; value: string }) => {
      const item = buildScopeItem(payload.kind, payload.value);
      if (!item) {
        throw new QmindApiError(422, {
          code: "validation_error",
          message: "Não foi possível identificar o item de escopo. Escolha uma opção da lista.",
          correlation_id: "",
        });
      }
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.addAssessmentScope({
          path: { assessment_id: assessmentId },
          body: item,
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentScopes(currentOrganizationId, assessmentId),
      });
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentScopeOptions(
          currentOrganizationId,
          assessmentId,
        ),
      });
    },
    onError: async (error) => {
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      if (error instanceof StaleTenantResponseError) return;
      await invalidateAssessmentBundle(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useDeleteScope(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (scopeId: string) => {
      if (!isUuid(scopeId)) {
        throw new QmindApiError(422, {
          code: "validation_error",
          message: "scope_id must be a UUID",
          correlation_id: "",
        });
      }
      const client = getQmindClient();
      return guardTenant(async () => {
        await client.api.deleteAssessmentScope({
          path: { assessment_id: assessmentId, scope_id: scopeId },
        });
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentScopes(currentOrganizationId, assessmentId),
      });
    },
    onError: async (error) => {
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateAssessmentBundle(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useAddTeamMember(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (payload: { membership_id: string; team_role?: string }) => {
      if (!isUuid(payload.membership_id)) {
        throw new QmindApiError(422, {
          code: "validation_error",
          message: "membership_id must be a UUID",
          correlation_id: "",
        });
      }
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.addAssessmentTeamMember({
          path: { assessment_id: assessmentId },
          body: {
            membership_id: payload.membership_id.trim(),
            team_role: payload.team_role?.trim() || null,
          },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentTeam(currentOrganizationId, assessmentId),
      });
    },
    onError: async (error) => {
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateAssessmentBundle(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useRemoveTeamMember(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async (memberId: string) => {
      if (!isUuid(memberId)) {
        throw new QmindApiError(422, {
          code: "validation_error",
          message: "member_id must be a UUID",
          correlation_id: "",
        });
      }
      const client = getQmindClient();
      return guardTenant(async () => {
        await client.api.removeAssessmentTeamMember({
          path: { assessment_id: assessmentId, member_id: memberId },
        });
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentTeam(currentOrganizationId, assessmentId),
      });
    },
    onError: async (error) => {
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateAssessmentBundle(qc, currentOrganizationId, assessmentId);
    },
  });
}

/**
 * Plan transition — no optimistic cache writes.
 * Success invalidates assessment caches for the active organization only.
 */
export function usePlanAssessment(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.planAssessment({
          path: { assessment_id: assessmentId },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateAssessmentBundle(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      // Conflict / concurrency / guard: reload authoritative resource
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateAssessmentBundle(qc, currentOrganizationId, assessmentId);
    },
  });
}
