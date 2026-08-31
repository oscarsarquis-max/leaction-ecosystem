import type {
  BoardCard,
  BoardContextCatalog,
  Catalog,
  Envelope,
  ExecutionView,
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
        "ingredient.read",
        "ingredient.create",
        "ingredient.update_draft",
        "ingredient.publish",
        "supplier.read",
        "supplier.manage",
        "supplier.price.record",
        "recipe.read",
        "recipe.create",
        "recipe.update_draft",
        "recipe.version.create",
        "recipe.scale",
        "recipe.trial.manage",
        "recipe.review",
        "recipe.approve",
        "recipe.publish",
        "recipe.retire",
        "recipe.reference.manage",
        "recipe.technical_sheet.read",
        "recipe.ai.propose",
        "recipe.ai.review",
        "recipe.ai.materialize",
        "product.read",
        "product.create",
        "product.update",
        "product.activate",
        "product.family.manage",
        "labeling.read",
        "labeling.dossier.create",
        "labeling.evaluate",
        "labeling.candidate.edit",
        "labeling.review",
        "labeling.render",
        "labeling.invalidate",
        "regulatory.source.read",
        "costing.read",
        "costing.policy.manage",
        "costing.assumption.manage",
        "costing.calculate.planned",
        "costing.calculate.actual",
        "pricing.simulation.manage",
        "pricing.review",
        "pricing.publish",
        "reporting.dashboard.read",
        "reporting.production.read",
        "reporting.traceability.read",
        "reporting.costing.read",
        "reporting.pricing.read",
        "reporting.compliance.read",
        "reporting.data_quality.read",
        "reporting.snapshot.create",
        "reporting.export",
        "reporting.saved_view.manage",
        "reporting.inventory.read",
        "inventory.read",
        "inventory.policy.manage",
        "inventory.item.manage",
        "inventory.lot.manage",
        "inventory.reserve",
        "inventory.separate",
        "inventory.move",
        "inventory.adjust",
        "inventory.count",
        "inventory.count.approve",
        "inventory.expired.override",
        "procurement.read",
        "procurement.requisition.create",
        "procurement.requisition.approve",
        "procurement.quotation.manage",
        "procurement.order.manage",
        "procurement.order.approve",
        "procurement.receive",
        "procurement.return",
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
        "ingredient.read",
        "supplier.read",
        "recipe.read",
        "recipe.technical_sheet.read",
        "product.read",
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
    "ingredient.read",
    "ingredient.create",
    "ingredient.update_draft",
    "ingredient.publish",
    "supplier.read",
    "supplier.manage",
    "supplier.price.record",
    "recipe.read",
    "recipe.create",
    "recipe.update_draft",
    "recipe.version.create",
    "recipe.scale",
    "recipe.trial.manage",
    "recipe.review",
    "recipe.approve",
    "recipe.publish",
    "recipe.retire",
    "recipe.reference.manage",
    "recipe.technical_sheet.read",
    "recipe.ai.propose",
    "recipe.ai.review",
    "recipe.ai.materialize",
    "product.read",
    "product.create",
    "product.update",
    "product.activate",
    "product.family.manage",
    "labeling.read",
    "labeling.dossier.create",
    "labeling.evaluate",
    "labeling.candidate.edit",
    "labeling.review",
    "labeling.render",
    "labeling.invalidate",
    "regulatory.source.read",
    "costing.read",
    "costing.policy.manage",
    "costing.assumption.manage",
    "costing.calculate.planned",
    "costing.calculate.actual",
    "pricing.simulation.manage",
    "pricing.review",
    "pricing.publish",
    "reporting.dashboard.read",
    "reporting.production.read",
    "reporting.traceability.read",
    "reporting.costing.read",
    "reporting.pricing.read",
    "reporting.compliance.read",
    "reporting.data_quality.read",
    "reporting.snapshot.create",
    "reporting.export",
    "reporting.saved_view.manage",
    "reporting.inventory.read",
    "inventory.read",
    "inventory.policy.manage",
    "inventory.item.manage",
    "inventory.lot.manage",
    "inventory.reserve",
    "inventory.separate",
    "inventory.move",
    "inventory.adjust",
    "inventory.count",
    "inventory.count.approve",
    "inventory.expired.override",
    "procurement.read",
    "procurement.requisition.create",
    "procurement.requisition.approve",
    "procurement.quotation.manage",
    "procurement.order.manage",
    "procurement.order.approve",
    "procurement.receive",
    "procurement.return",
  ],
};

export const POLICY_ID = "c0c0c0c0-c0c0-c0c0-c0c0-c0c0c0c0c0c0";
export const CALC_ID = "c1c1c1c1-c1c1-c1c1-c1c1-c1c1c1c1c1c1";
export const SIM_ID = "c2c2c2c2-c2c2-c2c2-c2c2-c2c2c2c2c2c2";
export const PRICE_ID = "c3c3c3c3-c3c3-c3c3-c3c3-c3c3c3c3c3c3";

export const costingPolicyFixture = {
  id: POLICY_ID,
  code: "POL-1",
  display_name: "Custeio padrão",
  status: "published",
  row_version: 2,
  version: {
    id: "c4c4c4c4-c4c4-c4c4-c4c4-c4c4c4c4c4c4",
    version_number: 1,
    status: "published",
    currency: "BRL",
    price_criterion: "latest_observed",
    enabled_categories: ["ingredient", "waste"],
  },
};

export const costingCalculationFixture = {
  id: CALC_ID,
  kind: "planned",
  completeness: "partial",
  currency: "BRL",
  total_amount: "12.50",
  sellable_unit_amount: null,
  auto_published: false,
  components: [{ category: "ingredient", amount: "12.50", quality: "current_price", share_percent: "100" }],
  gaps: [{ code: "rendimento_ausente", message: "Sem rendimento vendável confiável." }],
};

export const pricingSimulationFixture = {
  id: SIM_ID,
  kind: "markup_factor",
  channel: "own_counter",
  suggested_price: "25.00",
  warning: "Simulação sobre cálculo parcial. Publicação exige confirmação reforçada.",
  disclaimer: "Preço sugerido não é preço publicado.",
};

export const practicedPriceFixture = {
  id: PRICE_ID,
  channel: "own_counter",
  amount: "25.00",
  status: "draft",
  row_version: 1,
  justification: "revisão humana",
};

export const PRODUCT_ID = "a1a1a1a1-a1a1-4a1a-8a1a-a1a1a1a1a1a1";
export const PRODUCT_PURCHASED_ID = "a2a2a2a2-a2a2-4a2a-8a2a-a2a2a2a2a2a2";
export const PRODUCT_FAMILY_ID = "a3a3a3a3-a3a3-4a3a-8a3a-a3a3a3a3a3a3";

export const productFamilyFixture = {
  id: PRODUCT_FAMILY_ID,
  code: "FAM-PAES",
  display_name: "Pães",
  description: null,
  status: "active",
  parent_id: null,
  row_version: 1,
};

export const productFixture = {
  id: PRODUCT_ID,
  code: "PAO-TRAD",
  display_name: "Pão tradicional",
  description: "Pão de casca fina para o balcão.",
  status: "active",
  purpose: "final",
  supply_mode: "produced",
  family: {
    id: PRODUCT_FAMILY_ID,
    code: "FAM-PAES",
    display_name: "Pães",
    status: "active",
  },
  has_published_recipe: false,
  recipe_status_label: "Sem receita vigente",
  stock_unit: { id: "u1", code: "g", display_name: "grama" },
  sale_unit: { id: "u1", code: "g", display_name: "grama" },
  net_content: "500",
  net_content_unit: { id: "u1", code: "g", display_name: "grama" },
  default_shelf_life_days: 3,
  packaging_description: "Saco de papel",
  row_version: 1,
  created_at: "2026-08-24T10:00:00+00:00",
  updated_at: "2026-08-24T10:00:00+00:00",
  links: { recipes_count: 0, orders_count: 1 },
  operational_notes: [
    "Cadastro válido sem receita; produção fica bloqueada até haver receita vigente.",
  ],
};

export const productPurchasedFixture = {
  ...productFixture,
  id: PRODUCT_PURCHASED_ID,
  code: "REF-COLA",
  display_name: "Refrigerante de cola",
  description: null,
  purpose: "final",
  supply_mode: "purchased",
  family: null,
  has_published_recipe: false,
  recipe_status_label: "Não se aplica",
  net_content: "350",
  default_shelf_life_days: 180,
  packaging_description: "Lata",
  links: { recipes_count: 0, orders_count: 0 },
  operational_notes: [
    "Recebimento e estoque de mercadoria serão completados no próximo ciclo.",
  ],
};

export const productSummaryFixture = {
  total: 2,
  active: 2,
  purchased: 1,
  intermediate: 0,
  produced_without_recipe: 1,
};

export const INVENTORY_LOCATION_ID = "b0b0b0b0-b0b0-4b0b-8b0b-b0b0b0b0b0b0";
export const FISCAL_DOCUMENT_ID = "b1b1b1b1-b1b1-4b1b-8b1b-b1b1b1b1b1b1";
export const FISCAL_DOCUMENT_DIVERGENT_ID = "b2b2b2b2-b2b2-4b2b-8b2b-b2b2b2b2b2b2";

/** Espelha o serializador de `/fiscal/documents/{id}`: sem código público e sem rótulo de alvo. */
export const fiscalDocumentFixture = {
  id: FISCAL_DOCUMENT_ID,
  public_code: null,
  document_number: "104532",
  series: "1",
  access_key: "35260812345678000190550010001045321234567890",
  issued_on: "2026-08-28",
  status: "awaiting_check",
  status_label: "Aguardando conferência",
  origin: "xml",
  supplier: {
    id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
    display_name: "Moinho Demo",
    tax_id: "12345678000190",
    registered: true,
  },
  item_count: 2,
  matched_item_count: 1,
  checked_item_count: 0,
  divergence_count: 0,
  received_at: null,
  updated_at: "2026-08-29T09:10:00+00:00",
  document_total: "742.50",
  currency: "BRL",
  cost_access: true,
  costs: {
    currency: "BRL",
    items_total: "700.00",
    freight_total: "42.50",
    discount_total: "0.00",
    taxes_total: "58.10",
    document_total: "742.50",
  },
  storage_location_label: null,
  stock_applied: false,
  stock_summary: "Estoque ainda não atualizado: falta conferir o que chegou.",
  next_action: "record_physical",
  next_action_label: "Registrar o que realmente chegou na doca.",
  pending_reasons: [
    "Há itens sem correspondência com o cadastro da Panne.",
    "Há itens sem conferência física.",
  ],
  operational_notes: [],
  row_version: 3,
  items: [
    {
      id: "fi-1",
      sequence: 1,
      supplier_description: "Farinha de trigo tipo 1 saco 25 kg",
      supplier_sku: "SKU-FAR-25",
      invoiced_quantity: "40",
      unit_code: "kg",
      match: {
        status: "matched",
        target_kind: "ingredient",
        target_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
        target_label: null,
        suggestion_reason: null,
      },
      physical: null,
      unit_cost: "13.00",
      total_cost: "520.00",
    },
    {
      id: "fi-2",
      sequence: 2,
      supplier_description: "Açúcar cristal saco 25 kg",
      supplier_sku: "SKU-ACU-25",
      invoiced_quantity: "10",
      unit_code: "kg",
      match: {
        status: "suggested",
        target_kind: "ingredient",
        target_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeef",
        target_label: null,
        suggestion_reason: null,
      },
      physical: null,
      unit_cost: "18.00",
      total_cost: "180.00",
    },
  ],
  attachments: [
    { id: "fa-1", kind: "xml", filename: "nfe-104532.xml", uploaded_at: "2026-08-29T09:00:00+00:00" },
  ],
  history: [
    {
      id: "fh-1",
      occurred_at: "2026-08-29T09:00:00+00:00",
      action: "fiscal.document.xml_imported",
      action_label: "XML importado",
      actor_label: "Ana Padeiro",
      detail: null,
    },
    {
      id: "fh-2",
      occurred_at: "2026-08-29T09:10:00+00:00",
      action: "fiscal.document.match_confirmed",
      action_label: "Correspondência confirmada",
      actor_label: "Ana Padeiro",
      detail: null,
    },
  ],
};

/** Mesmo documento visto por um perfil sem leitura de valores: a API omite todo custo. */
export const fiscalDocumentNoCostFixture = {
  ...fiscalDocumentFixture,
  document_total: null,
  currency: null,
  cost_access: false,
  costs: null,
  items: fiscalDocumentFixture.items.map((item) => ({
    ...item,
    unit_cost: null,
    total_cost: null,
  })),
};

export const fiscalDocumentDivergentFixture = {
  ...fiscalDocumentFixture,
  id: FISCAL_DOCUMENT_DIVERGENT_ID,
  public_code: null,
  document_number: "990117",
  series: "2",
  status: "divergent",
  status_label: "Com divergência",
  origin: "manual",
  supplier: {
    id: null,
    display_name: "Laticínio Demo",
    tax_id: "98765432000155",
    registered: false,
  },
  matched_item_count: 2,
  checked_item_count: 2,
  divergence_count: 1,
  stock_applied: false,
  next_action: "resolve_divergence",
  next_action_label: "Resolver a divergência apontada na conferência.",
};

export const fiscalSummaryFixture = {
  total: 2,
  awaiting_match: 0,
  awaiting_check: 1,
  partially_received: 0,
  divergent: 1,
  confirmed: 0,
};

export const RECIPE_ID = "99999999-9999-9999-9999-999999999999";
export const RECIPE_VERSION_ID = "88888888-8888-8888-8888-888888888888";
export const PROPOSAL_ID = "77777777-7777-7777-7777-777777777777";
export const DOSSIER_ID = "55555555-5555-5555-5555-555555555555";

export const labelingDossierFixture = {
  id: DOSSIER_ID,
  status: "evaluated",
  formulation_id: RECIPE_ID,
  formulation_version_id: RECIPE_VERSION_ID,
  row_version: 2,
  disclaimer: "Proposta técnica para revisão. Não é declaração de conformidade.",
  certified: false,
  conforme_anvisa: false,
  formulation: { id: RECIPE_ID, code: "REC-PAO", display_name: "Pão francês" },
  formulation_version: { id: RECIPE_VERSION_ID, version_number: 2 },
  created_at: "2026-08-24T10:00:00+00:00",
  profile: {
    completeness: "complete",
    jurisdiction: "BR",
    packed_food: true,
    packed_away_from_consumer: true,
    packed_at_point_of_sale: null,
    packed_on_request: null,
    same_establishment: null,
    sales_channel: "retail",
    food_service: null,
    physical_state: "solid",
    ready_to_eat: true,
    regulatory_category_code: "pao",
    category_confirmed: true,
    net_content_g: "50.000000",
  },
  versions: [
    { id: "v1", version_number: 1, status: "evaluated", content_hash: "aaa" },
    { id: "v2", version_number: 2, status: "evaluated", content_hash: "bbb" },
  ],
  current: {
    version: { id: "v2", version_number: 2, status: "evaluated", content_hash: "bbb" },
    assessment: {
      status: "evaluated",
      proposal_summary: "Proposta técnica para revisão humana. Não é declaração de conformidade.",
    },
    findings: [
      {
        rule_code: "fop_added_sugars",
        result: "fail",
        fact: "limite da lupa",
        expected_value: ">= 15",
        found_value: "16",
        source_code: "in-75-2020",
        source_locator: "Anexo XV IN 75",
        explanation: "Ausência de nutriente não presume ausência de lupa.",
        action_needed: true,
      },
      {
        rule_code: "gluten_contains",
        result: "manual_review_required",
        fact: "gluten",
        expected_value: null,
        found_value: "contém Glúten",
        source_code: "lei-10674-2003",
        source_locator: "Lei 10.674/2003",
        explanation: "Presença declarada de glúten exige conferência humana.",
        action_needed: true,
      },
      {
        rule_code: "may_contain",
        result: "insufficient_evidence",
        fact: "cross_contact",
        expected_value: null,
        found_value: null,
        source_code: "rdc-727-2022",
        source_locator: "RDC 727/2022",
        explanation: "PODE CONTER exige evidência de processo ou instalações.",
        action_needed: true,
      },
      {
        rule_code: "lactose",
        result: "insufficient_evidence",
        fact: "lactose",
        expected_value: null,
        found_value: null,
        source_code: "rdc-727-2022",
        source_locator: "RDC 727/2022",
        explanation: "Lactose sem evidência suficiente.",
        action_needed: true,
      },
    ],
    nutrition: {
      portion_g: "50.000000",
      household_measure: "1 unidade",
      footnotes: ["Valores declarados são projeção regulatória, não certificado."],
      lines: [
        {
          nutrient_code: "energy_kcal",
          technical_per_100g: "280",
          declared_per_100g: "280",
          declared_per_serving: "140",
          daily_value_percent: "14",
          completeness: "complete",
          presented: "280",
        },
        {
          nutrient_code: "added_sugars",
          technical_per_100g: null,
          declared_per_100g: null,
          declared_per_serving: null,
          daily_value_percent: null,
          completeness: "insufficient_evidence",
          presented: null,
        },
      ],
    },
    front_of_pack: {
      added_sugars_result: "insufficient_evidence",
      saturated_fat_result: "below",
      sodium_result: "below",
      magnifier_required: null,
      nutrients_high: [],
      compared: { thresholds: { added_sugars: "15", saturated_fat: "6", sodium: "600" } },
      disclaimer: "Representação candidata da lupa. Não é arte-final certificada.",
    },
    ingredients: [{ sequence: 1, display_name: "Farinha de trigo", compound: false, components: [], gap: null }],
    warnings: [
      {
        code: "gluten_unknown",
        statement: "Declaração de glúten pendente. Ausência na fórmula não prova ausência.",
        result: "insufficient_evidence",
      },
    ],
    mandatory: [
      { code: "lote", label: "Lote", value: null, status: "pending", claim: false },
      { code: "lista_ingredientes", label: "Lista de ingredientes", value: "lista gerada", status: "filled", claim: false },
    ],
    candidate: {
      watermark: "Proposta técnica para revisão",
      payload_sha256: "bbb",
      payload: { title: "Pão francês", disclaimer: "Candidato para conferência." },
    },
    reviews: [],
  },
};

export const proposalFixture = {
  id: PROPOSAL_ID,
  intent: "create_recipe" as const,
  title: "Pão de teste assistivo",
  objective_summary: "Criar pão com farinha de trigo",
  status: "draft",
  status_label: "aguardando revisão",
  assisted_by_ai: true,
  base_formulation_version_id: null,
  materialized_formulation_version_id: null,
  warnings: ["Sugestão assistiva da Panne; não é formulação oficial, aprovada ou publicada."],
  missing_data: [],
  row_version: 1,
  items: [
    {
      id: "pi1",
      sequence: 1,
      ingredient_version_id: "ffffffff-ffff-ffff-ffff-ffffffffffff",
      proposed_ingredient_name: "Farinha",
      resolution_status: "resolved",
      net_quantity_g: "100",
      rationale: "Sugestão a partir da evidência.",
    },
  ],
  steps: [{ sequence: 1, title: "Misturar", instructions: "Misturar os ingredientes sugeridos." }],
  citations: [{ id: "c1", claim_path: "items[1].rationale" }],
  changes: [
    {
      change_key: "added:ffffffff-ffff-ffff-ffff-ffffffffffff",
      change_kind: "added" as const,
      path: "items[1]",
      before_value: null,
      after_value: { name: "Farinha", net_quantity_g: "100" },
      decision: "pending" as const,
    },
  ],
  materialized: null,
  guided_input: { objective: "Criar pão com farinha de trigo" },
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
  {
    order: {
      id: "order-ready",
      public_code: "OP-2026-0002",
      status: "ready",
      priority: 2,
      row_version: 1,
    },
    batches: [],
    product: { id: "prod-2", code: "BROA", display_name: "Broa de milho" },
    quantity: "4000",
    target_mode: "mass",
    planned_start_at: "2026-08-22T12:00:00+00:00",
    planned_end_at: "2026-08-22T13:00:00+00:00",
    operational_date: "2026-08-22",
    shift: "morning",
    current_step: "Fornos",
    dependencies: [],
    blocked: true,
    open_occurrences: 1,
    delayed: false,
    next_action: "start_step",
    has_execution_facts: false,
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
      item_count: 1,
      items_summary: "Pão francês",
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
        priority: 50,
        sort_order: 1,
        notes: null,
        product: { id: "prod-1", code: "PAO-FR", display_name: "Pão francês" },
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
      product: { id: "prod-1", code: "PAO-TRAD", display_name: "Pão tradicional" },
      plan: { id: PLAN_ID, public_code: "PL-2026-0008" },
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
      schema_version: "2",
      establishment: { id: "est-1", code: "E1", display_name: "Padaria Central" },
      organization: { id: ORG_A, slug: "padaria-central", display_name: "Padaria Central" },
      issuer: { user_id: meFixture.user_id, display_name: "Ana Padeiro", issued_at: "2026-08-23T12:00:00+00:00" },
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

export const boardContextFixture: Envelope<BoardContextCatalog> = {
  data: {
    establishments: [{ id: "est-1", code: "E1", display_name: "Padaria Central" }],
    shifts: [
      { code: "morning", label: "Manhã" },
      { code: "afternoon", label: "Tarde" },
      { code: "night", label: "Noite" },
    ],
    areas: [
      { code: "fornos", label: "Fornos" },
      { code: "masseira", label: "Masseira" },
      { code: "bancada", label: "Bancada" },
      { code: "embalagem", label: "Embalagem" },
    ],
  },
};

export const catalogFixture: Envelope<Catalog> = {
  data: {
    mass_units: [
      { id: "unit-g", code: "g", name: "grama", symbol: "g", dimension: "mass" },
      { id: "unit-kg", code: "kg", name: "quilograma", symbol: "kg", dimension: "mass" },
    ],
    yield_types: [
      "pre_bake_mass",
      "post_bake_mass",
      "good_units",
      "rejected_units",
      "leftover",
      "scrap",
    ],
    occurrence_categories: ["quality", "material", "time"],
    occurrence_severities: ["low", "medium", "high", "critical"],
    consumption_types: ["consume", "return", "waste", "correction"],
    verification_decisions: ["accepted", "rejected"],
    sheet_purposes: ["operational", "contingency"],
    weighing_policies: ["required"],
    verification_policies: ["second_person"],
    order_statuses: ["in_progress", "completed", "short_closed"],
    batch_statuses: ["in_progress"],
    step_statuses: ["pending", "in_progress", "completed"],
  },
};

export const COSTING_PERMS = [
  "costing.read",
  "costing.policy.manage",
  "costing.assumption.manage",
  "costing.calculate.planned",
  "costing.calculate.actual",
  "pricing.simulation.manage",
  "pricing.review",
  "pricing.publish",
] as const;

export const operatorMeFixture: Me = {
  ...meFixture,
  associations: meFixture.associations.map((item, index) =>
    index === 0
      ? {
          ...item,
          roles: ["baker_operator"],
          permissions: [
            ...item.permissions.filter(
              (code) =>
                !code.startsWith("costing.") &&
                !code.startsWith("pricing.") &&
                !code.startsWith("procurement.") &&
                !(code.startsWith("product.") && code !== "product.read") &&
                !(code.startsWith("inventory.") && !["inventory.read", "inventory.separate"].includes(code)) &&
                !["reporting.dashboard.read", "reporting.costing.read", "reporting.pricing.read", "reporting.inventory.read"].includes(code),
            ),
            "production.weighing.record",
            "production.weighing.verify",
            "production.consumption.record",
            "production.step.execute",
            "production.occurrence.record",
            "production.occurrence.resolve",
            "production.order.complete",
            "production.order.short_close",
            "production.sheet.issue",
          ],
        }
      : item,
  ),
  permissions: [
    ...meFixture.permissions.filter(
      (code) =>
        !code.startsWith("costing.") &&
        !code.startsWith("pricing.") &&
        !code.startsWith("procurement.") &&
        !(code.startsWith("product.") && code !== "product.read") &&
        !(code.startsWith("inventory.") && !["inventory.read", "inventory.separate"].includes(code)) &&
        !["reporting.dashboard.read", "reporting.costing.read", "reporting.pricing.read", "reporting.inventory.read"].includes(code),
    ),
    "production.weighing.record",
    "production.weighing.verify",
    "production.consumption.record",
    "production.step.execute",
    "production.occurrence.record",
    "production.occurrence.resolve",
    "production.order.complete",
    "production.order.short_close",
    "production.sheet.issue",
  ],
};

export const executionFixture: Envelope<ExecutionView> = {
  data: {
    viewer: {
      user_id: meFixture.user_id,
      display_name: "Ana Padeiro",
      permissions: operatorMeFixture.permissions,
    },
    order: ordersFixture.items[0],
    product: { id: "prod-1", code: "PAO-TRAD", display_name: "Pão tradicional" },
    establishment: { id: "est-1", code: "E1", display_name: "Padaria Central" },
    policy: {
      verification_policy: "second_person",
      require_manual_lot: false,
      completion_tolerance: "5",
    },
    batches: [
      {
        ...boardFixture[0].batches[0],
        materials: [
          {
            id: "bmat-1",
            batch_id: "batch-1",
            name: "Farinha de trigo",
            measurement_unit_id: "unit-g",
            unit: "g",
            planned_gross: "7000",
            weighed_canonical: "6998",
            weigh_state: "awaiting_verification",
            consumption: { consume: "0", return: "0", waste: "0", net: "0" },
          },
        ],
        sessions: [{ id: "sess-1", status: "open", row_version: 1, opened_by_user_id: meFixture.user_id }],
        weighings: [
          {
            id: "w-1",
            session_id: "sess-1",
            batch_material_id: "bmat-1",
            entry_type: "record",
            measurement_unit_id: "unit-kg",
            operator_user_id: meFixture.user_id,
            operator_name: "Ana Padeiro",
            lot_code: "L-88",
            justification: null,
            planned_quantity: "7000",
            absolute_difference: "2",
            percent_difference: "0.03",
            within_tolerance: false,
            verification: null,
            entered_quantity: "7",
            entered_unit: "kg",
            canonical_quantity: "7000",
            canonical_unit: "g",
            conversion_factor: "1000",
            conversion_source: "unit_catalog",
            conversion_version: "1",
          },
        ],
        steps: [
          {
            order_step_id: "step-1",
            batch_id: "batch-1",
            title: "Fermentação",
            instructions: "Manter 24 °C",
            sequence: 1,
            duration_seconds: 3600,
            temperature_value: "24",
            temperature_unit: "C",
            execution_id: "run-1",
            status: "in_progress",
            row_version: 2,
            operator_user_id: meFixture.user_id,
            operator_name: "Ana Padeiro",
            started_at: "2026-08-23T12:00:00.000Z",
            ended_at: null,
            measured_duration_seconds: null,
            measured_temperature: null,
            notes: null,
          },
          {
            order_step_id: "step-2",
            batch_id: "batch-1",
            title: "Fornada",
            instructions: "Assar até dourar",
            sequence: 2,
            duration_seconds: 1200,
            temperature_value: "220",
            temperature_unit: "C",
            execution_id: null,
            status: "pending",
            row_version: null,
            operator_user_id: null,
            operator_name: null,
            started_at: null,
            ended_at: null,
            measured_duration_seconds: null,
            measured_temperature: null,
            notes: null,
          },
        ],
        yields: [{ id: "y-1", type: "pre_bake_mass", quantity: "11800", unit: "g", measurement_unit_id: "unit-g", notes: null }],
        yield_projection: {
          final_mass: "11800",
          sellable_units: null,
          rejected_units: null,
          leftover: null,
          scrap: null,
          loss_absolute: null,
          loss_percent: null,
          target_deviation: "-200",
          completeness: "complete",
          within_tolerance: true,
        },
      },
    ],
    occurrences: [
      {
        id: "o-1",
        category: "quality",
        severity: "high",
        status: "open",
        description: "Crosta irregular",
        is_blocking: true,
        batch_id: "batch-1",
        order_step_id: "step-1",
      },
    ],
    dependencies: [],
    sheets: [{ id: ISSUE_ID, issue_number: 2, payload_sha256: "fff111", purpose: "operational", previous_issue_id: "prev-issue" }],
    blocked: true,
    open_session: true,
    next_action: "complete_step",
    readiness: {
      weighing: { ok: false, reason: "pesagem incompleta" },
      verifications: { ok: false, reason: "aguardando conferência por outro usuário" },
      steps: { ok: false, reason: "etapas incompletas" },
      consumptions: { ok: false, reason: "consumo mínimo ausente" },
      yields: { ok: true, reason: null },
      dependencies: { ok: true, reason: null },
      blocking_occurrences: { ok: false, reason: "ocorrência bloqueante aberta" },
      permissions: {
        complete: true,
        short_close: true,
        weighing_record: true,
        weighing_verify: true,
        consumption: true,
        step: true,
        occurrence_record: true,
        occurrence_resolve: true,
        batch_complete: true,
        sheet: true,
      },
    },
    updated_at: "2026-08-23T12:10:00.000Z",
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

export const SNAPSHOT_ID = "d0d0d0d0-d0d0-d0d0-d0d0-d0d0d0d0d0d0";

export const reportingPayloadFixture = {
  report_code: "executive",
  report_version: "1",
  data_cutoff_at: "2026-08-24T15:00:00+00:00",
  completeness: "partial",
  content_hash: "abc123def456",
  not_realtime: true,
  indicators: [
    {
      code: "orders_by_status",
      name: "Ordens por estado",
      status: "available",
      value: "3",
      unit: "count",
      coverage: { universe: 3, valid_count: 3, missing_count: 0 },
      by_group: { planned: 1, released: 0, in_execution: 1, completed: 1, short_closed: 0, cancelled: 0 },
    },
    {
      code: "normal_completion_rate",
      name: "Taxa de conclusão normal",
      status: "unavailable",
      value: null,
      reason: "conjunto_vazio",
      coverage: { universe: 0, valid_count: 0, missing_count: 0 },
    },
    {
      code: "cost_variance",
      name: "Variação de custo",
      status: "unavailable",
      value: null,
      reason: "par_previsto_realizado_ausente",
    },
  ],
  tables: [{ code: "orders", rows: [{ id: ORDER_ID, public_code: "OP-1", status: "draft", include: "ancora_no_periodo" }] }],
  gaps: [{ domain: "ingredient_price", id: "ing-1", reason: "sem_preco_vigente" }],
  impossible: ["faturamento", "vendas", "lucro_liquido"],
};

export const reportingSnapshotFixture = {
  id: SNAPSHOT_ID,
  execution_id: "e0e0e0e0-e0e0-e0e0-e0e0-e0e0e0e0e0e0",
  content_hash: "abc123def456",
  created_at: "2026-08-24T15:00:00+00:00",
  auto_recalculated: false,
  payload: reportingPayloadFixture,
};

export const reportingViewFixture = {
  id: "v0v0v0v0-v0v0-v0v0-v0v0-v0v0v0v0v0v0",
  code: "turno-manha",
  display_name: "Turno da manhã",
  report_code: "production",
  filters: { timezone: "America/Sao_Paulo" },
  row_version: 1,
};
