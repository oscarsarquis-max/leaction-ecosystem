import type { TrackChipData } from "../types";

const TONE_CLASS: Record<string, string> = {
  open: "c-open",
  accepted: "c-acc",
  paid: "c-paid",
  production: "c-prod",
  delivered: "c-del",
  cancelled: "c-can",
  warn: "c-warn",
  none: "c-none",
};

export function trackAccessibleName(name: string, track: TrackChipData): string {
  if (track.label === "—" || track.state === "not_applicable") {
    return `${name}: não se aplica`;
  }
  return track.hint ? `${name}: ${track.label}. ${track.hint}` : `${name}: ${track.label}`;
}

export function TrackChip({ name, track }: { name: string; track: TrackChipData }) {
  const tone = TONE_CLASS[track.tone] ?? "c-none";
  return (
    <span className={`admin-chip queue-chip ${tone}`} title={track.hint ?? undefined}>
      <span className="dot" aria-hidden="true" />
      <span className="queue-chip-label">{track.label}</span>
      <span className="queue-sr">{trackAccessibleName(name, track)}</span>
    </span>
  );
}
