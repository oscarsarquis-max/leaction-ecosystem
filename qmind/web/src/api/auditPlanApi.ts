import {
  getQmindClient,
  withTenantGeneration,
  QmindApiError,
} from "@/api/qmindApi";
import type { AuditPlan, AuditPlanPatch } from "@/api/auditPlanTypes";

export async function getOrCreateAuditPlan(
  assessmentId: string,
): Promise<AuditPlan> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.get({
      url: `/api/v1/assessments/${assessmentId}/audit-plan`,
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as AuditPlan;
  });
}

export async function patchAuditPlan(
  assessmentId: string,
  body: AuditPlanPatch,
): Promise<AuditPlan> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.patch({
      url: `/api/v1/assessments/${assessmentId}/audit-plan`,
      body,
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as AuditPlan;
  });
}

export async function markAuditPlanReady(
  assessmentId: string,
  expectedUpdatedAt?: string,
): Promise<AuditPlan> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/assessments/${assessmentId}/audit-plan/ready`,
      body: expectedUpdatedAt
        ? { expected_updated_at: expectedUpdatedAt }
        : {},
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as AuditPlan;
  });
}

export async function refreshAuditPlanFromPreparation(
  assessmentId: string,
  confirmOverwritePreparation = false,
): Promise<AuditPlan> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/assessments/${assessmentId}/audit-plan/refresh-from-preparation`,
      body: { confirm_overwrite_preparation: confirmOverwritePreparation },
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as AuditPlan;
  });
}

export function isAuditPlanApiError(err: unknown): err is QmindApiError {
  return err instanceof QmindApiError;
}
