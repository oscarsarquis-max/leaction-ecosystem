export type DecimalString = string;

export type Association = {
  organization_id: string;
  display_name: string;
  slug: string;
  roles: string[];
  status: string;
  permissions: string[];
};

export type Me = {
  user_id: string;
  display_name: string;
  status: string;
  selected_organization_id: string | null;
  associations: Association[];
  roles: string[];
  permissions: string[];
};

export type Page<T> = {
  items: T[];
  next_cursor: string | null;
};

export type Envelope<T> = {
  data: T;
  row_version?: number | null;
};

export type Plan = {
  id: string;
  public_code: string;
  establishment_id: string;
  operational_date: string;
  shift: string | null;
  status: string;
  notes: string | null;
  row_version: number;
  created_at: string;
  updated_at: string;
  scheduled_at: string | null;
};

export type PlanItem = {
  id: string;
  technical_product_id: string;
  target_mode: string;
  target_quantity: DecimalString;
  unit_weight_g: DecimalString | null;
  priority: number;
  sort_order: number;
  notes: string | null;
};

export type PlanDetail = Plan & { items: PlanItem[] };

export type Order = {
  id: string;
  public_code: string;
  establishment_id: string;
  plan_id: string | null;
  technical_product_id: string;
  target_mode: string;
  target_quantity: DecimalString;
  priority: number;
  status: string;
  planned_start_at: string | null;
  planned_end_at: string | null;
  row_version: number;
  materials_hash: string | null;
  steps_hash: string | null;
  snapshot_hash: string | null;
};

export type Batch = {
  id: string;
  production_order_id: string;
  sequence: number;
  operational_code: string;
  target_mode: string;
  target_quantity: DecimalString;
  status: string;
  row_version: number;
  planned_start_at: string | null;
  planned_end_at: string | null;
};

export type Conversion = {
  entered_quantity: DecimalString;
  entered_unit: string;
  canonical_quantity: DecimalString;
  canonical_unit: string;
  conversion_factor: DecimalString;
  conversion_source: string;
  conversion_version: string;
};

export type BoardCard = {
  order: {
    id: string;
    public_code: string;
    status: string;
    priority: number;
    row_version: number;
  };
  batches: Batch[];
  product: { id: string; code: string; display_name: string };
  quantity: DecimalString;
  target_mode: string;
  planned_start_at: string | null;
  planned_end_at: string | null;
  operational_date: string | null;
  shift: string | null;
  current_step: string | null;
  dependencies: Array<{
    id: string;
    predecessor_order_id: string;
    dependency_type: string;
  }>;
  blocked: boolean;
  open_occurrences: number;
  delayed: boolean;
  next_action: string | null;
  has_execution_facts: boolean;
};

export type BoardFilters = {
  operational_date?: string;
  date_from?: string;
  date_to?: string;
  establishment_id?: string;
  shift?: string;
  area?: string;
  product_id?: string;
  status?: string;
  priority?: string;
  q?: string;
};

export type MaterialsView = {
  planned: Array<{ id: string; name: string; gross: DecimalString; unit: string }>;
  actual: Array<{
    id: string;
    planned_gross: DecimalString;
    weighed_canonical: DecimalString;
    consumption: Record<string, DecimalString>;
  }>;
};

export type StepsView = {
  planned: Array<{ id: string; title: string; sequence: number }>;
  actual: Array<{ id: string; status: string }>;
};

export type WeighingsView = {
  entries: Array<{ id: string } & Conversion>;
  verifications: Array<{ id: string; entry_id: string; decision: string }>;
};

export type Consumption = { id: string; type: string } & Conversion;

export type YieldRow = { id: string; type: string; quantity: DecimalString };

export type Occurrence = { id: string; category: string; status: string };

export type Dependency = { id: string; predecessor_order_id: string; dependency_type: string };

export type EventRow = { id: string; type: string; command: string; occurred_at: string };

export type SheetSummary = {
  id: string;
  issue_number: number;
  payload_sha256: string;
  purpose: string;
};

export type SheetPayload = {
  schema_version?: string;
  order?: {
    id?: string;
    public_code?: string;
    status?: string;
    target_mode?: string;
    target_quantity?: string;
    materials_hash?: string | null;
    steps_hash?: string | null;
    snapshot_hash?: string | null;
    policy_hash?: string | null;
  };
  policy?: Record<string, unknown>;
  materials?: Array<Record<string, unknown>>;
  steps?: Array<Record<string, unknown>>;
  batches?: Array<Record<string, unknown>>;
  [key: string]: unknown;
};

export type SheetIssue = {
  id: string;
  issue_number: number;
  purpose: string;
  order_status_at_issue: string;
  previous_issue_id: string | null;
  payload_sha256: string;
  canonical_payload: SheetPayload;
};

export type Traceability = {
  order: {
    id: string;
    public_code: string;
    status: string;
    formulation_version_id: string | null;
    scale_calculation_id: string | null;
    materials_hash: string | null;
    steps_hash: string | null;
    snapshot_hash: string | null;
    policy_hash: string | null;
  };
  batches: Array<{ id: string; operational_code: string; status: string }>;
  planned_materials: Array<{
    id: string;
    name: string;
    gross: DecimalString;
    unit: string;
  }>;
  planned_steps: Array<{ id: string; title: string }>;
  actual_materials: Array<{
    batch_material_id: string;
    planned_gross: DecimalString;
    weighed_canonical: DecimalString;
    consumption: Record<string, DecimalString>;
  }>;
  weighings: Array<{ id: string; lot_code: string | null; operator_user_id: string } & Conversion>;
  verifications: Array<{
    id: string;
    entry_id: string;
    decision: string;
    verifier_user_id: string;
  }>;
  consumptions: Consumption[];
  step_runs: Array<{ id: string; status: string; operator_user_id: string | null }>;
  yields: YieldRow[];
  occurrences: Occurrence[];
  dependencies: Array<{ id: string; predecessor_order_id: string; type: string }>;
  overrides: Array<{ id: string; reason: string }>;
  sheet_issues: Array<{ id: string; issue_number: number; payload_sha256: string }>;
  events: EventRow[];
};
