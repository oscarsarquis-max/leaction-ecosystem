"""Núcleo de produto técnico e formulações.

Revision ID: 0004_formulation_lab
Revises: 0003_ingredient_catalog
Create Date: 2026-08-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_formulation_lab"
down_revision: Union[str, Sequence[str], None] = "0003_ingredient_catalog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_pair() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "technical_product",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'development'"), nullable=False),
        *_audit_pair(),
        sa.CheckConstraint("char_length(code) > 0", name="ck_technical_product_code"),
        sa.CheckConstraint(
            "status IN ('development','approved','retired')",
            name="ck_technical_product_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_technical_product_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_technical_product_id_org"),
    )
    op.create_index(
        "ix_technical_product_org_status", "technical_product", ["organization_id", "status"]
    )

    op.create_table(
        "recipe_reference",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("license_or_usage_notes", sa.Text(), nullable=True),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("char_length(title) > 0", name="ck_recipe_reference_title"),
        sa.CheckConstraint(
            "source_type IN ('external','internal','user_declared')",
            name="ck_recipe_reference_source_type",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_recipe_reference_id_org"),
    )

    op.create_table(
        "formulation",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("technical_product_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'development'"), nullable=False),
        *_audit_pair(),
        sa.CheckConstraint("char_length(code) > 0", name="ck_formulation_code"),
        sa.CheckConstraint(
            "status IN ('development','active','retired')",
            name="ck_formulation_status",
        ),
        sa.ForeignKeyConstraint(
            ["technical_product_id", "organization_id"],
            ["technical_product.id", "technical_product.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_formulation_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_formulation_id_org"),
    )
    op.create_index(
        "ix_formulation_product",
        "formulation",
        ["organization_id", "technical_product_id"],
    )

    op.create_table(
        "formulation_recipe_reference",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_id", sa.Uuid(), nullable=False),
        sa.Column("recipe_reference_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('inspiration','source','comparison')",
            name="ck_formulation_recipe_reference_role",
        ),
        sa.ForeignKeyConstraint(
            ["formulation_id", "organization_id"],
            ["formulation.id", "formulation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_reference_id", "organization_id"],
            ["recipe_reference.id", "recipe_reference.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "formulation_id",
            "recipe_reference_id",
            name="uq_formulation_recipe_reference",
        ),
    )

    op.create_table(
        "formulation_version",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("yield_units", sa.Integer(), nullable=True),
        sa.Column("target_unit_weight_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("expected_bake_loss_rate", sa.Numeric(20, 10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft','published','retired')",
            name="ck_formulation_version_status",
        ),
        sa.CheckConstraint("version_number >= 1", name="ck_formulation_version_number"),
        sa.CheckConstraint(
            "yield_units IS NULL OR yield_units >= 0",
            name="ck_formulation_version_yield",
        ),
        sa.CheckConstraint(
            "target_unit_weight_g IS NULL OR target_unit_weight_g >= 0",
            name="ck_formulation_version_unit_weight",
        ),
        sa.CheckConstraint(
            "expected_bake_loss_rate IS NULL"
            " OR (expected_bake_loss_rate >= 0 AND expected_bake_loss_rate < 1)",
            name="ck_formulation_version_loss",
        ),
        sa.ForeignKeyConstraint(
            ["formulation_id", "organization_id"],
            ["formulation.id", "formulation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "formulation_id", "version_number", name="uq_formulation_version_number"
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_formulation_version_id_org"),
    )
    op.create_index(
        "uq_formulation_version_published",
        "formulation_version",
        ["formulation_id"],
        unique=True,
        postgresql_where=sa.text("status = 'published'"),
    )
    op.create_index(
        "ix_formulation_version_org_status",
        "formulation_version",
        ["organization_id", "status"],
    )

    op.create_table(
        "formulation_item",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_version_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_version_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("net_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("measurement_unit_id", sa.Uuid(), nullable=False),
        sa.Column(
            "correction_factor",
            sa.Numeric(20, 10),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("is_flour_basis", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("role", sa.Text(), server_default=sa.text("'ingredient'"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("net_quantity > 0", name="ck_formulation_item_net"),
        sa.CheckConstraint("correction_factor > 0", name="ck_formulation_item_factor"),
        sa.CheckConstraint("sequence >= 0", name="ck_formulation_item_sequence"),
        sa.CheckConstraint(
            "role IN ('ingredient','preparation','additive')",
            name="ck_formulation_item_role",
        ),
        sa.ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["measurement_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "formulation_version_id", "sequence", name="uq_formulation_item_sequence"
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_formulation_item_id_org"),
    )

    op.create_table(
        "process_step",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_version_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("temperature_celsius", sa.Numeric(6, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("sequence >= 0", name="ck_process_step_sequence"),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_process_step_duration",
        ),
        sa.CheckConstraint("char_length(instructions) > 0", name="ck_process_step_instructions"),
        sa.ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("formulation_version_id", "sequence", name="uq_process_step_sequence"),
    )

    op.create_table(
        "scale_calculation",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_version_id", sa.Uuid(), nullable=False),
        sa.Column("calculation_mode", sa.Text(), nullable=False),
        sa.Column("input_target_total_dough_mass", sa.Numeric(14, 6), nullable=True),
        sa.Column("input_unit_count", sa.Integer(), nullable=True),
        sa.Column("input_final_unit_weight_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("input_bake_loss_rate", sa.Numeric(20, 10), nullable=True),
        sa.Column("base_total_net_mass", sa.Numeric(14, 6), nullable=False),
        sa.Column("scale_factor", sa.Numeric(20, 10), nullable=False),
        sa.Column("required_pre_bake_mass", sa.Numeric(14, 6), nullable=False),
        sa.Column("algorithm_code", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("rounding_mode", sa.Text(), nullable=False),
        sa.Column("presentation_decimal_places", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "calculation_mode IN ('total_dough_mass','final_units')",
            name="ck_scale_calculation_mode",
        ),
        sa.CheckConstraint(
            "("
            "calculation_mode = 'total_dough_mass'"
            " AND input_target_total_dough_mass IS NOT NULL"
            " AND input_target_total_dough_mass > 0"
            " AND input_unit_count IS NULL"
            " AND input_final_unit_weight_g IS NULL"
            " AND input_bake_loss_rate IS NULL"
            ") OR ("
            "calculation_mode = 'final_units'"
            " AND input_unit_count IS NOT NULL"
            " AND input_unit_count > 0"
            " AND input_final_unit_weight_g IS NOT NULL"
            " AND input_final_unit_weight_g > 0"
            " AND input_bake_loss_rate IS NOT NULL"
            " AND input_bake_loss_rate >= 0"
            " AND input_bake_loss_rate < 1"
            ")",
            name="ck_scale_calculation_inputs",
        ),
        sa.CheckConstraint("base_total_net_mass > 0", name="ck_scale_calculation_base"),
        sa.CheckConstraint("scale_factor > 0", name="ck_scale_calculation_factor"),
        sa.CheckConstraint("required_pre_bake_mass > 0", name="ck_scale_calculation_prebake"),
        sa.CheckConstraint(
            "presentation_decimal_places >= 0",
            name="ck_scale_calculation_places",
        ),
        sa.CheckConstraint(
            "rounding_mode = 'ROUND_HALF_UP'",
            name="ck_scale_calculation_rounding",
        ),
        sa.ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_scale_calculation_id_org"),
    )
    op.create_index(
        "ix_scale_calculation_version",
        "scale_calculation",
        ["formulation_version_id"],
    )

    op.create_table(
        "scale_calculation_item",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("scale_calculation_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_item_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_version_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("scaled_net_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("scaled_gross_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("bakers_percentage", sa.Numeric(14, 6), nullable=True),
        sa.Column("measurement_unit_id", sa.Uuid(), nullable=False),
        sa.Column("base_net_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("base_correction_factor", sa.Numeric(20, 10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("scaled_net_quantity > 0", name="ck_scale_item_net"),
        sa.CheckConstraint("scaled_gross_quantity > 0", name="ck_scale_item_gross"),
        sa.CheckConstraint("base_net_quantity > 0", name="ck_scale_item_base_net"),
        sa.CheckConstraint("base_correction_factor > 0", name="ck_scale_item_base_factor"),
        sa.CheckConstraint(
            "bakers_percentage IS NULL OR bakers_percentage >= 0",
            name="ck_scale_item_percent",
        ),
        sa.ForeignKeyConstraint(
            ["scale_calculation_id", "organization_id"],
            ["scale_calculation.id", "scale_calculation.organization_id"],
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
            ["measurement_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scale_calculation_id", "sequence", name="uq_scale_calculation_item_sequence"
        ),
    )

    op.create_table(
        "trial",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_version_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'planned'"), nullable=False),
        sa.Column("planned_on", sa.Date(), nullable=True),
        sa.Column("executed_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("char_length(code) > 0", name="ck_trial_code"),
        sa.CheckConstraint(
            "status IN ('planned','in_progress','completed','cancelled')",
            name="ck_trial_status",
        ),
        sa.ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_trial_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_trial_id_org"),
    )
    op.create_index("ix_trial_version", "trial", ["formulation_version_id"])

    op.create_table(
        "trial_measurement",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("trial_id", sa.Uuid(), nullable=False),
        sa.Column("measurement_type", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(14, 6), nullable=False),
        sa.Column("measurement_unit_id", sa.Uuid(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "measurement_type IN ("
            "'dough_mass','units_produced','final_unit_weight',"
            "'actual_loss','duration','temperature'"
            ")",
            name="ck_trial_measurement_type",
        ),
        sa.ForeignKeyConstraint(
            ["trial_id", "organization_id"],
            ["trial.id", "trial.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["measurement_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "approval",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_version_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "decision IN ('submitted','approved','rejected','revoked')",
            name="ck_approval_decision",
        ),
        sa.ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_approval_version_occurred",
        "approval",
        ["formulation_version_id", "occurred_at"],
    )

    op.execute(
        """
        CREATE FUNCTION panne_forbid_physical_delete() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'physical_delete_forbidden';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in (
        "technical_product",
        "recipe_reference",
        "formulation",
        "formulation_recipe_reference",
        "formulation_version",
        "scale_calculation",
        "scale_calculation_item",
        "approval",
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
        CREATE FUNCTION panne_formulation_item_unit_is_mass() RETURNS trigger AS $$
        DECLARE
          dim text;
        BEGIN
          SELECT dimension INTO dim FROM measurement_unit
          WHERE id = NEW.measurement_unit_id;
          IF dim IS DISTINCT FROM 'mass' THEN
            RAISE EXCEPTION 'formulation_item_unit_must_be_mass';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER formulation_item_unit_mass
        BEFORE INSERT OR UPDATE ON formulation_item
        FOR EACH ROW EXECUTE FUNCTION panne_formulation_item_unit_is_mass();
        """
    )

    op.execute(
        """
        CREATE FUNCTION panne_formulation_publish_requires_approval() RETURNS trigger AS $$
        BEGIN
          IF NEW.status = 'published'
             AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'published') THEN
            IF NOT EXISTS (
              SELECT 1 FROM approval
              WHERE formulation_version_id = NEW.id
                AND organization_id = NEW.organization_id
                AND decision = 'approved'
                AND NOT EXISTS (
                  SELECT 1 FROM approval later
                  WHERE later.formulation_version_id = NEW.id
                    AND later.organization_id = NEW.organization_id
                    AND (later.occurred_at, later.id) > (approval.occurred_at, approval.id)
                )
            ) THEN
              RAISE EXCEPTION 'publish_requires_approval';
            END IF;
            IF NEW.published_at IS NULL THEN
              NEW.published_at := clock_timestamp();
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER formulation_version_publish_approval
        BEFORE INSERT OR UPDATE ON formulation_version
        FOR EACH ROW EXECUTE FUNCTION panne_formulation_publish_requires_approval();
        """
    )

    op.execute(
        """
        CREATE FUNCTION panne_forbid_published_formulation_mutation() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'published_frozen';
          END IF;
          IF OLD.status = 'retired' THEN
            RAISE EXCEPTION 'published_frozen';
          END IF;
          IF OLD.status = 'published' THEN
            IF NEW.status = 'retired'
               AND NEW.version_number IS NOT DISTINCT FROM OLD.version_number
               AND NEW.formulation_id IS NOT DISTINCT FROM OLD.formulation_id
               AND NEW.organization_id IS NOT DISTINCT FROM OLD.organization_id
               AND NEW.yield_units IS NOT DISTINCT FROM OLD.yield_units
               AND NEW.target_unit_weight_g IS NOT DISTINCT FROM OLD.target_unit_weight_g
               AND NEW.expected_bake_loss_rate IS NOT DISTINCT FROM OLD.expected_bake_loss_rate
               AND NEW.notes IS NOT DISTINCT FROM OLD.notes
               AND NEW.created_at IS NOT DISTINCT FROM OLD.created_at
               AND NEW.created_by_user_id IS NOT DISTINCT FROM OLD.created_by_user_id
               AND NEW.published_at IS NOT DISTINCT FROM OLD.published_at
            THEN
              RETURN NEW;
            END IF;
            RAISE EXCEPTION 'published_frozen';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER formulation_version_published_frozen
        BEFORE UPDATE ON formulation_version
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_published_formulation_mutation();
        """
    )

    op.execute(
        """
        CREATE FUNCTION panne_forbid_published_formulation_child_mutation() RETURNS trigger AS $$
        DECLARE
          version_id uuid;
          v_status text;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            version_id := OLD.formulation_version_id;
          ELSE
            version_id := NEW.formulation_version_id;
          END IF;
          SELECT status INTO v_status FROM formulation_version WHERE id = version_id;
          IF v_status IN ('published', 'retired') THEN
            RAISE EXCEPTION 'published_frozen';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER formulation_item_published_frozen
        BEFORE INSERT OR UPDATE OR DELETE ON formulation_item
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_published_formulation_child_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER process_step_published_frozen
        BEFORE INSERT OR UPDATE OR DELETE ON process_step
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_published_formulation_child_mutation();
        """
    )

    op.execute(
        """
        CREATE TRIGGER scale_calculation_append_only
        BEFORE UPDATE ON scale_calculation
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER scale_calculation_item_append_only
        BEFORE UPDATE ON scale_calculation_item
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER approval_append_only
        BEFORE UPDATE ON approval
        FOR EACH ROW EXECUTE FUNCTION panne_forbid_mutation();
        """
    )

    op.execute(
        """
        CREATE FUNCTION panne_preserve_completed_trial() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND OLD.status IN ('completed', 'cancelled') THEN
            RAISE EXCEPTION 'trial_preserved';
          END IF;
          IF TG_OP = 'UPDATE' AND OLD.status IN ('completed', 'cancelled') THEN
            RAISE EXCEPTION 'trial_preserved';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trial_completed_preserved
        BEFORE UPDATE OR DELETE ON trial
        FOR EACH ROW EXECUTE FUNCTION panne_preserve_completed_trial();
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_preserve_completed_trial_measurement() RETURNS trigger AS $$
        DECLARE
          trial_status text;
          trial_id uuid;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            trial_id := OLD.trial_id;
          ELSE
            trial_id := NEW.trial_id;
          END IF;
          SELECT status INTO trial_status FROM trial WHERE id = trial_id;
          IF trial_status IN ('completed', 'cancelled') THEN
            RAISE EXCEPTION 'trial_preserved';
          END IF;
          IF TG_OP = 'DELETE' THEN
            RETURN OLD;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trial_measurement_completed_preserved
        BEFORE INSERT OR UPDATE OR DELETE ON trial_measurement
        FOR EACH ROW EXECUTE FUNCTION panne_preserve_completed_trial_measurement();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trial_measurement_completed_preserved ON trial_measurement")
    op.execute("DROP TRIGGER IF EXISTS trial_completed_preserved ON trial")
    op.execute("DROP TRIGGER IF EXISTS approval_append_only ON approval")
    op.execute(
        "DROP TRIGGER IF EXISTS scale_calculation_item_append_only ON scale_calculation_item"
    )
    op.execute("DROP TRIGGER IF EXISTS scale_calculation_append_only ON scale_calculation")
    op.execute("DROP TRIGGER IF EXISTS process_step_published_frozen ON process_step")
    op.execute("DROP TRIGGER IF EXISTS formulation_item_published_frozen ON formulation_item")
    op.execute("DROP TRIGGER IF EXISTS formulation_version_published_frozen ON formulation_version")
    op.execute("DROP TRIGGER IF EXISTS formulation_version_publish_approval ON formulation_version")
    op.execute("DROP TRIGGER IF EXISTS formulation_item_unit_mass ON formulation_item")
    for table in (
        "approval",
        "scale_calculation_item",
        "scale_calculation",
        "formulation_version",
        "formulation_recipe_reference",
        "formulation",
        "recipe_reference",
        "technical_product",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_forbid_delete ON {table}")
    op.execute("DROP FUNCTION IF EXISTS panne_preserve_completed_trial_measurement()")
    op.execute("DROP FUNCTION IF EXISTS panne_preserve_completed_trial()")
    op.execute("DROP FUNCTION IF EXISTS panne_forbid_published_formulation_child_mutation()")
    op.execute("DROP FUNCTION IF EXISTS panne_forbid_published_formulation_mutation()")
    op.execute("DROP FUNCTION IF EXISTS panne_formulation_publish_requires_approval()")
    op.execute("DROP FUNCTION IF EXISTS panne_formulation_item_unit_is_mass()")
    op.execute("DROP FUNCTION IF EXISTS panne_forbid_physical_delete()")
    op.drop_table("approval")
    op.drop_table("trial_measurement")
    op.drop_index("ix_trial_version", table_name="trial")
    op.drop_table("trial")
    op.drop_table("scale_calculation_item")
    op.drop_index("ix_scale_calculation_version", table_name="scale_calculation")
    op.drop_table("scale_calculation")
    op.drop_table("process_step")
    op.drop_table("formulation_item")
    op.drop_index("ix_formulation_version_org_status", table_name="formulation_version")
    op.drop_index("uq_formulation_version_published", table_name="formulation_version")
    op.drop_table("formulation_version")
    op.drop_table("formulation_recipe_reference")
    op.drop_index("ix_formulation_product", table_name="formulation")
    op.drop_table("formulation")
    op.drop_table("recipe_reference")
    op.drop_index("ix_technical_product_org_status", table_name="technical_product")
    op.drop_table("technical_product")
