import type { CalendarDay } from "./calendarApi";

export function isProductionDay(day: Pick<CalendarDay, "status">): boolean {
  return day.status !== "past" && day.status !== "closed";
}

export function isDaySelectable(day: Pick<CalendarDay, "status">): boolean {
  return isProductionDay(day) && day.status !== "full" && day.status !== "same_day";
}

/**
 * Dia que a vitrine vende: mesma regra do servidor para recusar a solicitação de data.
 * Vale também quando a ficha do pão ainda não informa unidades/base (reserva fica para o aceite).
 */
export function isSellableDay(
  day: Pick<CalendarDay, "eligible" | "reason" | "remaining_physical">,
): boolean {
  const catalogGap = day.reason === "unknown_units" || day.reason === "unknown_base";
  return (day.eligible || catalogGap) && day.remaining_physical > 0;
}

export function showsBreadIcon(
  day: Pick<CalendarDay, "status">,
  loading: boolean,
  error: boolean,
): boolean {
  return !loading && !error && isProductionDay(day);
}

export function parsePreferredTime(value: string): string | null {
  const text = value.trim();
  if (!text) {
    return null;
  }
  return /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(text) ? text : null;
}

export function preferredTimeOutsideWindows(
  preferred: string | null,
  windows: CalendarDay["windows"] | undefined,
): boolean {
  if (!preferred || !windows?.length) {
    return false;
  }
  const [hour, minute] = preferred.split(":").map(Number);
  const minutes = hour * 60 + minute;
  return !windows.some((window) => {
    const start = timeMinutesFromIso(window.starts_at);
    const end = timeMinutesFromIso(window.ends_at);
    if (start === null || end === null) {
      return false;
    }
    return minutes >= start && minutes < end;
  });
}

function timeMinutesFromIso(value: string): number | null {
  const match = value.match(/T(\d{2}):(\d{2})/);
  if (!match) {
    return null;
  }
  return Number(match[1]) * 60 + Number(match[2]);
}

export function formatWindowLabel(window: { starts_at: string; ends_at: string }): string {
  const start = window.starts_at.match(/T(\d{2}:\d{2})/)?.[1];
  const end = window.ends_at.match(/T(\d{2}:\d{2})/)?.[1];
  if (!start || !end) {
    return "";
  }
  return `${start} às ${end}`;
}
