import { getQmindClient, withTenantGeneration } from "@/api/qmindApi";
import type {
  AuditPlanSchedule,
  PlannedInterviewCreate,
  ScheduleMeetingCreate,
  ScheduleMilestoneCreate,
} from "@/api/auditPlanScheduleTypes";

export async function getAuditPlanSchedule(
  assessmentId: string,
): Promise<AuditPlanSchedule> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.get({
      url: `/api/v1/assessments/${assessmentId}/audit-plan/schedule`,
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as AuditPlanSchedule;
  });
}

export async function createAuditPlanMeeting(
  assessmentId: string,
  body: ScheduleMeetingCreate,
): Promise<AuditPlanSchedule> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/assessments/${assessmentId}/audit-plan/schedule/meetings`,
      body,
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as AuditPlanSchedule;
  });
}

export async function createAuditPlanMilestone(
  assessmentId: string,
  body: ScheduleMilestoneCreate,
): Promise<AuditPlanSchedule> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/assessments/${assessmentId}/audit-plan/schedule/milestones`,
      body,
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as AuditPlanSchedule;
  });
}

export async function createPlannedInterview(
  assessmentId: string,
  body: PlannedInterviewCreate,
): Promise<unknown> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/assessments/${assessmentId}/interviews`,
      body,
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data;
  });
}

export async function startInterview(interviewId: string): Promise<unknown> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: `/api/v1/interviews/${interviewId}/start`,
      body: {},
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data;
  });
}
