import type { HotpageIconName } from "./iconNames";

/** Capítulos canônicos da Jornada V2 (ordem estável). */
export const JOURNEY_CHAPTER_IDS = [
  "understand",
  "assess",
  "recognize",
  "analyze",
  "execute",
  "evidence_measure",
  "interpret",
  "control",
  "decide",
] as const;

export type JourneyChapterId = (typeof JOURNEY_CHAPTER_IDS)[number];

export type JourneyChapter = {
  id: JourneyChapterId;
  label: string;
  title: string;
  situation: string;
  organizes: string;
  evidence: string;
  humanAction: string;
  observableResult: string;
  icon: HotpageIconName;
};

export type IllustrativeExampleStep = {
  id: string;
  label: string;
  detail: string;
};

export type ProductCapability = {
  id: string;
  name: string;
  problem: string;
  productEvidence: string;
  humanLimit: string;
  chapterId: JourneyChapterId;
  icon: HotpageIconName;
};

export type GuidedTourContextRequirement =
  | "organization"
  | "assessment"
  | "case"
  | "action"
  | "cockpit";

export type GuidedTourStepAvailabilityStatus =
  | "ready"
  | "unavailable"
  | "forbidden"
  | "loading"
  | "error";

export type GuidedTourStepAvailability = {
  status: GuidedTourStepAvailabilityStatus;
  href: string | null;
  reason: string | null;
};

export type GuidedTourSpeakBlocks = {
  demonstrate: string;
  message: string;
  limitation: string;
};

export type GuidedTourStepDef = GuidedTourSpeakBlocks & {
  id: JourneyChapterId;
  title: string;
  contextRequirement: GuidedTourContextRequirement;
  order: number;
};

/** Fatos demonstráveis derivados de GETs (Evolution/ações) — sem mutação. */
export type TourDemoFacts = {
  hasAnalysisRun: boolean;
  hasActionItem: boolean;
  hasMeasurement: boolean;
  hasExecutionIntelligence: boolean;
  hasOutcome: boolean;
};

export type TourDemoContext = {
  organizationId: string | null;
  roles: readonly string[];
  assessmentId: string | null;
  caseId: string | null;
  actionItemId: string | null;
  assessmentsLoading: boolean;
  casesLoading: boolean;
  actionsLoading: boolean;
  evolutionLoading: boolean;
  assessmentsError: boolean;
  casesError: boolean;
  actionsError: boolean;
  evolutionError: boolean;
  /** Conteúdo real no caso/ação em foco (Evolution + ações). */
  facts: TourDemoFacts;
};
