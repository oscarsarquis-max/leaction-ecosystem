import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  getQmindClient,
  withTenantGeneration,
  StaleTenantResponseError,
  QmindApiError,
} from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import {
  uploadEvidenceFile,
  openEvidencePreview,
  type EvidenceLinkTarget,
  type EvidenceUploadPhase,
} from "@/lib/evidenceUpload";

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

function isConflictOrStale(error: unknown): boolean {
  return error instanceof QmindApiError && (error.status === 409 || error.status === 422);
}

async function invalidateFieldBundle(
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
      queryKey: queryKeys.assessmentInterviews(organizationId, assessmentId),
    }),
    qc.invalidateQueries({
      queryKey: queryKeys.assessmentEvidences(organizationId, assessmentId),
    }),
    qc.invalidateQueries({
      queryKey: queryKeys.assessmentQuestions(organizationId, assessmentId),
    }),
  ]);
}

export function useStartAssessment(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.startAssessment({
          path: { assessment_id: assessmentId },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateFieldBundle(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateFieldBundle(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useAssessmentQuestions(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentQuestions(currentOrganizationId, assessmentId)
        : ["org", "none", "questions"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.listAssessmentQuestions({
          path: { assessment_id: assessmentId! },
        });
        return res.data ?? [];
      });
    },
  });
}

export function useAssessmentInterviews(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentInterviews(currentOrganizationId, assessmentId)
        : ["org", "none", "interviews"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.listAssessmentInterviews({
          path: { assessment_id: assessmentId! },
        });
        return res.data ?? [];
      });
    },
  });
}

export function useInterviewAnswers(interviewId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && interviewId
        ? queryKeys.interviewAnswers(currentOrganizationId, interviewId)
        : ["org", "none", "answers"],
    enabled: !!currentOrganizationId && !!interviewId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.listInterviewAnswers({
          path: { interview_id: interviewId! },
        });
        return res.data ?? [];
      });
    },
  });
}

export function useAssessmentEvidences(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentEvidences(currentOrganizationId, assessmentId)
        : ["org", "none", "evidences"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.listAssessmentEvidences({
          path: { assessment_id: assessmentId! },
        });
        return res.data ?? [];
      });
    },
  });
}

export type CreateInterviewInput = {
  mode?: "onsite" | "remote" | "hybrid";
  title?: string;
  objective?: string;
  process_name?: string;
  org_contact_name?: string;
  scheduled_at?: string;
  duration_minutes?: number;
  location?: string;
  remote_link?: string;
  preparation?: string;
  outside_period_justification?: string;
};

export function useCreateInterview(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateInterviewInput | "onsite" | "remote" | "hybrid") => {
      const body: CreateInterviewInput =
        typeof input === "string" ? { mode: input } : input;
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.createInterview({
          path: { assessment_id: assessmentId },
          body: {
            mode: body.mode ?? "onsite",
            title: body.title,
            objective: body.objective,
            process_name: body.process_name,
            org_contact_name: body.org_contact_name,
            scheduled_at: body.scheduled_at,
            duration_minutes: body.duration_minutes,
            location: body.location,
            remote_link: body.remote_link,
            preparation: body.preparation,
            outside_period_justification: body.outside_period_justification,
          },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await Promise.all([
        qc.invalidateQueries({
          queryKey: queryKeys.assessmentInterviews(currentOrganizationId, assessmentId),
        }),
        qc.invalidateQueries({
          queryKey: queryKeys.auditPlanSchedule(currentOrganizationId, assessmentId),
        }),
      ]);
    },
  });
}

export function useStartInterviewMutation(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (interviewId: string) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.startInterview({
          path: { interview_id: interviewId },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateFieldBundle(qc, currentOrganizationId, assessmentId);
      await qc.invalidateQueries({
        queryKey: queryKeys.auditPlanSchedule(currentOrganizationId, assessmentId),
      });
    },
  });
}

export function useCancelInterviewMutation(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { interviewId: string; reason: string }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        if (args.reason.trim()) {
          await client.api.updateInterview({
            path: { interview_id: args.interviewId },
            body: {
              preparation: `Cancelamento: ${args.reason.trim()}`,
            },
          });
        }
        const res = await client.api.cancelInterview({
          path: { interview_id: args.interviewId },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateFieldBundle(qc, currentOrganizationId, assessmentId);
      await qc.invalidateQueries({
        queryKey: queryKeys.auditPlanSchedule(currentOrganizationId, assessmentId),
      });
    },
  });
}

export function useCreateAnswer(assessmentId: string, interviewId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { body: string; question_id?: string }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.createAnswer({
          path: { interview_id: interviewId },
          body: {
            body: payload.body,
            question_id: payload.question_id || null,
          },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.interviewAnswers(currentOrganizationId, interviewId),
      });
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentInterviews(currentOrganizationId, assessmentId),
      });
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateFieldBundle(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useCompleteInterview(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (interviewId: string) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.completeInterview({
          path: { interview_id: interviewId },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateFieldBundle(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useUploadEvidence(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      file: File;
      link?: EvidenceLinkTarget;
      onPhase?: (phase: EvidenceUploadPhase) => void;
    }) => {
      return uploadEvidenceFile({
        assessmentId,
        file: payload.file,
        link: payload.link,
        onPhase: payload.onPhase,
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentEvidences(currentOrganizationId, assessmentId),
      });
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentEvidences(currentOrganizationId, assessmentId),
      });
    },
  });
}

export function useSecurityPassEvidence(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (evidenceId: string) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.securityPassEvidence({
          path: { evidence_id: evidenceId },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentEvidences(currentOrganizationId, assessmentId),
      });
    },
  });
}

export function useSecurityFailEvidence(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (evidenceId: string) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.securityFailEvidence({
          path: { evidence_id: evidenceId },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentEvidences(currentOrganizationId, assessmentId),
      });
    },
  });
}

export function useAbandonEvidence(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (evidenceId: string) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.abandonEvidenceUpload({
          path: { evidence_id: evidenceId },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentEvidences(currentOrganizationId, assessmentId),
      });
    },
  });
}

export function usePreviewEvidence() {
  return useMutation({
    mutationFn: async (evidenceId: string) => openEvidencePreview(evidenceId),
  });
}

/** Vincula evidência já existente (ex.: antecipada) a entrevista/resposta sem novo upload. */
export function useLinkEvidence(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      evidenceId: string;
      target_type: EvidenceLinkTarget["target_type"];
      target_id: string;
    }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.createEvidenceLink({
          path: { evidence_id: payload.evidenceId },
          body: {
            target_type: payload.target_type,
            target_id: payload.target_id,
          },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await qc.invalidateQueries({
        queryKey: queryKeys.assessmentEvidences(currentOrganizationId, assessmentId),
      });
    },
  });
}
