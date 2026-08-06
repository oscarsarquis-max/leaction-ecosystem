import type { AssessmentOut } from "@qmind/api-client";

const ACTIVE_STATUSES = new Set([
  "in_progress",
  "analysis",
  "actions",
  "report",
]);

function byUpdatedDesc(a: AssessmentOut, b: AssessmentOut): number {
  const ta = Date.parse(a.updated_at ?? a.created_at ?? "") || 0;
  const tb = Date.parse(b.updated_at ?? b.created_at ?? "") || 0;
  return tb - ta;
}

/**
 * Avaliação em foco na home — uma por vez; nunca mistura progresso.
 * Prioridade: em andamento (recente) → planejada → preparação → última concluída.
 */
export function selectFocusAssessment(
  items: AssessmentOut[],
): AssessmentOut | null {
  const active = items.filter((a) => a.status !== "cancelled");
  if (active.length === 0) return null;

  const inFlight = active
    .filter((a) => ACTIVE_STATUSES.has(a.status))
    .sort(byUpdatedDesc);
  if (inFlight[0]) return inFlight[0];

  const planned = active
    .filter((a) => a.status === "planned")
    .sort(byUpdatedDesc);
  if (planned[0]) return planned[0];

  const draft = active.filter((a) => a.status === "draft").sort(byUpdatedDesc);
  if (draft[0]) return draft[0];

  const closed = active
    .filter((a) => a.status === "closed")
    .sort(byUpdatedDesc);
  return closed[0] ?? null;
}
