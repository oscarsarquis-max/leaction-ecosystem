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

export type RecipeCard = {
  id: string;
  code: string;
  display_name: string;
  status: string;
  technical_product_id: string;
  row_version: number;
  current_version: { id: string; version_number: number; status: string } | null;
};

export type RecipeVersion = {
  id: string;
  formulation_id: string;
  version_number: number;
  status: string;
  yield_units: number | null;
  target_unit_weight_g: string | null;
  expected_bake_loss_rate: string | null;
  notes: string | null;
  published_at: string | null;
  row_version: number;
};

export type RecipeItem = {
  id: string;
  ingredient_version_id: string;
  sequence: number;
  net_quantity: string;
  gross_quantity: string | null;
  measurement_unit_id: string;
  correction_factor: string;
  is_flour_basis: boolean;
  role: string;
  notes: string | null;
  bakers_percentage: string | null;
};

export type RecipeStep = {
  id: string;
  sequence: number;
  title: string;
  instructions: string;
  duration_seconds: number | null;
  temperature_celsius: string | null;
};

export type BakersView = {
  flour_mass: string | null;
  explained_absence: boolean;
  items: Array<{
    id: string;
    net_quantity: string;
    gross_quantity: string;
    is_flour_basis: boolean;
    bakers_percentage: string | null;
  }>;
};

export type YieldView = {
  base_net_mass: string | null;
  yield_units: number | null;
  target_unit_weight_g: string | null;
  expected_bake_loss_rate: string | null;
  expected_final_mass_g: string | null;
  portion_mass_g: string | null;
};

export type ScaleRow = {
  id?: string;
  calculation_mode: string;
  scale_factor: string | null;
  base_total_net_mass: string | null;
  required_pre_bake_mass: string | null;
  algorithm_code?: string;
  algorithm_version?: string;
  persisted?: boolean;
  items?: Array<{
    sequence: number;
    scaled_net_quantity: string | null;
    scaled_gross_quantity: string | null;
    bakers_percentage: string | null;
  }>;
};

export type TrialRow = {
  id: string;
  code: string;
  status: string;
  notes: string | null;
  measurements?: Array<{
    id: string;
    measurement_type: string;
    value: string | null;
  }>;
};

export type ApprovalRow = {
  id: string;
  decision: string;
  notes: string | null;
  occurred_at: string;
};

export type RecipeReference = {
  id: string;
  title: string;
  source_type: string;
  source_url: string | null;
  author: string | null;
  notes: string | null;
};

export type RecipeReferenceLink = {
  id: string;
  recipe_reference_id: string;
  role: string;
};

export type NutritionPreview = {
  id: string;
  status: string;
  formula_net_mass_g: string | null;
  expected_final_mass_g: string | null;
  portion_mass_g: string | null;
  disclaimer: string;
  items?: Array<{
    nutrient_definition_id: string;
    whole_formula_amount: string | null;
    per_100g_amount: string | null;
    technical_portion_amount: string | null;
    completeness_status: string;
  }>;
};

export type TechnicalSheet = {
  kind: string;
  disclaimer: string;
  payload_sha256: string;
  identity: RecipeCard & { product_name?: string | null };
  version: RecipeVersion;
  organization: { display_name: string };
  responsible: { display_name: string | null };
  components: RecipeItem[];
  steps: RecipeStep[];
  completeness: Completeness;
};

export type RecipePage = {
  items: RecipeCard[];
  total: number;
  limit: number;
  offset: number;
};

export type RecipeDossier = {
  identity: RecipeCard;
  version: RecipeVersion;
  items: RecipeItem[];
  steps: RecipeStep[];
  bakers: BakersView;
  yield: YieldView;
  completeness: Completeness;
};

export type RecipeAiChange = {
  change_key: string;
  change_kind: "added" | "removed" | "changed" | "unresolved";
  path: string;
  before_value: Record<string, unknown> | null;
  after_value: Record<string, unknown> | null;
  decision: "pending" | "accepted" | "rejected";
};

export type RecipeAiProposal = {
  id: string;
  intent: "create_recipe" | "adapt_recipe";
  title: string;
  objective_summary: string;
  status: string;
  status_label: string;
  assisted_by_ai: boolean;
  base_formulation_version_id: string | null;
  materialized_formulation_version_id: string | null;
  warnings: string[];
  missing_data: string[];
  row_version: number;
  items?: Array<{
    id: string;
    sequence: number;
    ingredient_version_id: string | null;
    proposed_ingredient_name: string;
    resolution_status: string;
    net_quantity_g: string | null;
    rationale: string;
  }>;
  steps?: Array<{ sequence: number; title: string; instructions: string }>;
  citations?: Array<{ id: string; claim_path: string }>;
  changes?: RecipeAiChange[];
  materialized?: { formulation_id: string; version_id: string; status: string } | null;
  guided_input?: Record<string, unknown>;
};

export type LabelingFinding = {
  rule_code: string;
  result: string;
  fact: string;
  expected_value: string | null;
  found_value: string | null;
  source_code: string;
  source_locator: string;
  explanation: string;
  action_needed: boolean;
};

export type LabelingDossier = {
  id: string;
  status: string;
  formulation_id: string;
  formulation_version_id: string;
  row_version: number;
  disclaimer: string;
  certified?: boolean;
  conforme_anvisa?: boolean;
  profile?: Record<string, unknown>;
  versions?: Array<{ id: string; version_number: number; status: string; content_hash: string }>;
  current?: {
    version: { id: string; version_number: number; status: string; content_hash: string };
    assessment: { proposal_summary: string; status: string } | null;
    findings: LabelingFinding[];
    nutrition: {
      portion_g: string | null;
      household_measure: string | null;
      footnotes: string[];
      lines: Array<{
        nutrient_code: string;
        technical_per_100g: string | null;
        declared_per_100g: string | null;
        declared_per_serving: string | null;
        daily_value_percent: string | null;
        completeness: string;
        presented: string | null;
      }>;
    } | null;
    front_of_pack: {
      magnifier_required: boolean | null;
      nutrients_high: string[];
      compared: Record<string, unknown>;
      added_sugars_result: string;
      saturated_fat_result: string;
      sodium_result: string;
      disclaimer: string;
    } | null;
    ingredients: Array<{
      sequence: number;
      display_name: string;
      compound: boolean;
      components: Array<{ name?: string | null }>;
      gap: string | null;
    }>;
    warnings: Array<{ code: string; statement: string; result: string }>;
    mandatory: Array<{
      code: string;
      label: string;
      value: string | null;
      status: string;
      claim: boolean;
    }>;
    candidate: { watermark: string; payload_sha256: string; payload: Record<string, unknown> } | null;
    reviews: Array<{ decision: string; notes: string | null }>;
  } | null;
};

export type CostingPolicy = {
  id: string;
  code: string;
  display_name: string;
  status: string;
  row_version: number;
  version?: {
    id: string;
    version_number: number;
    status: string;
    currency: string;
    price_criterion: string;
    enabled_categories: string[];
  };
};

export type CostingCalculation = {
  id: string;
  kind: string;
  completeness: string;
  currency: string;
  total_amount: string | null;
  sellable_unit_amount: string | null;
  auto_published?: boolean;
  components?: Array<{ category: string; amount: string | null; quality: string; share_percent: string | null }>;
  gaps?: Array<{ code: string; message: string }>;
};

export type PricingSimulation = {
  id: string;
  kind: string;
  channel: string;
  suggested_price: string | null;
  warning: string | null;
  disclaimer: string;
};

export type PracticedPrice = {
  id: string;
  channel: string;
  amount: string;
  status: string;
  row_version: number;
  justification: string | null;
};
