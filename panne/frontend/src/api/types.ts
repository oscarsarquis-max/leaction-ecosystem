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

export type Catalog = {
  mass_units: Array<{
    id: string;
    code: string;
    name: string;
    symbol: string;
    dimension: string;
  }>;
  yield_types: string[];
  occurrence_categories: string[];
  occurrence_severities: string[];
  consumption_types: string[];
  verification_decisions: string[];
  sheet_purposes: string[];
  weighing_policies: string[];
  verification_policies: string[];
  order_statuses: string[];
  batch_statuses: string[];
  step_statuses: string[];
};

export type ReadinessItem = { ok: boolean; reason: string | null };

export type ExecutionMaterial = {
  id: string;
  batch_id: string;
  name: string;
  measurement_unit_id: string | null;
  unit: string | null;
  planned_gross: DecimalString;
  weighed_canonical: DecimalString;
  weigh_state: string;
  consumption: Record<string, DecimalString>;
};

export type ExecutionWeighing = {
  id: string;
  session_id: string;
  batch_material_id: string;
  entry_type: string;
  measurement_unit_id: string;
  operator_user_id: string;
  operator_name: string | null;
  lot_code: string | null;
  justification: string | null;
  planned_quantity: DecimalString | null;
  absolute_difference: DecimalString | null;
  percent_difference: DecimalString | null;
  within_tolerance: boolean;
  verification: {
    id: string;
    decision: string;
    verifier_user_id: string;
    verifier_name: string | null;
    justification: string | null;
  } | null;
} & Conversion;

export type ExecutionStep = {
  order_step_id: string;
  batch_id: string;
  title: string;
  instructions: string;
  sequence: number;
  duration_seconds: number | null;
  temperature_value: DecimalString | null;
  temperature_unit: string | null;
  execution_id: string | null;
  status: string;
  row_version: number | null;
  operator_user_id: string | null;
  operator_name: string | null;
  started_at: string | null;
  ended_at: string | null;
  measured_duration_seconds: number | null;
  measured_temperature: DecimalString | null;
  notes: string | null;
};

export type ExecutionBatch = Batch & {
  materials: ExecutionMaterial[];
  sessions: Array<{ id: string; status: string; row_version: number; opened_by_user_id: string }>;
  weighings: ExecutionWeighing[];
  steps: ExecutionStep[];
  yields: Array<{
    id: string;
    type: string;
    quantity: DecimalString;
    unit: string;
    measurement_unit_id: string;
    notes: string | null;
  }>;
  yield_projection: {
    final_mass: DecimalString | null;
    sellable_units: DecimalString | null;
    rejected_units: DecimalString | null;
    leftover: DecimalString | null;
    scrap: DecimalString | null;
    loss_absolute: DecimalString | null;
    loss_percent: DecimalString | null;
    target_deviation: DecimalString | null;
    completeness: string;
    within_tolerance: boolean | null;
  };
};

export type ExecutionView = {
  viewer: { user_id: string; display_name: string; permissions: string[] };
  order: Order;
  product: { id: string; code: string; display_name: string } | null;
  establishment: { id: string; code: string; display_name: string } | null;
  policy: Record<string, unknown> | null;
  batches: ExecutionBatch[];
  occurrences: Array<{
    id: string;
    category: string;
    severity: string;
    status: string;
    description: string;
    is_blocking: boolean;
    batch_id: string | null;
    order_step_id: string | null;
  }>;
  dependencies: Dependency[];
  sheets: Array<SheetSummary & { previous_issue_id: string | null }>;
  blocked: boolean;
  open_session: boolean;
  next_action: string | null;
  readiness: {
    weighing: ReadinessItem;
    verifications: ReadinessItem;
    steps: ReadinessItem;
    consumptions: ReadinessItem;
    yields: ReadinessItem;
    dependencies: ReadinessItem;
    blocking_occurrences: ReadinessItem;
    permissions: Record<string, boolean>;
  };
  updated_at: string;
};

export type SheetPayload = {
  schema_version?: string;
  establishment?: { id?: string | null; code?: string | null; display_name?: string | null };
  organization?: { id?: string | null; slug?: string | null; display_name?: string | null };
  issuer?: { user_id?: string; display_name?: string | null; issued_at?: string | null };
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

export type IngredientCard = {
  id: string;
  code: string;
  display_name: string;
  ingredient_type: string;
  status: string;
  row_version: number;
  current_version: { id: string; version_number: number; status: string } | null;
};

export type IngredientVersion = {
  id: string;
  ingredient_id: string;
  version_number: number;
  status: string;
  data_source_id: string | null;
  notes: string | null;
  row_version: number;
  nutrition_basis_unit_id: string;
  created_by_user_id?: string | null;
};

export type Completeness = {
  ready_to_publish: boolean;
  complete_dossier: boolean;
  items: Array<{ code: string; label: string; blocking: boolean; origin: string }>;
};

export type IngredientPage = {
  items: IngredientCard[];
  total: number;
  limit: number;
  offset: number;
};

export type SupplierCard = {
  id: string;
  code: string;
  display_name: string;
  status: string;
  row_version: number;
};

export type CatalogItem = {
  id: string;
  code?: string;
  name?: string;
  title?: string;
  access: string;
};

export type CompositionLine = {
  id: string;
  component_version_id: string;
  component_type: string;
  quantity: string;
  measurement_unit_id: string;
  sequence: number;
};

export type NutrientLine = {
  id: string;
  nutrient_id: string;
  value: string | null;
  value_status: string;
  limit_of_quantification: string | null;
  loq_unit_id: string | null;
  method_or_source: string | null;
};

export type AllergenLine = {
  id: string;
  allergen_id: string;
  presence: string;
  data_source_id: string | null;
  evidence_note: string | null;
};

export type SupplierItemCard = {
  id: string;
  supplier_id: string;
  ingredient_id: string;
  supplier_sku: string;
  description: string | null;
  package_quantity: string;
  measurement_unit_id: string;
  status: string;
  row_version: number;
  latest_purchase: { unit_price: string; currency: string; observed_at: string } | null;
};

export type IngredientDossier = {
  identity: IngredientCard;
  version: IngredientVersion;
  composition: CompositionLine[];
  nutrients: NutrientLine[];
  allergens: AllergenLine[];
  completeness: Completeness;
};
