import { getQmindClient, withTenantGeneration } from "@/api/qmindApi";

export type AgendaEventType =
  | "interview"
  | "meeting"
  | "visit"
  | "reminder"
  | "milestone"
  | "deadline"
  | "other";

export type AgendaEventStatus = "scheduled" | "completed" | "cancelled";

export type AgendaEvent = {
  id: string;
  organization_id: string;
  assessment_id: string | null;
  assessment_label: string | null;
  title: string;
  description: string;
  event_type: AgendaEventType;
  starts_at: string;
  ends_at: string | null;
  timezone: string;
  owner_membership_id: string | null;
  owner_label: string | null;
  participant_membership_ids: string[];
  location_or_link: string;
  status: AgendaEventStatus;
  guidance: string;
  related_action: string;
  source_kind: string | null;
  source_id: string | null;
  is_auto: boolean;
  is_overdue: boolean;
  primary_action_label: string;
  primary_action_href: string | null;
  why_it_matters: string;
  preparation: string;
  created_at: string;
  updated_at: string;
};

export type AgendaDaySummary = {
  date: string;
  count: number;
  has_overdue: boolean;
};

export type AgendaBoard = {
  timezone: string;
  selected_date: string;
  next_up: AgendaEvent | null;
  today: AgendaEvent[];
  selected_day: AgendaEvent[];
  overdue: AgendaEvent[];
  in_progress_assessments: { id: string; label: string; href: string }[];
  month_markers: AgendaDaySummary[];
};

export type AgendaEventCreate = {
  assessment_id?: string | null;
  title: string;
  description?: string;
  event_type: AgendaEventType;
  starts_at: string;
  ends_at?: string | null;
  timezone?: string;
  owner_membership_id?: string | null;
  participant_membership_ids?: string[];
  location_or_link?: string;
  guidance?: string;
  related_action?: string;
};

export async function fetchAgendaBoard(
  selectedDate?: string,
): Promise<AgendaBoard> {
  const client = getQmindClient();
  const qs = selectedDate
    ? `?selected_date=${encodeURIComponent(selectedDate)}`
    : "";
  return withTenantGeneration(async () => {
    const res = await client.raw.get({
      url: `/api/v1/agenda/board${qs}`,
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as AgendaBoard;
  });
}

export async function createAgendaEvent(
  payload: AgendaEventCreate,
): Promise<AgendaEvent> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.post({
      url: "/api/v1/agenda/events",
      body: payload,
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as AgendaEvent;
  });
}

export async function updateAgendaEvent(
  eventId: string,
  payload: Partial<AgendaEventCreate> & { status?: AgendaEventStatus },
): Promise<AgendaEvent> {
  const client = getQmindClient();
  return withTenantGeneration(async () => {
    const res = await client.raw.patch({
      url: `/api/v1/agenda/events/${eventId}`,
      body: payload,
      headers: { "Content-Type": "application/json" },
      security: [{ scheme: "bearer", type: "http" }],
    });
    return res.data as AgendaEvent;
  });
}
