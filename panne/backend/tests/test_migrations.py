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
EXPECTED = set(EXPECTED_0013) | {"ingredient_command"}


def _alembic() -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    return config


def test_upgrade_downgrade_reapply(engine: Engine) -> None:
    parsed_db = engine.url.database
    assert parsed_db == "panne"
    assert engine.dialect.name == "postgresql"
    url = postgres_url()
    assert "mysql" not in url.lower()

    command.downgrade(_alembic(), "0001_foundation")
    tables_at_0001 = set(inspect(engine).get_table_names())
    assert tables_at_0001 == {"alembic_version"} or tables_at_0001 <= {"alembic_version"}

    command.upgrade(_alembic(), "0003_ingredient_catalog")
    tables_at_0003 = set(inspect(engine).get_table_names())
    assert "formulation" not in tables_at_0003
    assert "technical_product" not in tables_at_0003

    command.upgrade(_alembic(), "0004_formulation_lab")
    tables_at_0004 = set(inspect(engine).get_table_names())
    assert "formulation" in tables_at_0004
    assert "nutrition_calculation" not in tables_at_0004
    assert "calculation_evidence" not in tables_at_0004

    command.upgrade(_alembic(), "0005_nutrition_calculation")
    tables_at_0005 = set(inspect(engine).get_table_names())
    assert "nutrition_calculation" in tables_at_0005
    assert "knowledge_source" not in tables_at_0005
    assert "nutrition_expectation_profile" not in tables_at_0005

    command.upgrade(_alembic(), "0006_knowledge_grounding")
    tables_at_0006 = set(inspect(engine).get_table_names())
    assert "knowledge_source" in tables_at_0006
    assert "ai_interaction" not in tables_at_0006
    assert "ai_proposal" not in tables_at_0006

    command.upgrade(_alembic(), "0007_ai_orchestration")
    tables_at_0007 = set(inspect(engine).get_table_names())
    assert "ai_interaction" in tables_at_0007
    assert "compliance_framework" not in tables_at_0007

    command.upgrade(_alembic(), "0008_compliance_governance")
    tables = set(inspect(engine).get_table_names())
    assert "compliance_framework" in tables
    assert "auth_identity" not in tables

    command.upgrade(_alembic(), "0009_identity_authorization_rls")
    tables = set(inspect(engine).get_table_names())
    assert "auth_identity" in tables
    assert "production_order" not in tables

    command.upgrade(_alembic(), "0010_production_planning")
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_0010 <= tables
    assert "production_weighing_entry" not in tables
    assert "organization_ingredient" not in tables
    assert "formula_ingredient" not in tables
    assert "label_snapshot" not in tables

    command.upgrade(_alembic(), "0011_production_execution")
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_0011 <= tables
    assert "organization_membership_role" not in tables

    command.upgrade(_alembic(), "0012_production_api_roles")
    tables = set(inspect(engine).get_table_names())
    assert EXPECTED_0013 <= tables
    cols_0012 = {col["name"] for col in inspect(engine).get_columns("organization_membership")}
    assert "role" in cols_0012
    assert "legacy_role_label" not in cols_0012

    command.upgrade(_alembic(), "0013_legacy_role_label")
    cols_0013 = {col["name"] for col in inspect(engine).get_columns("organization_membership")}
    assert "legacy_role_label" in cols_0013
    assert "role" not in cols_0013

    command.upgrade(_alembic(), "0014_ingredient_http")
    tables_0014 = set(inspect(engine).get_table_names())
    assert "ingredient_command" in tables_0014
    cols_ing = {col["name"] for col in inspect(engine).get_columns("ingredient")}
    assert "row_version" in cols_ing
    command.downgrade(_alembic(), "0013_legacy_role_label")
    assert "ingredient_command" not in set(inspect(engine).get_table_names())
    command.upgrade(_alembic(), "0014_ingredient_http")

    command.downgrade(_alembic(), "0012_production_api_roles")
    cols_back = {col["name"] for col in inspect(engine).get_columns("organization_membership")}
    assert "role" in cols_back
    assert "legacy_role_label" not in cols_back

    command.upgrade(_alembic(), "0013_legacy_role_label")
    command.downgrade(_alembic(), "0011_production_execution")
    tables_after_0012_down = set(inspect(engine).get_table_names())
    assert "organization_membership_role" not in tables_after_0012_down
    assert "production_weighing_entry" in tables_after_0012_down

    command.upgrade(_alembic(), "0012_production_api_roles")
    command.downgrade(_alembic(), "0010_production_planning")
    tables_after_0011_down = set(inspect(engine).get_table_names())
    assert "production_weighing_entry" not in tables_after_0011_down
    assert "production_order" in tables_after_0011_down

    command.upgrade(_alembic(), "0011_production_execution")
    command.downgrade(_alembic(), "0009_identity_authorization_rls")
    tables_after_0010_down = set(inspect(engine).get_table_names())
    assert "production_order" not in tables_after_0010_down
    assert "production_event" not in tables_after_0010_down
    assert "auth_identity" in tables_after_0010_down

    command.upgrade(_alembic(), "0010_production_planning")
    command.downgrade(_alembic(), "0008_compliance_governance")
    tables_after_0009_down = set(inspect(engine).get_table_names())
    assert "auth_identity" not in tables_after_0009_down
    assert "permission" not in tables_after_0009_down
    assert "compliance_framework" in tables_after_0009_down

    command.upgrade(_alembic(), "0009_identity_authorization_rls")
    command.downgrade(_alembic(), "0007_ai_orchestration")
    tables_after_down = set(inspect(engine).get_table_names())
    assert "compliance_framework" not in tables_after_down
    assert "ai_interaction" in tables_after_down

    command.upgrade(_alembic(), "0008_compliance_governance")
    command.downgrade(_alembic(), "0001_foundation")
    command.upgrade(_alembic(), "head")
    tables_from_empty = set(inspect(engine).get_table_names())
    assert EXPECTED <= tables_from_empty

    with engine.connect() as connection:
        current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        other = (
            connection.execute(text("SELECT datname FROM pg_database WHERE datname <> 'panne'"))
            .scalars()
            .all()
        )
    assert current == "0014_ingredient_http"
    assert "mysql" not in "".join(other).lower()
