/**
 * Persistência do tour autenticado — versão 2 (Jornada V2).
 * Estado antigo (v1 / 11 etapas) é reiniciado com segurança.
 */

import {
  GUIDED_TOUR_V2_STEPS,
  indexOfChapter,
  parseChapterParam,
  type JourneyChapterId,
} from "@/journeyV2";

const TOUR_STEP_KEY = "qmind.guidedTour.step";
const TOUR_ACTIVE_KEY = "qmind.guidedTour.active";
const TOUR_ORG_KEY = "qmind.guidedTour.orgId";
const TOUR_VERSION_KEY = "qmind.guidedTour.version";
const TOUR_VERSION = "2";

/** @deprecated use JourneyChapterId — mantido para testes legíveis */
export type GuidedTourStepId = JourneyChapterId;

export type GuidedTourStep = (typeof GUIDED_TOUR_V2_STEPS)[number];

export const GUIDED_TOUR_STEPS = GUIDED_TOUR_V2_STEPS;

function ensureTourVersion(): void {
  try {
    const v = sessionStorage.getItem(TOUR_VERSION_KEY);
    if (v === TOUR_VERSION) return;
    sessionStorage.setItem(TOUR_VERSION_KEY, TOUR_VERSION);
    sessionStorage.setItem(TOUR_STEP_KEY, "0");
  } catch {
    /* ignore */
  }
}

export function writeGuidedTourActive(orgId: string, stepIndex: number): void {
  try {
    ensureTourVersion();
    sessionStorage.setItem(TOUR_ACTIVE_KEY, "1");
    sessionStorage.setItem(TOUR_ORG_KEY, orgId);
    sessionStorage.setItem(
      TOUR_STEP_KEY,
      String(Math.max(0, Math.min(stepIndex, GUIDED_TOUR_STEPS.length - 1))),
    );
  } catch {
    /* ignore */
  }
}

export function readGuidedTourStepIndex(): number {
  try {
    ensureTourVersion();
    const raw = sessionStorage.getItem(TOUR_STEP_KEY);
    const n = raw == null ? 0 : Number.parseInt(raw, 10);
    if (!Number.isFinite(n) || n < 0) return 0;
    return Math.min(n, GUIDED_TOUR_STEPS.length - 1);
  } catch {
    return 0;
  }
}

export function isGuidedTourActive(orgId: string | null): boolean {
  try {
    ensureTourVersion();
    if (sessionStorage.getItem(TOUR_ACTIVE_KEY) !== "1") return false;
    const storedOrg = sessionStorage.getItem(TOUR_ORG_KEY);
    if (!orgId || !storedOrg || storedOrg !== orgId) return false;
    return true;
  } catch {
    return false;
  }
}

export function setGuidedTourStepIndex(stepIndex: number): void {
  try {
    ensureTourVersion();
    sessionStorage.setItem(
      TOUR_STEP_KEY,
      String(Math.max(0, Math.min(stepIndex, GUIDED_TOUR_STEPS.length - 1))),
    );
  } catch {
    /* ignore */
  }
}

export function clearGuidedTour(): void {
  try {
    sessionStorage.removeItem(TOUR_ACTIVE_KEY);
    sessionStorage.removeItem(TOUR_ORG_KEY);
    sessionStorage.removeItem(TOUR_STEP_KEY);
    sessionStorage.removeItem(TOUR_VERSION_KEY);
  } catch {
    /* ignore */
  }
}

/** Resolve índice a partir de ?chapter= allowlisted; inválido → 0. */
export function stepIndexFromChapterParam(
  raw: string | null | undefined,
): number {
  const id = parseChapterParam(raw);
  if (!id) return 0;
  return indexOfChapter(id);
}

export function chapterIdFromStepIndex(stepIndex: number): JourneyChapterId {
  return (
    GUIDED_TOUR_STEPS[Math.max(0, Math.min(stepIndex, GUIDED_TOUR_STEPS.length - 1))]
      ?.id ?? "understand"
  );
}
