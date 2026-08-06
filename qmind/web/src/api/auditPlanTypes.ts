export type AuditPlanStatus = "draft" | "ready" | "amended";

export type AuditPlanModality =
  | "diagnosis"
  | "internal_audit"
  | "external_audit"
  | "certification_prep"
  | "other";

export type AuditPlanCriteria = {
  iso9001_2015: boolean;
  internal_processes: boolean;
  legal_contractual: boolean;
  legal_contractual_text: string;
  additional_text: string;
};

export type AuditPlanSite = {
  name: string;
  location: string;
  notes: string;
  from_preparation: boolean;
};

export type AuditPlanProcess = {
  name: string;
  owner: string;
  notes: string;
  from_preparation: boolean;
  interview_justification?: string;
};

export type OrgRepresentative = {
  name: string;
  role: string;
  notes: string;
};

export type ReadinessItem = {
  key: string;
  label: string;
  done: boolean;
  blocking: boolean;
};

export type AuditPlanReadiness = {
  ready: boolean;
  completed_count: number;
  pending_count: number;
  percent: number;
  items: ReadinessItem[];
  next_action: string;
  blockers: string[];
};

export type AuditPlan = {
  id: string;
  organization_id: string;
  assessment_id: string;
  objective: string;
  modality: AuditPlanModality;
  modality_label: string;
  scope_text: string;
  criteria: AuditPlanCriteria;
  sites: AuditPlanSite[];
  processes: AuditPlanProcess[];
  lead_membership_id: string | null;
  team_membership_ids: string[];
  org_representatives: OrgRepresentative[];
  planned_start: string | null;
  planned_end: string | null;
  preparation_notes: string;
  risks_notes: string;
  plan_status: AuditPlanStatus;
  field_sources: Record<string, string>;
  last_amendment_reason: string;
  readiness: AuditPlanReadiness;
  editable: boolean;
  requires_amendment_reason: boolean;
  updated_by_user_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type AuditPlanPatch = {
  objective?: string;
  modality?: AuditPlanModality;
  scope_text?: string;
  criteria?: AuditPlanCriteria;
  sites?: AuditPlanSite[];
  processes?: AuditPlanProcess[];
  lead_membership_id?: string | null;
  team_membership_ids?: string[];
  org_representatives?: OrgRepresentative[];
  planned_start?: string | null;
  planned_end?: string | null;
  preparation_notes?: string;
  risks_notes?: string;
  expected_updated_at?: string;
  amendment_reason?: string;
};

export const MODALITY_OPTIONS: { value: AuditPlanModality; label: string }[] = [
  { value: "internal_audit", label: "Auditoria interna" },
  { value: "external_audit", label: "Auditoria externa" },
  { value: "diagnosis", label: "Diagnóstico inicial" },
  { value: "certification_prep", label: "Preparação para certificação" },
];

export function planStatusLabel(status: AuditPlanStatus): string {
  if (status === "ready") return "Pronto";
  if (status === "amended") return "Emendado";
  return "Rascunho";
}
