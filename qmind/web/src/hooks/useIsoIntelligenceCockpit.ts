import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { useOrganization } from "@/org/OrganizationProvider";
import {
  getQmindClient,
  withTenantGeneration,
  StaleTenantResponseError,
} from "@/api/qmindApi";
import { queryKeys } from "@/api/queryKeys";
import type {
  CockpitActivityPageOut,
  CockpitCasesPageOut,
  CockpitSummaryOut,
  MeasurementPosture,
  TargetPosture,
} from "@qmind/api-client";

async function guardTenant<T>(fn: () => Promise<T>): Promise<T> {
  return withTenantGeneration(fn);
}

export type CockpitCaseFilters = {
  priority_band?:
    | "immediate_attention"
    | "attention"
    | "follow_up"
    | "on_course"
    | "completed_or_observed";
  execution_posture?:
    | "insufficient_information"
    | "not_started"
    | "progressing"
    | "attention_required"
    | "stalled"
    | "awaiting_result_evaluation"
    | "result_observed";
  intelligence_freshness?: "current" | "stale" | "never_analyzed";
  measurement_posture?: MeasurementPosture;
  target_posture?: TargetPosture;
  signal_category?:
    | "flow"
    | "schedule"
    | "blocker"
    | "dependency"
    | "evidence"
    | "measurement"
    | "outcome";
  related_process?: string;
  search?: string;
  case_status?: Array<"open" | "analyzing" | "acting" | "reviewing" | "closed">;
  ready_for_review?: boolean;
  has_overdue_actions?: boolean;
  has_active_impediment?: boolean;
  limit?: number;
};

function filtersKey(filters: CockpitCaseFilters): Record<string, string | undefined> {
  return {
    priority_band: filters.priority_band,
    execution_posture: filters.execution_posture,
    intelligence_freshness: filters.intelligence_freshness,
    measurement_posture: filters.measurement_posture,
    target_posture: filters.target_posture,
    signal_category: filters.signal_category,
    related_process: filters.related_process,
    search: filters.search,
    case_status: filters.case_status?.join(",") || undefined,
    ready_for_review:
      filters.ready_for_review != null ? String(filters.ready_for_review) : undefined,
    has_overdue_actions:
      filters.has_overdue_actions != null
        ? String(filters.has_overdue_actions)
        : undefined,
    has_active_impediment:
      filters.has_active_impediment != null
        ? String(filters.has_active_impediment)
        : undefined,
    limit: filters.limit != null ? String(filters.limit) : undefined,
  };
}

export function useIsoIntelligenceCockpitSummary() {
  const { currentOrganizationId, requestGeneration } = useOrganization();

  return useQuery({
    queryKey: currentOrganizationId
      ? [
          ...queryKeys.isoIntelligenceCockpitSummary(currentOrganizationId),
          requestGeneration,
        ]
      : ["org", "none", "iso-intelligence", "cockpit", "summary"],
    enabled: !!currentOrganizationId,
    refetchOnWindowFocus: false,
    placeholderData: (previous) => previous,
    queryFn: async (): Promise<CockpitSummaryOut> => {
      const orgId = currentOrganizationId;
      if (!orgId) throw new Error("organization required");
      try {
        return await guardTenant(async () => {
          const client = getQmindClient();
          const res =
            await client.api.getCurrentOrganizationIsoIntelligenceCockpitSummary();
          if (!res.data) throw new Error("Empty cockpit summary");
          return res.data;
        });
      } catch (e) {
        if (e instanceof StaleTenantResponseError) {
          throw e;
        }
        throw e;
      }
    },
  });
}

export function useIsoIntelligenceCockpitCases(filters: CockpitCaseFilters = {}) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  const keyFilters = filtersKey(filters);
  const limit = filters.limit ?? 25;

  return useInfiniteQuery({
    queryKey: currentOrganizationId
      ? [
          ...queryKeys.isoIntelligenceCockpitCases(
            currentOrganizationId,
            keyFilters,
          ),
          requestGeneration,
        ]
      : ["org", "none", "iso-intelligence", "cockpit", "cases"],
    enabled: !!currentOrganizationId,
    refetchOnWindowFocus: false,
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage: CockpitCasesPageOut) =>
      lastPage.next_cursor ?? undefined,
    queryFn: async ({ pageParam }): Promise<CockpitCasesPageOut> => {
      const orgId = currentOrganizationId;
      if (!orgId) throw new Error("organization required");
      return guardTenant(async () => {
        const client = getQmindClient();
        const res =
          await client.api.listCurrentOrganizationIsoIntelligenceCockpitCases({
            query: {
              priority_band: filters.priority_band ?? null,
              execution_posture: filters.execution_posture ?? null,
              intelligence_freshness: filters.intelligence_freshness ?? null,
              measurement_posture: filters.measurement_posture ?? null,
              target_posture: filters.target_posture ?? null,
              signal_category: filters.signal_category ?? null,
              related_process: filters.related_process ?? null,
              search: filters.search ?? null,
              case_status: filters.case_status ?? null,
              ready_for_review: filters.ready_for_review ?? null,
              has_overdue_actions: filters.has_overdue_actions ?? null,
              has_active_impediment: filters.has_active_impediment ?? null,
              limit,
              cursor: pageParam,
            },
          });
        if (!res.data) throw new Error("Empty cockpit cases");
        return res.data;
      });
    },
  });
}

export function useIsoIntelligenceCockpitActivity(options?: {
  activity_window_days?: 7 | 30 | 90;
  limit?: number;
}) {
  const { currentOrganizationId, requestGeneration } = useOrganization();
  const activity_window_days = options?.activity_window_days ?? 30;
  const limit = options?.limit ?? 20;

  return useQuery({
    queryKey: currentOrganizationId
      ? [
          ...queryKeys.isoIntelligenceCockpitActivity(currentOrganizationId, {
            activity_window_days,
            limit,
          }),
          requestGeneration,
        ]
      : ["org", "none", "iso-intelligence", "cockpit", "activity"],
    enabled: !!currentOrganizationId,
    refetchOnWindowFocus: false,
    placeholderData: (previous) => previous,
    queryFn: async (): Promise<CockpitActivityPageOut> => {
      const orgId = currentOrganizationId;
      if (!orgId) throw new Error("organization required");
      return guardTenant(async () => {
        const client = getQmindClient();
        const res =
          await client.api.listCurrentOrganizationIsoIntelligenceCockpitActivity(
            {
              query: { activity_window_days, limit },
            },
          );
        if (!res.data) throw new Error("Empty cockpit activity");
        return res.data;
      });
    },
  });
}
