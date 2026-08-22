import type {
  BoardCard,
  Envelope,
  MaterialsView,
  Me,
  Order,
  Page,
  Plan,
  PlanDetail,
  SheetIssue,
  StepsView,
  Traceability,
  WeighingsView,
} from "./types";

export const ORG_A = "11111111-1111-1111-1111-111111111111";
export const ORG_B = "22222222-2222-2222-2222-222222222222";
export const ORDER_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
export const PLAN_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
export const ISSUE_ID = "cccccccc-cccc-cccc-cccc-cccccccccccc";

export const meFixture: Me = {
  user_id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
  display_name: "Ana Padeiro",
  status: "active",
  selected_organization_id: ORG_A,
  associations: [
    {
      organization_id: ORG_A,
      display_name: "Padaria Central",
      slug: "padaria-central",
      roles: ["production_manager", "viewer"],
      status: "active",
      permissions: [
        "identity.read_me",
        "organization.read",
        "membership.read",
        "production.board.read",
        "production.plan.read",
        "production.order.read",
        "production.traceability.read",
      ],
    },
    {
      organization_id: ORG_B,
      display_name: "Atelier Norte",
      slug: "atelier-norte",
      roles: ["viewer"],
      status: "active",
      permissions: [
        "identity.read_me",
        "organization.read",
        "membership.read",
        "production.board.read",
        "production.plan.read",
        "production.order.read",
      ],
    },
  ],
  roles: ["production_manager", "viewer"],
  permissions: [
    "identity.read_me",
    "organization.read",
    "membership.read",
    "production.board.read",
    "production.plan.read",
    "production.order.read",
    "production.traceability.read",
  ],
};

export const boardFixture: BoardCard[] = [
  {
    order: {
      id: ORDER_ID,
      public_code: "OP-2026-0001",
      status: "in_progress",
      priority: 1,
      row_version: 4,
    },
    batches: [
      {
        id: "batch-1",
        production_order_id: ORDER_ID,
        sequence: 1,
        operational_code: "B1",
        target_mode: "mass",
        target_quantity: "12000",
        status: "in_progress",
        row_version: 2,
        planned_start_at: "2026-08-22T11:00:00+00:00",
        planned_end_at: "2026-08-22T14:00:00+00:00",
      },
    ],
    product: { id: "prod-1", code: "PAO-TRAD", display_name: "Pão tradicional" },
    quantity: "12000",
    target_mode: "mass",
    planned_start_at: "2026-08-22T11:00:00+00:00",
    planned_end_at: "2026-08-22T14:00:00+00:00",
    operational_date: "2026-08-22",
    shift: "morning",
    current_step: "Fermentação",
    dependencies: [],
    blocked: false,
    open_occurrences: 1,
    delayed: true,
    next_action: "complete_step",
    has_execution_facts: true,
  },
];

export const plansFixture: Page<Plan> = {
  items: [
    {
      id: PLAN_ID,
      public_code: "PL-2026-0008",
      establishment_id: "est-1",
      operational_date: "2026-08-22",
      shift: "morning",
      status: "scheduled",
      notes: null,
      row_version: 1,
      created_at: "2026-08-21T10:00:00+00:00",
      updated_at: "2026-08-21T10:00:00+00:00",
      scheduled_at: "2026-08-21T12:00:00+00:00",
    },
  ],
  next_cursor: null,
};

export const planDetailFixture: Envelope<PlanDetail> = {
  data: {
    ...plansFixture.items[0],
    items: [
      {
        id: "item-1",
        technical_product_id: "prod-1",
        target_mode: "mass",
        target_quantity: "12000",
        unit_weight_g: null,
        priority: 1,
        sort_order: 1,
        notes: null,
      },
    ],
  },
  row_version: 1,
};

export const ordersFixture: Page<Order> = {
  items: [
    {
      id: ORDER_ID,
      public_code: "OP-2026-0001",
      establishment_id: "est-1",
      plan_id: PLAN_ID,
      technical_product_id: "prod-1",
      target_mode: "mass",
      target_quantity: "12000",
      priority: 1,
      status: "in_progress",
      planned_start_at: "2026-08-22T11:00:00+00:00",
      planned_end_at: "2026-08-22T14:00:00+00:00",
      row_version: 4,
      materials_hash: "abc123",
      steps_hash: "def456",
      snapshot_hash: "ghi789",
    },
  ],
  next_cursor: null,
};

export const materialsFixture: Envelope<MaterialsView> = {
  data: {
    planned: [{ id: "mat-1", name: "Farinha de trigo", gross: "7000", unit: "g" }],
    actual: [
      {
        id: "bmat-1",
        planned_gross: "7000",
        weighed_canonical: "6998",
        consumption: { use: "6990", waste: "8" },
      },
    ],
  },
};

export const stepsFixture: Envelope<StepsView> = {
  data: {
    planned: [{ id: "step-1", title: "Fermentação", sequence: 1 }],
    actual: [{ id: "run-1", status: "in_progress" }],
  },
};

export const weighingsFixture: Envelope<WeighingsView> = {
  data: {
    entries: [
      {
        id: "w-1",
        entered_quantity: "7",
        entered_unit: "kg",
        canonical_quantity: "7000",
        canonical_unit: "g",
        conversion_factor: "1000",
        conversion_source: "unit_catalog",
        conversion_version: "1",
      },
    ],
    verifications: [{ id: "v-1", entry_id: "w-1", decision: "accepted" }],
  },
};

export const sheetFixture: Envelope<SheetIssue> = {
  data: {
    id: ISSUE_ID,
    issue_number: 2,
    purpose: "operational",
    order_status_at_issue: "in_progress",
    previous_issue_id: "prev-issue",
    payload_sha256: "fff111",
    canonical_payload: {
      schema_version: "1",
      order: {
        id: ORDER_ID,
        public_code: "OP-2026-0001",
        status: "in_progress",
        target_mode: "mass",
        target_quantity: "12000",
        materials_hash: "abc123",
        steps_hash: "def456",
        snapshot_hash: "ghi789",
        policy_hash: "pol999",
      },
      policy: { algorithm_code: "weighing.v1", algorithm_version: "1" },
      materials: [{ sequence: 1, name: "Farinha de trigo", unit: "g", gross: "7000", net: "7000" }],
      steps: [{ sequence: 1, title: "Fermentação", instructions: "Manter 24 °C por 60 min" }],
      batches: [{ sequence: 1, operational_code: "B1", target: "12000", status: "in_progress" }],
    },
  },
};

export const cancelledSheetFixture: Envelope<SheetIssue> = {
  data: {
    ...sheetFixture.data,
    order_status_at_issue: "cancelled",
    previous_issue_id: "prev-issue",
  },
};

export const traceFixture: Envelope<Traceability> = {
  data: {
    order: {
      id: ORDER_ID,
      public_code: "OP-2026-0001",
      status: "in_progress",
      formulation_version_id: "form-1",
      scale_calculation_id: "scale-1",
      materials_hash: "abc123",
      steps_hash: "def456",
      snapshot_hash: "ghi789",
      policy_hash: "pol999",
    },
    batches: [{ id: "batch-1", operational_code: "B1", status: "in_progress" }],
    planned_materials: [{ id: "mat-1", name: "Farinha de trigo", gross: "7000", unit: "g" }],
    planned_steps: [{ id: "step-1", title: "Fermentação" }],
    actual_materials: [
      {
        batch_material_id: "bmat-1",
        planned_gross: "7000",
        weighed_canonical: "6998",
        consumption: { use: "6990" },
      },
    ],
    weighings: [
      {
        id: "w-1",
        lot_code: "L-88",
        operator_user_id: "op-1",
        entered_quantity: "7",
        entered_unit: "kg",
        canonical_quantity: "7000",
        canonical_unit: "g",
        conversion_factor: "1000",
        conversion_source: "unit_catalog",
        conversion_version: "1",
      },
    ],
    verifications: [
      { id: "v-1", entry_id: "w-1", decision: "accepted", verifier_user_id: "op-2" },
    ],
    consumptions: [
      {
        id: "c-1",
        type: "use",
        entered_quantity: "6990",
        entered_unit: "g",
        canonical_quantity: "6990",
        canonical_unit: "g",
        conversion_factor: "1",
        conversion_source: "unit_catalog",
        conversion_version: "1",
      },
    ],
    step_runs: [{ id: "run-1", status: "in_progress", operator_user_id: "op-1" }],
    yields: [{ id: "y-1", type: "actual", quantity: "11800" }],
    occurrences: [{ id: "o-1", category: "delay", status: "open" }],
    dependencies: [],
    overrides: [],
    sheet_issues: [{ id: ISSUE_ID, issue_number: 2, payload_sha256: "fff111" }],
    events: [
      {
        id: "e-1",
        type: "order.released",
        command: "release_order",
        occurred_at: "2026-08-22T10:00:00+00:00",
      },
    ],
  },
};
