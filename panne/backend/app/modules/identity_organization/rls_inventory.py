"""Classificação de tabelas para RLS. Fonte da matriz e dos testes de inventário."""

ORGANIZATIONAL_TABLES = frozenset(
    {
        "establishment",
        "organization_membership",
        "ingredient",
        "ingredient_version",
        "ingredient_composition",
        "ingredient_nutrient",
        "ingredient_allergen",
        "supplier",
        "supplier_item",
        "technical_product",
        "recipe_reference",
        "formulation",
        "formulation_recipe_reference",
        "formulation_version",
        "formulation_item",
        "process_step",
        "scale_calculation",
        "scale_calculation_item",
        "trial",
        "trial_measurement",
        "approval",
        "nutrition_calculation",
        "nutrition_calculation_item",
        "calculation_evidence",
        "ai_interaction",
        "ai_proposal",
        "ai_proposal_item",
        "ai_proposal_process_step",
        "ai_proposal_citation",
        "ai_proposal_review",
        "compliance_profile",
        "compliance_assessment",
        "compliance_finding",
        "compliance_evidence",
        "compliance_review",
    }
)

PRODUCTION_TABLES = frozenset(
    {
        "production_code_counter",
        "production_plan",
        "production_plan_item",
        "production_order",
        "production_order_dependency",
        "production_batch",
        "production_order_material",
        "production_order_step",
        "production_batch_material",
        "production_event",
    }
)

PRODUCTION_EXECUTION_TABLES = frozenset(
    {
        "production_execution_policy",
        "production_weighing_session",
        "production_weighing_entry",
        "production_weighing_verification",
        "production_material_consumption",
        "production_step_execution",
        "production_step_execution_event",
        "production_yield_measurement",
        "production_occurrence",
        "production_occurrence_event",
        "production_dependency_override",
        "production_sheet_issue",
    }
)

HYBRID_TABLES = frozenset(
    {
        "organization",
        "audit_event",
        "knowledge_source",
        "knowledge_source_version",
        "knowledge_fragment",
        "grounding_query",
        "nutrition_expectation_profile",
        "compliance_framework",
        "compliance_framework_version",
        "compliance_requirement",
        "compliance_requirement_source",
    }
)

INHERITED_TABLES = frozenset(
    {
        "supplier_item_price",
        "knowledge_source_tag",
        "nutrition_expectation_profile_item",
        "grounding_result",
        "grounding_citation",
    }
)

GLOBAL_TABLES = frozenset(
    {
        "measurement_unit",
        "unit_conversion",
        "nutrient_definition",
        "allergen",
        "data_source",
        "knowledge_tag",
        "permission",
        "role_permission",
    }
)

IDENTITY_TABLES = frozenset({"app_user", "auth_identity"})
MEMBERSHIP_ROLE_TABLES = frozenset({"organization_membership_role"})
INGREDIENT_HTTP_TABLES = frozenset({"ingredient_command"})
FORMULATION_HTTP_TABLES = frozenset({"formulation_command"})
RECIPE_AI_TABLES = frozenset(
    {
        "formulation_version_recipe_reference",
        "ai_proposal_change",
    }
)
LABELING_TABLES = frozenset(
    {
        "labeling_dossier",
        "labeling_applicability_profile",
        "labeling_dossier_version",
        "labeling_assessment",
        "labeling_finding",
        "labeling_evidence",
        "labeling_review",
        "labeling_nutrition_candidate",
        "labeling_nutrition_line",
        "labeling_front_of_pack",
        "labeling_ingredient_candidate",
        "labeling_warning_candidate",
        "labeling_mandatory_item",
        "labeling_label_candidate",
        "labeling_invalidation",
        "labeling_command",
    }
)
COSTING_TABLES = frozenset(
    {
        "costing_policy",
        "costing_policy_version",
        "costing_assumption",
        "costing_calculation",
        "costing_component",
        "costing_evidence",
        "costing_gap",
        "costing_invalidation",
        "pricing_simulation",
        "pricing_simulation_component",
        "pricing_decision",
        "practiced_price",
        "costing_command",
    }
)
INVENTORY_TABLES = frozenset(
    {
        "inventory_policy",
        "inventory_policy_version",
        "inventory_location",
        "inventory_item",
        "inventory_lot",
        "inventory_movement",
        "inventory_balance",
        "inventory_reservation",
        "inventory_reservation_allocation",
        "inventory_pick",
        "inventory_pick_line",
        "inventory_consumption_posting",
        "inventory_count_session",
        "inventory_count_scope",
        "inventory_count_entry",
        "inventory_count_review",
        "inventory_replenishment_suggestion",
        "inventory_replenishment_item",
        "procurement_requisition",
        "procurement_requisition_item",
        "procurement_quotation",
        "procurement_quotation_item",
        "procurement_order",
        "procurement_order_revision",
        "procurement_order_item",
        "procurement_receipt",
        "procurement_receipt_item",
        "procurement_return",
        "inventory_command",
        "inventory_code_counter",
    }
)
REPORTING_TABLES = frozenset(
    {
        "reporting_saved_view",
        "reporting_dashboard_preference",
        "reporting_execution",
        "reporting_snapshot",
        "reporting_coverage_item",
        "reporting_export",
        "reporting_command",
    }
)

PRE_PRODUCTION_RLS_TABLES = (
    ORGANIZATIONAL_TABLES | HYBRID_TABLES | INHERITED_TABLES | GLOBAL_TABLES | IDENTITY_TABLES
)
RLS_TABLES = (
    PRE_PRODUCTION_RLS_TABLES
    | PRODUCTION_TABLES
    | PRODUCTION_EXECUTION_TABLES
    | MEMBERSHIP_ROLE_TABLES
    | INGREDIENT_HTTP_TABLES
    | FORMULATION_HTTP_TABLES
    | RECIPE_AI_TABLES
    | LABELING_TABLES
    | COSTING_TABLES
    | REPORTING_TABLES
    | INVENTORY_TABLES
)
UNMANAGED_TABLES = frozenset({"alembic_version"})
