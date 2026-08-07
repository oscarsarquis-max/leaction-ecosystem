import {
  getQmindClient,
  withTenantGeneration,
  QmindApiError,
} from "@/api/qmindApi";
import type { AuditPlan, AuditPlanPatch } from "@/api/auditPlanTypes";

export type ConcludePlanningResult = {
  plan: AuditPlan;
  transition: {
    from_status: string;
    to_status: string;
    event: string;
  };
  message?: string;
};

export type StartFieldResult = {
  transition: {
    from_status: string;
    to_status: string;
    event: string;
  };
  redirect_href: string;
  message?: string;
};

export type OpeningMeetingResult = {
  event_id: string;
  status: "completed" | "waived";
  message: string;
};

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

export async function concludeAuditPlanning(
  assessmentId: string,
  body?: { expected_updated_at?: string; mark_ready_if_needed?: boolean },
): Promise<ConcludePlanningResult> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/assessments/${assessmentId}/audit-plan/conclude-planning`,
      body: body ?? {},
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as ConcludePlanningResult;
  });
}

export async function startAuditFieldExecution(
  assessmentId: string,
): Promise<StartFieldResult> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/assessments/${assessmentId}/audit-plan/start-field`,
      body: {},
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as StartFieldResult;
  });
}

export async function performOpeningMeeting(
  assessmentId: string,
  eventId: string,
  body?: {
    actual_starts_at?: string;
    participant_membership_ids?: string[];
    observations?: string;
    adjustments?: string;
    pendings?: string;
  },
): Promise<OpeningMeetingResult> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/assessments/${assessmentId}/audit-plan/schedule/meetings/${eventId}/perform`,
      body: body ?? {},
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as OpeningMeetingResult;
  });
}

export async function waiveOpeningMeeting(
  assessmentId: string,
  eventId: string,
  waiverReason: string,
): Promise<OpeningMeetingResult> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/assessments/${assessmentId}/audit-plan/schedule/meetings/${eventId}/waive`,
      body: { waiver_reason: waiverReason },
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as OpeningMeetingResult;
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
