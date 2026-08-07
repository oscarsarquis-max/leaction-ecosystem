/** View model da Central de Campo — reutilizável (UI + futuro assistente). */

export type FieldPhaseMode =
  | "draft_redirect"
  | "planned_handoff"
  | "field_active"
  | "field_readonly";

export type FieldNextActionKind =
  | "open_audit_plan"
  | "resolve_blocker"
  | "opening_meeting"
  | "continue_interview"
  | "start_interview"
  | "review_evidence"
  | "register_unplanned"
  | "complete_interview"
  | "prepare_closing"
  | "go_analysis"
  | "none";

export type FieldNextAction = {
  kind: FieldNextActionKind;
  label: string;
  hint: string;
  href?: string;
  interviewId?: string;
  eventId?: string;
  /** Ação local na página (não navegação). */
  localAction?:
    | "focus_opening"
    | "focus_interview"
    | "focus_evidence"
    | "focus_unplanned"
    | "focus_closing";
};

export type FieldTodayItem = {
  id: string;
  kind: "interview" | "meeting" | "milestone";
  title: string;
  status: string;
  statusLabel: string;
  startsAt: string | null;
  processName: string;
  locationOrLink: string;
  preparation: string;
  objective: string;
  interviewId: string | null;
  planActivityKind: string | null;
  done: boolean;
  primaryLabel: string;
};

export type FieldPendency = {
  key: string;
  problem: string;
  impact: string;
  actionLabel: string;
  href?: string;
  localAction?: FieldNextAction["localAction"];
  interviewId?: string;
};

export type EvidenceBucketKey =
  | "early"
  | "field"
  | "verifying"
  | "pending_review"
  | "pending"
  | "rejected";

export type EvidenceBucket = {
  key: EvidenceBucketKey;
  label: string;
  explanation: string;
  count: number;
  evidenceIds: string[];
};

export type FieldProgress = {
  interviewsDone: number;
  interviewsPlanned: number;
  processesCovered: number;
  processesPlanned: number;
  evidencesReady: number;
  evidencesPending: number;
  activitiesDone: number;
  activitiesPlanned: number;
  /** Texto humano — sem % inventado. */
  summary: string;
};

export type FieldClosingPrep = {
  show: boolean;
  covered: string[];
  pending: string[];
  evidencesWaiting: string[];
  interviewsSkipped: string[];
  deepen: string[];
  closingMeetingReady: boolean;
};

/** Contexto seguro para futuro assistente — sem docs completos nem cross-org. */
export type FieldAssistantContext = {
  organization_id: string;
  assessment_id: string;
  phase: string;
  page: "field_central";
  user_role_summary: string[];
  next_action: FieldNextAction;
  current_activity_id: string | null;
  current_activity_title: string | null;
  pendency_keys: string[];
  blockers: string[];
  allowed_links: string[];
};

export type FieldCentralModel = {
  mode: FieldPhaseMode;
  organizationName: string;
  assessmentLabel: string;
  modalityLabel: string;
  scopeSummary: string;
  phaseLabel: string;
  todayLabel: string;
  planStatusLabel: string;
  planReady: boolean;
  openingSatisfied: boolean;
  openingStatusLabel: string | null;
  nextAction: FieldNextAction;
  todayItems: FieldTodayItem[];
  pendencies: FieldPendency[];
  evidenceBuckets: EvidenceBucket[];
  progress: FieldProgress;
  closingPrep: FieldClosingPrep;
  canMutate: boolean;
  assistantContext: FieldAssistantContext;
};
