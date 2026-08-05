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
  return error instanceof QmindApiError && (error.status === 409 || error.status === 422);
}

async function invalidateReports(
  qc: ReturnType<typeof useQueryClient>,
  organizationId: string,
  assessmentId: string,
  reportId?: string,
) {
  const jobs = [
    qc.invalidateQueries({
      queryKey: queryKeys.assessmentReports(organizationId, assessmentId),
    }),
    qc.invalidateQueries({
      queryKey: queryKeys.assessment(organizationId, assessmentId),
    }),
    qc.invalidateQueries({
      queryKey: queryKeys.assessments(organizationId),
    }),
  ];
  if (reportId) {
    jobs.push(
      qc.invalidateQueries({
        queryKey: queryKeys.report(organizationId, reportId),
      }),
    );
  }
  await Promise.all(jobs);
}

export function useAssessmentReports(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.assessmentReports(currentOrganizationId, assessmentId)
        : ["org", "none", "reports"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.listReports({
          query: { assessment_id: assessmentId! },
        });
        return res.data ?? [];
      });
    },
  });
}

export function useCreateReport(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input?: {
      include_maturity?: boolean;
      include_action_plan?: boolean;
    }) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.createReport({
          body: {
            assessment_id: assessmentId,
            include_maturity: input?.include_maturity ?? true,
            include_action_plan: input?.include_action_plan ?? true,
          },
          headers: { "Idempotency-Key": newIdempotencyKey("report") },
        });
        return res.data!;
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId, data.id);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useRefreshReportSnapshot(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reportId: string) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.refreshReportSnapshot({
          path: { report_id: reportId },
        });
        return res.data!;
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId, data.id);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId);
    },
  });
}

type ReportTransition =
  | { kind: "submit" }
  | { kind: "request_changes"; reason: string }
  | { kind: "discard"; reason?: string | null }
  | { kind: "publish" }
  | { kind: "archive" };

export function useReportTransition(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { reportId: string; transition: ReportTransition }) => {
      const client = getQmindClient();
      const path = { report_id: payload.reportId };
      return guardTenant(async () => {
        switch (payload.transition.kind) {
          case "submit":
            return (await client.api.submitReport({ path })).data!;
          case "request_changes":
            return (
              await client.api.requestReportChanges({
                path,
                body: { reason: payload.transition.reason },
              })
            ).data!;
          case "discard":
            return (
              await client.api.discardReport({
                path,
                body: { reason: payload.transition.reason ?? null },
              })
            ).data!;
          case "publish":
            return (await client.api.publishReport({ path })).data!;
          case "archive":
            return (await client.api.archiveReport({ path })).data!;
        }
      });
    },
    onSuccess: async (data) => {
      if (!currentOrganizationId) return;
      await invalidateReports(
        qc,
        currentOrganizationId,
        assessmentId,
        data.report?.id,
      );
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId);
    },
  });
}

export type ReportPdfJob = {
  id: string;
  organization_id: string;
  job_type: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled" | string;
  idempotency_key: string;
  input_ref?: Record<string, unknown>;
  attempt_count?: number;
  max_attempts?: number;
  error_code?: string | null;
  error_safe_message?: string | null;
  output_ref?: Record<string, unknown>;
  created_at?: string;
};

export function useExportReportPdf(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reportId: string) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.exportReportPdf({
          path: { report_id: reportId },
          headers: { "Idempotency-Key": newIdempotencyKey("report-pdf") },
        });
        return res.data! as ReportPdfJob;
      });
    },
    onSuccess: async (_data, reportId) => {
      if (!currentOrganizationId) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId, reportId);
    },
  });
}

export async function fetchReportPdfJob(jobId: string): Promise<ReportPdfJob> {
  const client = getQmindClient();
  return guardTenant(async () => {
    const res = await client.raw.get({
      url: `/api/v1/jobs/${jobId}`,
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as ReportPdfJob;
  });
}

export async function fetchReportPdfDownloadUrl(
  reportId: string,
): Promise<{ url: string; expires_in_seconds: number }> {
  const client = getQmindClient();
  return guardTenant(async () => {
    const res = await client.raw.get({
      url: `/api/v1/reports/${reportId}/export-pdf/download-url`,
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as { url: string; expires_in_seconds: number };
  });
}

export function useBeginAssessmentReport(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.beginAssessmentReport({
          path: { assessment_id: assessmentId },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useCloseAssessment(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (waiver_reason?: string | null) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.closeAssessment({
          path: { assessment_id: assessmentId },
          body: { waiver_reason: waiver_reason?.trim() || null },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId);
    },
  });
}

export function useReopenAssessment(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (reason: string) => {
      const client = getQmindClient();
      return guardTenant(async () => {
        const res = await client.api.reopenAssessment({
          path: { assessment_id: assessmentId },
          body: { reason },
        });
        return res.data!;
      });
    },
    onSuccess: async () => {
      if (!currentOrganizationId) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId);
    },
    onError: async (error) => {
      if (error instanceof StaleTenantResponseError) return;
      if (!currentOrganizationId || !isConflictOrStale(error)) return;
      await invalidateReports(qc, currentOrganizationId, assessmentId);
    },
  });
}
