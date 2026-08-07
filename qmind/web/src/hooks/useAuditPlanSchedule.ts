import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import { queryKeys } from "@/api/queryKeys";
import {
  createAuditPlanMeeting,
  createAuditPlanMilestone,
  createPlannedInterview,
  getAuditPlanSchedule,
  startInterview,
} from "@/api/auditPlanScheduleApi";
import type {
  PlannedInterviewCreate,
  ScheduleMeetingCreate,
  ScheduleMilestoneCreate,
} from "@/api/auditPlanScheduleTypes";
import {
  isAuditPlanApiError,
  performOpeningMeeting,
  waiveOpeningMeeting,
} from "@/api/auditPlanApi";

export function useAuditPlanSchedule(assessmentId: string | undefined) {
  const { currentOrganizationId } = useOrganization();
  return useQuery({
    queryKey:
      currentOrganizationId && assessmentId
        ? queryKeys.auditPlanSchedule(currentOrganizationId, assessmentId)
        : ["org", "none", "audit-plan-schedule"],
    enabled: !!currentOrganizationId && !!assessmentId,
    queryFn: () => getAuditPlanSchedule(assessmentId!),
    retry: (count, err) => {
      if (isAuditPlanApiError(err) && (err.status === 404 || err.status === 403))
        return false;
      return count < 1;
    },
  });
}

function useInvalidateSchedule(assessmentId: string) {
  const { currentOrganizationId } = useOrganization();
  const qc = useQueryClient();
  return () => {
    if (!currentOrganizationId) return;
    void qc.invalidateQueries({
      queryKey: queryKeys.auditPlanSchedule(currentOrganizationId, assessmentId),
    });
    void qc.invalidateQueries({
      queryKey: queryKeys.auditPlan(currentOrganizationId, assessmentId),
    });
    void qc.invalidateQueries({
      queryKey: queryKeys.assessmentInterviews(currentOrganizationId, assessmentId),
    });
  };
}

export function useCreateScheduleMeeting(assessmentId: string) {
  const invalidate = useInvalidateSchedule(assessmentId);
  return useMutation({
    mutationFn: (body: ScheduleMeetingCreate) =>
      createAuditPlanMeeting(assessmentId, body),
    onSuccess: invalidate,
  });
}

export function useCreateScheduleMilestone(assessmentId: string) {
  const invalidate = useInvalidateSchedule(assessmentId);
  return useMutation({
    mutationFn: (body: ScheduleMilestoneCreate) =>
      createAuditPlanMilestone(assessmentId, body),
    onSuccess: invalidate,
  });
}

export function useCreatePlannedInterview(assessmentId: string) {
  const invalidate = useInvalidateSchedule(assessmentId);
  return useMutation({
    mutationFn: (body: PlannedInterviewCreate) =>
      createPlannedInterview(assessmentId, body),
    onSuccess: invalidate,
  });
}

export function useStartInterview(assessmentId: string) {
  const invalidate = useInvalidateSchedule(assessmentId);
  return useMutation({
    mutationFn: (interviewId: string) => startInterview(interviewId),
    onSuccess: invalidate,
  });
}

export function usePerformOpeningMeeting(assessmentId: string) {
  const invalidate = useInvalidateSchedule(assessmentId);
  return useMutation({
    mutationFn: (args: {
      eventId: string;
      observations?: string;
      adjustments?: string;
      pendings?: string;
      actual_starts_at?: string;
    }) =>
      performOpeningMeeting(assessmentId, args.eventId, {
        observations: args.observations,
        adjustments: args.adjustments,
        pendings: args.pendings,
        actual_starts_at: args.actual_starts_at,
      }),
    onSuccess: invalidate,
  });
}

export function useWaiveOpeningMeeting(assessmentId: string) {
  const invalidate = useInvalidateSchedule(assessmentId);
  return useMutation({
    mutationFn: (args: { eventId: string; waiverReason: string }) =>
      waiveOpeningMeeting(assessmentId, args.eventId, args.waiverReason),
    onSuccess: invalidate,
  });
}
