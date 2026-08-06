export type ScheduleItemKind = "interview" | "meeting" | "milestone";

export type PlanActivityKind =
  | "opening_meeting"
  | "closing_meeting"
  | "additional_meeting"
  | "milestone_preparation_done"
  | "milestone_plan_approved"
  | "milestone_field_start"
  | "milestone_field_done"
  | "milestone_analysis_done"
  | "milestone_report_due"
  | "milestone_closure_due"
  | "milestone_custom";

export type ScheduleItem = {
  kind: ScheduleItemKind;
  id: string;
  title: string;
  status: string;
  starts_at?: string | null;
  ends_at?: string | null;
  timezone: string;
  location_or_link: string;
  preparation: string;
  objective: string;
  process_name: string;
  owner_membership_id?: string | null;
  participant_membership_ids: string[];
  plan_activity_kind?: PlanActivityKind | null;
  interview_id?: string | null;
  agenda_event_id?: string | null;
  primary_action_label: string;
  primary_action_href?: string | null;
  next_action: string;
};

export type OverlapWarning = {
  message: string;
  membership_id?: string | null;
  item_ids: string[];
};

export type SchedulePending = {
  key: string;
  label: string;
  blocking: boolean;
};

export type AuditPlanSchedule = {
  assessment_id: string;
  organization_id: string;
  timezone: string;
  agenda_href: string;
  items: ScheduleItem[];
  overlaps: OverlapWarning[];
  pendings: SchedulePending[];
  next_action: string;
  has_opening_meeting: boolean;
  has_closing_meeting: boolean;
};

export type ScheduleMeetingCreate = {
  kind: "opening_meeting" | "closing_meeting" | "additional_meeting";
  objective?: string;
  participant_membership_ids?: string[];
  starts_at: string;
  duration_minutes?: number;
  location_or_link?: string;
  preparation?: string;
  owner_membership_id?: string | null;
  title?: string;
  outside_period_justification?: string;
  timezone?: string;
};

export type ScheduleMilestoneCreate = {
  kind: Exclude<
    PlanActivityKind,
    "opening_meeting" | "closing_meeting" | "additional_meeting"
  >;
  title?: string;
  notes?: string;
  occurs_at: string;
  owner_membership_id?: string | null;
  outside_period_justification?: string;
  timezone?: string;
};

export type PlannedInterviewCreate = {
  title: string;
  objective?: string;
  process_name?: string;
  org_contact_name?: string;
  interviewer_membership_id?: string | null;
  participant_membership_ids?: string[];
  scheduled_at: string;
  duration_minutes?: number;
  location?: string;
  remote_link?: string;
  preparation?: string;
  mode?: "onsite" | "remote" | "hybrid";
  outside_period_justification?: string;
};
