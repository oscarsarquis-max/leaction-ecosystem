import { requestJson } from "../services/http";
import type { CalendarLine } from "./calendarApi";
import type { Money } from "./types";

export type SuggestionItem = {
  name: string;
  slug: string;
  presentation: string;
  image_url: string | null;
  image_alt: string;
  price: Money;
  price_is_from: boolean;
  href: string;
};

export type SuggestionsPayload = {
  context_date: string | null;
  context_source: "selected" | "next_eligible" | "none";
  context_label: string | null;
  mode: "new_types" | "already_programmed" | "empty";
  title: string;
  message: string | null;
  items: SuggestionItem[];
};

export type DateRequestResult = {
  id: string;
  status: string;
  desired_date: string;
  message: string;
};

export function fetchSuggestions(payload: {
  selected?: string | null;
  lines: CalendarLine[];
}): Promise<SuggestionsPayload> {
  return requestJson<SuggestionsPayload>("/api/v1/schedule/suggestions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      selected: payload.selected || null,
      lines: payload.lines,
    }),
  });
}

export function submitDateRequest(payload: {
  desired_date: string;
  customer_name: string;
  customer_email: string;
  intended_quantity?: number;
  message?: string;
  idempotency_key: string;
  lines: Array<{ variant_id: string; quantity: number }>;
}): Promise<DateRequestResult> {
  return requestJson<DateRequestResult>("/api/v1/schedule/date-requests", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
