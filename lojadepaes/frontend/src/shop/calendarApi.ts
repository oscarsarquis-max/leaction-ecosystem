import { requestJson } from "../services/http";

export type CalendarLine = {
  kind: "product" | "custom";
  quantity: number;
  variant_id?: string;
  dough_type_id?: string;
};

export type CalendarDay = {
  date: string;
  status: string;
  origin: string;
  daily_physical_limit: number;
  daily_base_limit: number;
  committed_physical: number;
  remaining_physical: number;
  reason: string;
  accessible_label: string;
  weekday_name: string;
  eligible: boolean;
  awaiting_review?: boolean;
  windows: Array<{
    id: string;
    starts_at: string;
    ends_at: string;
    modality: string;
  }>;
};

export type CalendarPreview = {
  occupancy_enabled: boolean;
  reservation_policy: string;
  timezone: string;
  selected_date: string | null;
  selected_status: string | null;
  full_message: string | null;
  alternatives: Array<{ date: string; accessible_label: string; weekday_name: string }>;
  notice: string | null;
  review_message?: string | null;
  days: CalendarDay[];
};

export function previewCalendar(payload: {
  start?: string;
  end?: string;
  selected?: string | null;
  lines?: CalendarLine[];
}): Promise<CalendarPreview> {
  return requestJson<CalendarPreview>("/api/v1/schedule/preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
