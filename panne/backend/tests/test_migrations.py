from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from tests.conftest import postgres_url

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    "organization",
    "establishment",
    "app_user",
    "organization_membership",
    "audit_event",
    "measurement_unit",
    "unit_conversion",
    "nutrient_definition",
    "allergen",
    "data_source",
    "ingredient",
    "ingredient_version",
    "ingredient_composition",
    "ingredient_nutrient",
    "ingredient_allergen",
    "supplier",
    "supplier_item",
    "supplier_item_price",
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
    "knowledge_source",
    "knowledge_source_version",
    "knowledge_fragment",
    "knowledge_tag",
    "knowledge_source_tag",
    "grounding_query",
    "grounding_result",
    "grounding_citation",
    "nutrition_expectation_profile",
    "nutrition_expectation_profile_item",
    "ai_interaction",
    "ai_proposal",
    "ai_proposal_item",
    "ai_proposal_process_step",
    "ai_proposal_citation",
    "ai_proposal_review",
    "compliance_framework",
    "compliance_framework_version",
    "compliance_requirement",
    "compliance_requirement_source",
    "compliance_profile",
    "compliance_assessment",
    "compliance_finding",
    "compliance_evidence",
    "compliance_review",
    "auth_identity",
    "permission",
    "role_permission",
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

EXPECTED_0010 = set(EXPECTED)
EXPECTED_0011 = set(EXPECTED) | {
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
EXPECTED_0013 = set(EXPECTED_0011) | {"organization_membership_role"}
EXPECTED_0014 = set(EXPECTED_0013) | {"ingredient_command"}
EXPECTED_0015 = set(EXPECTED_0014) | {"formulation_command"}
EXPECTED_0016 = set(EXPECTED_0015) | {
    "formulation_version_recipe_reference",
    "ai_proposal_change",
}
EXPECTED = set(EXPECTED_0016) | {
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
EXPECTED_0017 = set(EXPECTED)
EXPECTED = set(EXPECTED_0017) | {
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
EXPECTED_0018 = set(EXPECTED)
EXPECTED = set(EXPECTED_0018) | {
    "reporting_saved_view",
    "reporting_dashboard_preference",
    "reporting_execution",
    "reporting_snapshot",
    "reporting_coverage_item",
    "reporting_export",
    "reporting_command",
}
EXPECTED_0019 = set(EXPECTED)
EXPECTED = set(EXPECTED_0019) | {
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
EXPECTED_0020 = set(EXPECTED)
EXPECTED = set(EXPECTED_0020) | {"product_family"}
EXPECTED = set(EXPECTED) | {"pricing_markup_policy", "pricing_economic_audit"}


def _upgrade(engine: Engine, revision: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, revision)


def _downgrade(engine: Engine, revision: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.downgrade(config, revision)


def test_upgrade_downgrade_reapply(engine: Engine) -> None:
    parsed_db = engine.url.database
    assert parsed_db == "panne"
    assert engine.dialect.name == "postgresql"
    url = postgres_url()
    assert "mysql" not in url.lower()

    _downgrade(engine, "0001_foundation")
    tables_at_0001 = set(inspect(engine).get_table_names())
    assert tables_at_0001 == {"alembic_version"} or tables_at_0001 <= {"alembic_version"}

    _upgrade(engine, "0003_ingredient_catalog")
    tables_at_0003 = set(inspect(engine).get_table_names())
    assert "formulation" not in tables_at_0003
    assert "technical_product" not in tables_at_0003

    _upgrade(engine, "0004_formulation_lab")
    tables_at_0004 = set(inspect(engine).get_table_names())
    assert "formulation" in tables_at_0004
    assert "nutrition_calculation" not in tables_at_0004
    assert "calculation_evidence" not in tables_at_0004

    _upgrade(engine, "0005_nutrition_calculation")
    tables_at_0005 = set(inspect(engine).get_table_names())
    assert "nutrition_calculation" in tables_at_0005
    assert "knowledge_source" not in tables_at_0005
    assert "nutrition_expectation_profile" not in tables_at_0005

    _upgrade(engine, "0006_knowledge_grounding")
    tables_at_0006 = set(inspect(engine).get_table_names())
    assert "knowledge_source" in tables_at_0006
    assert "ai_interaction" not in tables_at_0006
    assert "ai_proposal" not in tables_at_0006

    _upgrade(engine, "0007_ai_orchestration")
    tables_at_0007 = set(inspect(engine).get_table_names())
    assert "ai_interaction" in tables_at_0007
    assert "compliance_framework" not in tables_at_0007

    _upgrade(engine, "0008_compliance_governance")
    tables = set(inspect(engine).get_table_names())
    assert "compliance_framework" in tables
    assert "auth_identity" not in tables

    _upgrade(engine, "0009_identity_authorization_rls")
    tables = set(inspect(engine).get_table_names())
    assert "auth_identity" in tables
    assert "production_order" not in tables

    _upgrade(engine, "0010_production_planning")
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_0010 <= tables
    assert "production_weighing_entry" not in tables
    assert "organization_ingredient" not in tables
    assert "formula_ingredient" not in tables
    assert "label_snapshot" not in tables

    _upgrade(engine, "0011_production_execution")
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_0011 <= tables
    assert "organization_membership_role" not in tables

    _upgrade(engine, "0012_production_api_roles")
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_0013 <= tables
    cols_0012 = {col["name"] for col in inspect(engine).get_columns("organization_membership")}
    assert "role" in cols_0012
    assert "legacy_role_label" not in cols_0012

    _upgrade(engine, "0013_legacy_role_label")
    cols_0013 = {col["name"] for col in inspect(engine).get_columns("organization_membership")}
    assert "legacy_role_label" in cols_0013
    assert "role" not in cols_0013

    _upgrade(engine, "0014_ingredient_http")
    tables_0014 = set(inspect(engine).get_table_names())
    assert "ingredient_command" in tables_0014
    cols_ing = {col["name"] for col in inspect(engine).get_columns("ingredient")}
    assert "row_version" in cols_ing
    _downgrade(engine, "0013_legacy_role_label")
    assert "ingredient_command" not in set(inspect(engine).get_table_names())
    _upgrade(engine, "0014_ingredient_http")
    _upgrade(engine, "0015_formulation_http")
    tables_0015 = set(inspect(engine).get_table_names())
    assert "formulation_command" in tables_0015
    cols_form = {col["name"] for col in inspect(engine).get_columns("formulation")}
    assert "row_version" in cols_form
    _downgrade(engine, "0014_ingredient_http")
    assert "formulation_command" not in set(inspect(engine).get_table_names())
    _upgrade(engine, "0015_formulation_http")
    _downgrade(engine, "0014_ingredient_http")
    _upgrade(engine, "0015_formulation_http")
    _upgrade(engine, "0016_recipe_ai_assistant")
    tables_0016 = set(inspect(engine).get_table_names())
    assert "formulation_version_recipe_reference" in tables_0016
    assert "ai_proposal_change" in tables_0016
    _downgrade(engine, "0015_formulation_http")
    assert "formulation_version_recipe_reference" not in set(inspect(engine).get_table_names())
    _upgrade(engine, "0016_recipe_ai_assistant")
    _downgrade(engine, "0015_formulation_http")
    _upgrade(engine, "0016_recipe_ai_assistant")
    _upgrade(engine, "0017_labeling_compliance")
    tables_0017 = set(inspect(engine).get_table_names())
    assert "labeling_dossier" in tables_0017
    assert "labeling_label_candidate" in tables_0017
    _downgrade(engine, "0016_recipe_ai_assistant")
    assert "labeling_dossier" not in set(inspect(engine).get_table_names())
    _upgrade(engine, "0017_labeling_compliance")
    _downgrade(engine, "0016_recipe_ai_assistant")
    _upgrade(engine, "0017_labeling_compliance")
    _upgrade(engine, "0018_costing_pricing")
    tables_0018 = set(inspect(engine).get_table_names())
    assert "costing_policy" in tables_0018
    assert "practiced_price" in tables_0018
    _downgrade(engine, "0017_labeling_compliance")
    assert "costing_policy" not in set(inspect(engine).get_table_names())
    _upgrade(engine, "0018_costing_pricing")
    _downgrade(engine, "0017_labeling_compliance")
    _upgrade(engine, "0018_costing_pricing")
    _upgrade(engine, "0019_reporting_analytics")
    tables_0019 = set(inspect(engine).get_table_names())
    assert "reporting_execution" in tables_0019
    assert "reporting_snapshot" in tables_0019
    _downgrade(engine, "0018_costing_pricing")
    assert "reporting_execution" not in set(inspect(engine).get_table_names())
    _upgrade(engine, "0019_reporting_analytics")
    _downgrade(engine, "0018_costing_pricing")
    _upgrade(engine, "0019_reporting_analytics")
    _upgrade(engine, "0020_inventory_procurement")
    tables_0020 = set(inspect(engine).get_table_names())
    assert "inventory_movement" in tables_0020
    assert "procurement_order" in tables_0020
    _downgrade(engine, "0019_reporting_analytics")
    assert "inventory_movement" not in set(inspect(engine).get_table_names())
    _upgrade(engine, "0020_inventory_procurement")
    _downgrade(engine, "0019_reporting_analytics")
    _upgrade(engine, "0020_inventory_procurement")
    _upgrade(engine, "0021_product_canonical")
    tables_0021 = set(inspect(engine).get_table_names())
    assert "product_family" in tables_0021
    cols_product = {col["name"] for col in inspect(engine).get_columns("technical_product")}
    assert "supply_mode" in cols_product
    assert "purpose" in cols_product
    _downgrade(engine, "0020_inventory_procurement")
    assert "product_family" not in set(inspect(engine).get_table_names())
    _upgrade(engine, "0021_product_canonical")
    _upgrade(engine, "0022_fiscal_inbound")
    tables_0022 = set(inspect(engine).get_table_names())
    assert "fiscal_inbound_document" in tables_0022
    assert "establishment_fiscal_certificate" in tables_0022
    receipt_cols = {col["name"] for col in inspect(engine).get_columns("procurement_receipt")}
    assert "fiscal_inbound_document_id" in receipt_cols
    assert "source" in receipt_cols
    _downgrade(engine, "0021_product_canonical")
    assert "fiscal_inbound_document" not in set(inspect(engine).get_table_names())
    _upgrade(engine, "0022_fiscal_inbound")

    _downgrade(engine, "0012_production_api_roles")
    cols_back = {col["name"] for col in inspect(engine).get_columns("organization_membership")}
    assert "role" in cols_back
    assert "legacy_role_label" not in cols_back

    _upgrade(engine, "0013_legacy_role_label")
    _downgrade(engine, "0011_production_execution")
    tables_after_0012_down = set(inspect(engine).get_table_names())
    assert "organization_membership_role" not in tables_after_0012_down
    assert "production_weighing_entry" in tables_after_0012_down

    _upgrade(engine, "0012_production_api_roles")
    _downgrade(engine, "0010_production_planning")
    tables_after_0011_down = set(inspect(engine).get_table_names())
    assert "production_weighing_entry" not in tables_after_0011_down
    assert "production_order" in tables_after_0011_down

    _upgrade(engine, "0011_production_execution")
    _downgrade(engine, "0009_identity_authorization_rls")
    tables_after_0010_down = set(inspect(engine).get_table_names())
    assert "production_order" not in tables_after_0010_down
    assert "production_event" not in tables_after_0010_down
    assert "auth_identity" in tables_after_0010_down

    _upgrade(engine, "0010_production_planning")
    _downgrade(engine, "0008_compliance_governance")
    tables_after_0009_down = set(inspect(engine).get_table_names())
    assert "auth_identity" not in tables_after_0009_down
    assert "permission" not in tables_after_0009_down
    assert "compliance_framework" in tables_after_0009_down

    _upgrade(engine, "0009_identity_authorization_rls")
    _downgrade(engine, "0007_ai_orchestration")
    tables_after_down = set(inspect(engine).get_table_names())
    assert "compliance_framework" not in tables_after_down
    assert "ai_interaction" in tables_after_down

    _upgrade(engine, "0008_compliance_governance")
    _downgrade(engine, "0001_foundation")
    _upgrade(engine, "head")
    tables_from_empty = set(inspect(engine).get_table_names())
    assert EXPECTED <= tables_from_empty

    with engine.connect() as connection:
        current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        other = (
            connection.execute(text("SELECT datname FROM pg_database WHERE datname <> 'panne'"))
            .scalars()
            .all()
        )
    assert current == "0025_economic_audit_policy"
    assert "mysql" not in "".join(other).lower()
