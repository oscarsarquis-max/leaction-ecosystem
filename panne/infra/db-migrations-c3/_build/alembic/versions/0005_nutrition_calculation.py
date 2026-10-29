"""Cálculo nutricional técnico bruto e versionado.

Revision ID: 0005_nutrition_calculation
Revises: 0004_formulation_lab
Create Date: 2026-08-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_nutrition_calculation"
down_revision: Union[str, Sequence[str], None] = "0004_formulation_lab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nutrition_calculation",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("calculation_basis", sa.Text(), nullable=False),
        sa.Column("formulation_version_status", sa.Text(), nullable=False),
        sa.Column("is_simulation", sa.Boolean(), nullable=False),
        sa.Column("formula_net_mass_g", sa.Numeric(14, 6), nullable=False),
        sa.Column("expected_final_mass_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("portion_mass_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("algorithm_name", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("rounding_policy", sa.Text(), nullable=False),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("calculated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "assumptions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('complete','incomplete','invalidated')",
            name="ck_nutrition_calculation_status",
        ),
        sa.CheckConstraint(
            "calculation_basis IN ('whole_formula','per_100g','technical_portion')",
            name="ck_nutrition_calculation_basis",
        ),
        sa.CheckConstraint("formula_net_mass_g > 0", name="ck_nutrition_calculation_net"),
        sa.CheckConstraint(
            "expected_final_mass_g IS NULL OR expected_final_mass_g > 0",
            name="ck_nutrition_calculation_final",
        ),
        sa.CheckConstraint(
            "portion_mass_g IS NULL OR portion_mass_g > 0",
            name="ck_nutrition_calculation_portion",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(warnings) = 'array'",
            name="ck_nutrition_calculation_warnings",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(assumptions) = 'array'",
            name="ck_nutrition_calculation_assumptions",
        ),
        sa.ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["calculated_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_nutrition_calculation_id_org"),
    )
    op.create_index(
        "ix_nutrition_calculation_version",
        "nutrition_calculation",
        ["organization_id", "formulation_version_id"],
    )

    op.create_table(
        "nutrition_calculation_item",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("nutrition_calculation_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_definition_id", sa.Uuid(), nullable=False),
        sa.Column("measurement_unit_id", sa.Uuid(), nullable=False),
        sa.Column("whole_formula_amount", sa.Numeric(14, 6), nullable=False),
        sa.Column("per_100g_amount", sa.Numeric(14, 6), nullable=True),
        sa.Column("technical_portion_amount", sa.Numeric(14, 6), nullable=True),
        sa.Column("completeness_status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("whole_formula_amount >= 0", name="ck_nutrition_item_whole"),
        sa.CheckConstraint(
            "per_100g_amount IS NULL OR per_100g_amount >= 0",
            name="ck_nutrition_item_100g",
        ),
        sa.CheckConstraint(
            "technical_portion_amount IS NULL OR technical_portion_amount >= 0",
            name="ck_nutrition_item_portion",
        ),
        sa.CheckConstraint(
            "completeness_status IN ("
            "'complete','missing_data','not_applicable','below_quantification_limit')",
            name="ck_nutrition_item_completeness",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_calculation_id", "organization_id"],
            ["nutrition_calculation.id", "nutrition_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["nutrient_definition_id"], ["nutrient_definition.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["measurement_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "nutrition_calculation_id",
            "nutrient_definition_id",
            name="uq_nutrition_calculation_item_nutrient",
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_nutrition_calculation_item_id_org"),
    )

    op.create_table(
        "calculation_evidence",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("nutrition_calculation_id", sa.Uuid(), nullable=False),
        sa.Column("nutrition_calculation_item_id", sa.Uuid(), nullable=True),
        sa.Column("formulation_item_id", sa.Uuid(), nullable=True),
        sa.Column("ingredient_version_id", sa.Uuid(), nullable=True),
        sa.Column("ingredient_nutrient_id", sa.Uuid(), nullable=True),
        sa.Column("data_source_id", sa.Uuid(), nullable=True),
        sa.Column("evidence_type", sa.Text(), nullable=False),
        sa.Column("ingredient_quantity_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("source_nutrient_value", sa.Numeric(14, 6), nullable=True),
        sa.Column("source_basis", sa.Text(), nullable=True),
        sa.Column("contribution_amount", sa.Numeric(14, 6), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "evidence_type IN ("
            "'source_value','calculated_contribution','missing_value',"
            "'yield_assumption','portion_assumption','unit_conversion','warning')",
            name="ck_calculation_evidence_type",
        ),
        sa.CheckConstraint(
            "status IN ('recorded','missing')",
            name="ck_calculation_evidence_status",
        ),
        sa.CheckConstraint(
            "ingredient_quantity_g IS NULL OR ingredient_quantity_g > 0",
            name="ck_calculation_evidence_qty",
        ),
        sa.CheckConstraint(
            "source_nutrient_value IS NULL OR source_nutrient_value >= 0",
            name="ck_calculation_evidence_source",
        ),
        sa.CheckConstraint(
            "contribution_amount IS NULL OR contribution_amount >= 0",
            name="ck_calculation_evidence_contrib",
        ),
        sa.CheckConstraint("char_length(message) > 0", name="ck_calculation_evidence_message"),
        sa.ForeignKeyConstraint(
            ["nutrition_calculation_id", "organization_id"],
            ["nutrition_calculation.id", "nutrition_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["nutrition_calculation_item_id", "organization_id"],
            ["nutrition_calculation_item.id", "nutrition_calculation_item.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["formulation_item_id", "organization_id"],
            ["formulation_item.id", "formulation_item.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_nutrient_id"], ["ingredient_nutrient.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_source.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_calculation_evidence_calc",
        "calculation_evidence",
        ["nutrition_calculation_id", "created_at"],
    )

    for table in (
        "nutrition_calculation",
        "nutrition_calculation_item",
        "calculation_evidence",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_forbid_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_physical_delete();
            """
        )

    op.execute(
        """
        CREATE TRIGGER nutrition_calculation_item_append_only
        BEFORE UPDATE ON nutrition_calculation_item
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER calculation_evidence_append_only
        BEFORE UPDATE ON calculation_evidence
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_mutation();
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_nutrition_calculation_freeze() RETURNS trigger AS $$
        BEGIN
          IF OLD.status = 'invalidated' THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF NEW.status = 'invalidated'
             AND NEW.organization_id IS NOT DISTINCT FROM OLD.organization_id
             AND NEW.formulation_version_id IS NOT DISTINCT FROM OLD.formulation_version_id
             AND NEW.calculation_basis IS NOT DISTINCT FROM OLD.calculation_basis
             AND NEW.formulation_version_status IS NOT DISTINCT FROM OLD.formulation_version_status
             AND NEW.is_simulation IS NOT DISTINCT FROM OLD.is_simulation
             AND NEW.formula_net_mass_g IS NOT DISTINCT FROM OLD.formula_net_mass_g
             AND NEW.expected_final_mass_g IS NOT DISTINCT FROM OLD.expected_final_mass_g
             AND NEW.portion_mass_g IS NOT DISTINCT FROM OLD.portion_mass_g
             AND NEW.algorithm_name IS NOT DISTINCT FROM OLD.algorithm_name
             AND NEW.algorithm_version IS NOT DISTINCT FROM OLD.algorithm_version
             AND NEW.rounding_policy IS NOT DISTINCT FROM OLD.rounding_policy
             AND NEW.calculated_at IS NOT DISTINCT FROM OLD.calculated_at
             AND NEW.calculated_by_user_id IS NOT DISTINCT FROM OLD.calculated_by_user_id
             AND NEW.warnings IS NOT DISTINCT FROM OLD.warnings
             AND NEW.assumptions IS NOT DISTINCT FROM OLD.assumptions
          THEN
            RETURN NEW;
          END IF;
          RAISE EXCEPTION 'append_only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER nutrition_calculation_freeze
        BEFORE UPDATE ON nutrition_calculation
        FOR EACH ROW EXECUTE FUNCTION panne_nutrition_calculation_freeze();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS nutrition_calculation_freeze ON nutrition_calculation")
    op.execute("DROP TRIGGER IF EXISTS calculation_evidence_append_only ON calculation_evidence")
    op.execute(
        "DROP TRIGGER IF EXISTS nutrition_calculation_item_append_only"
        " ON nutrition_calculation_item"
    )
    for table in (
        "calculation_evidence",
        "nutrition_calculation_item",
        "nutrition_calculation",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_forbid_delete ON {table}")
    op.execute("DROP FUNCTION IF EXISTS panne_nutrition_calculation_freeze()")
    op.drop_index("ix_calculation_evidence_calc", table_name="calculation_evidence")
    op.drop_table("calculation_evidence")
    op.drop_table("nutrition_calculation_item")
    op.drop_index("ix_nutrition_calculation_version", table_name="nutrition_calculation")
    op.drop_table("nutrition_calculation")
