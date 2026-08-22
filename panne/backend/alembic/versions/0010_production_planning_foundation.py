"""Fundação de planejamento e ordens de produção.

Revision ID: 0010_production_planning
Revises: 0009_identity_authorization_rls
Create Date: 2026-08-22
"""

# ruff: noqa: E501

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from app.modules.identity_organization.authorization import (
    PERMISSIONS,
    PRODUCTION_PERMISSIONS,
    ROLE_PERMISSIONS,
)
from sqlalchemy.dialects import postgresql

revision: str = "0010_production_planning"
down_revision: Union[str, Sequence[str], None] = "0009_identity_authorization_rls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"

_TABLES = (
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
)

_PLAN_STATUS = "status IN ('draft','scheduled','archived')"
_ORDER_STATUS = (
    "status IN ('draft','scheduled','released','in_weighing','ready','in_progress',"
    "'on_hold','completed','short_closed','cancelled')"
)
_BATCH_STATUS = (
    "status IN ('pending','in_weighing','in_progress','on_hold','completed','scrapped','cancelled')"
)
_SHIFT = "shift IS NULL OR shift IN ('morning','afternoon','night')"
_TARGET = "target_mode IN ('units','mass')"
_DEP = "dependency_type IN ('preferment','intermediate','other')"


def _uuid() -> sa.Column:
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _org() -> sa.Column:
    return sa.Column("organization_id", sa.Uuid(), nullable=False)


def _ts() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def _enable(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def _policy_org(table: str) -> None:
    op.execute(
        f"CREATE POLICY rls_{table}_org ON {table} FOR ALL USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )


def upgrade() -> None:
    op.create_index("uq_process_step_id_org", "process_step", ["id", "organization_id"], unique=True)
    op.execute("CREATE SEQUENCE production_event_seq")

    op.create_table(
        "production_code_counter",
        _uuid(),
        _org(),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("period", sa.Text(), nullable=False),
        sa.Column("last_value", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *_ts(),
        sa.CheckConstraint("kind IN ('plan','order')", name="ck_production_code_counter_kind"),
        sa.CheckConstraint("last_value >= 0", name="ck_production_code_counter_value"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "kind", "period", name="uq_production_code_counter_period"),
    )

    op.create_table(
        "production_plan",
        _uuid(),
        _org(),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("public_code", sa.Text(), nullable=False),
        sa.Column("operational_date", sa.Date(), nullable=False),
        sa.Column("shift", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        *_ts(),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("char_length(btrim(public_code)) > 0", name="ck_production_plan_code"),
        sa.CheckConstraint(_PLAN_STATUS, name="ck_production_plan_status"),
        sa.CheckConstraint(_SHIFT, name="ck_production_plan_shift"),
        sa.CheckConstraint("row_version >= 1", name="ck_production_plan_version"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "public_code", name="uq_production_plan_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_plan_id_org"),
    )

    op.create_table(
        "production_plan_item",
        _uuid(),
        _org(),
        sa.Column("production_plan_id", sa.Uuid(), nullable=False),
        sa.Column("technical_product_id", sa.Uuid(), nullable=False),
        sa.Column("target_mode", sa.Text(), nullable=False),
        sa.Column("target_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("unit_weight_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("priority", sa.Integer(), server_default=sa.text("50"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("desired_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("desired_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_ts(),
        sa.CheckConstraint(_TARGET, name="ck_production_plan_item_mode"),
        sa.CheckConstraint("target_quantity > 0", name="ck_production_plan_item_qty"),
        sa.CheckConstraint("priority BETWEEN 1 AND 99", name="ck_production_plan_item_priority"),
        sa.ForeignKeyConstraint(
            ["production_plan_id", "organization_id"],
            ["production_plan.id", "production_plan.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["technical_product_id", "organization_id"],
            ["technical_product.id", "technical_product.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("production_plan_id", "sort_order", name="uq_production_plan_item_sort"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_plan_item_id_org"),
    )

    op.create_table(
        "production_order",
        _uuid(),
        _org(),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("public_code", sa.Text(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=True),
        sa.Column("plan_item_id", sa.Uuid(), nullable=True),
        sa.Column("technical_product_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_version_id", sa.Uuid(), nullable=True),
        sa.Column("scale_calculation_id", sa.Uuid(), nullable=True),
        sa.Column("target_mode", sa.Text(), nullable=False),
        sa.Column("target_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("unit_weight_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("priority", sa.Integer(), server_default=sa.text("50"), nullable=False),
        sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("scheduled_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("released_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("cancelled_by_user_id", sa.Uuid(), nullable=True),
        *_ts(),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("held_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("hold_reason", sa.Text(), nullable=True),
        sa.Column("superseded_order_id", sa.Uuid(), nullable=True),
        sa.Column("successor_order_id", sa.Uuid(), nullable=True),
        sa.Column("materials_hash", sa.Text(), nullable=True),
        sa.Column("steps_hash", sa.Text(), nullable=True),
        sa.Column("snapshot_hash", sa.Text(), nullable=True),
        sa.CheckConstraint("char_length(btrim(public_code)) > 0", name="ck_production_order_code"),
        sa.CheckConstraint(_ORDER_STATUS, name="ck_production_order_status"),
        sa.CheckConstraint(_TARGET, name="ck_production_order_mode"),
        sa.CheckConstraint("target_quantity > 0", name="ck_production_order_qty"),
        sa.CheckConstraint("priority BETWEEN 1 AND 99", name="ck_production_order_priority"),
        sa.CheckConstraint("row_version >= 1", name="ck_production_order_version"),
        sa.CheckConstraint(
            "(plan_id IS NULL) = (plan_item_id IS NULL) OR plan_item_id IS NULL",
            name="ck_production_order_plan_pair",
        ),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["scheduled_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["released_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cancelled_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id", "organization_id"],
            ["production_plan.id", "production_plan.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["plan_item_id", "organization_id"],
            ["production_plan_item.id", "production_plan_item.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["technical_product_id", "organization_id"],
            ["technical_product.id", "technical_product.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scale_calculation_id", "organization_id"],
            ["scale_calculation.id", "scale_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["superseded_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["successor_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "public_code", name="uq_production_order_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_order_id_org"),
    )
    op.create_index(
        "uq_production_order_active_item",
        "production_order",
        ["plan_item_id"],
        unique=True,
        postgresql_where=sa.text("plan_item_id IS NOT NULL AND status <> 'cancelled'"),
    )

    op.create_table(
        "production_order_dependency",
        _uuid(),
        _org(),
        sa.Column("dependent_order_id", sa.Uuid(), nullable=False),
        sa.Column("predecessor_order_id", sa.Uuid(), nullable=False),
        sa.Column("dependency_type", sa.Text(), nullable=False),
        sa.Column("relation_note", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(_DEP, name="ck_production_order_dependency_type"),
        sa.CheckConstraint(
            "dependent_order_id <> predecessor_order_id",
            name="ck_production_order_dependency_self",
        ),
        sa.ForeignKeyConstraint(
            ["dependent_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["predecessor_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dependent_order_id", "predecessor_order_id", name="uq_production_order_dependency_pair"
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_order_dependency_id_org"),
    )

    op.create_table(
        "production_batch",
        _uuid(),
        _org(),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("operational_code", sa.Text(), nullable=False),
        sa.Column("target_mode", sa.Text(), nullable=False),
        sa.Column("target_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("split_factor", sa.Numeric(20, 10), nullable=False),
        sa.Column("remainder_applied", sa.Numeric(14, 6), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "split_memory",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        *_ts(),
        sa.CheckConstraint(_BATCH_STATUS, name="ck_production_batch_status"),
        sa.CheckConstraint(_TARGET, name="ck_production_batch_mode"),
        sa.CheckConstraint("target_quantity > 0", name="ck_production_batch_qty"),
        sa.CheckConstraint("sequence >= 1", name="ck_production_batch_sequence"),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("production_order_id", "sequence", name="uq_production_batch_sequence"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_batch_id_org"),
    )

    op.create_table(
        "production_order_material",
        _uuid(),
        _org(),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_item_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_version_id", sa.Uuid(), nullable=False),
        sa.Column("operational_name", sa.Text(), nullable=False),
        sa.Column("measurement_unit_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("unit_name", sa.Text(), nullable=False),
        sa.Column("net_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("correction_factor", sa.Numeric(20, 10), nullable=False),
        sa.Column("gross_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("bakers_percentage", sa.Numeric(14, 6), nullable=True),
        sa.Column("is_flour_basis", sa.Boolean(), nullable=False),
        sa.Column("presentation_sequence", sa.Integer(), nullable=False),
        sa.Column("algorithm_code", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("rounding_mode", sa.Text(), nullable=False),
        sa.Column("presentation_decimal_places", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("net_quantity > 0 AND gross_quantity > 0", name="ck_production_order_material_qty"),
        sa.ForeignKeyConstraint(["measurement_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "production_order_id", "presentation_sequence", name="uq_production_order_material_seq"
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_order_material_id_org"),
    )

    op.create_table(
        "production_order_step",
        _uuid(),
        _org(),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("process_step_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("temperature_value", sa.Numeric(6, 2), nullable=True),
        sa.Column("temperature_unit", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "control_points",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["process_step_id", "organization_id"],
            ["process_step.id", "process_step.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("production_order_id", "sequence", name="uq_production_order_step_seq"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_order_step_id_org"),
    )

    op.create_table(
        "production_batch_material",
        _uuid(),
        _org(),
        sa.Column("production_batch_id", sa.Uuid(), nullable=False),
        sa.Column("production_order_material_id", sa.Uuid(), nullable=False),
        sa.Column("planned_net_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("planned_gross_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("remainder_applied", sa.Numeric(14, 6), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_order_material_id", "organization_id"],
            ["production_order_material.id", "production_order_material.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "production_batch_id",
            "production_order_material_id",
            name="uq_production_batch_material_line",
        ),
    )

    op.create_table(
        "production_event",
        _uuid(),
        _org(),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("plan_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        sa.Column("causation_event_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("payload_digest", sa.Text(), nullable=False),
        sa.Column("schema_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "sequence_no",
            sa.BigInteger(),
            server_default=sa.text("nextval('production_event_seq')"),
            nullable=False,
        ),
        sa.CheckConstraint("char_length(btrim(event_type)) > 0", name="ck_production_event_type"),
        sa.ForeignKeyConstraint(["establishment_id"], ["establishment.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["causation_event_id"], ["production_event.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["plan_id", "organization_id"],
            ["production_plan.id", "production_plan.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_production_event_idempotency"),
    )
    op.create_index(
        "ix_production_event_stable_order", "production_event", ["organization_id", "sequence_no"]
    )

    op.execute(
        """
        CREATE FUNCTION production_event_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'evento_imutavel';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_production_event_append_only
        BEFORE UPDATE OR DELETE ON production_event
        FOR EACH ROW EXECUTE FUNCTION production_event_append_only()
        """
    )
    op.execute(
        """
        CREATE FUNCTION production_snapshot_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'snapshot_imutavel';
        END;
        $$
        """
    )
    for table in (
        "production_order_material",
        "production_order_step",
        "production_batch_material",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_immutable
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION production_snapshot_immutable()
            """
        )
    op.execute(
        """
        CREATE FUNCTION production_order_protect() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND OLD.status NOT IN ('draft','scheduled') THEN
            RAISE EXCEPTION 'ordem_nao_excluivel';
          END IF;
          IF TG_OP = 'UPDATE' THEN
            IF OLD.public_code IS DISTINCT FROM NEW.public_code THEN
              RAISE EXCEPTION 'codigo_imutavel';
            END IF;
            IF OLD.status NOT IN ('draft','scheduled') THEN
              IF OLD.technical_product_id IS DISTINCT FROM NEW.technical_product_id
                 OR OLD.formulation_version_id IS DISTINCT FROM NEW.formulation_version_id
                 OR OLD.scale_calculation_id IS DISTINCT FROM NEW.scale_calculation_id
                 OR OLD.establishment_id IS DISTINCT FROM NEW.establishment_id
                 OR OLD.target_mode IS DISTINCT FROM NEW.target_mode
                 OR OLD.target_quantity IS DISTINCT FROM NEW.target_quantity
                 OR OLD.organization_id IS DISTINCT FROM NEW.organization_id THEN
                RAISE EXCEPTION 'ordem_imutavel';
              END IF;
            END IF;
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_production_order_protect
        BEFORE UPDATE OR DELETE ON production_order
        FOR EACH ROW EXECUTE FUNCTION production_order_protect()
        """
    )
    op.execute(
        """
        CREATE FUNCTION production_plan_protect() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND (
            EXISTS (SELECT 1 FROM production_order o WHERE o.plan_id = OLD.id)
            OR EXISTS (SELECT 1 FROM production_event e WHERE e.plan_id = OLD.id)
          ) THEN
            RAISE EXCEPTION 'plano_nao_excluivel';
          END IF;
          IF TG_OP = 'UPDATE' AND OLD.public_code IS DISTINCT FROM NEW.public_code THEN
            RAISE EXCEPTION 'codigo_imutavel';
          END IF;
          RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_production_plan_protect
        BEFORE UPDATE OR DELETE ON production_plan
        FOR EACH ROW EXECUTE FUNCTION production_plan_protect()
        """
    )

    bind = op.get_bind()
    for code, description in PERMISSIONS:
        if code not in PRODUCTION_PERMISSIONS:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO permission (code, description) VALUES (:code, :description) "
                "ON CONFLICT (code) DO NOTHING"
            ),
            {"code": code, "description": description},
        )
    for role, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            if code not in PRODUCTION_PERMISSIONS:
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO role_permission (role, permission_id) "
                    "SELECT :role, id FROM permission WHERE code = :code "
                    "AND NOT EXISTS ("
                    "SELECT 1 FROM role_permission rp "
                    "WHERE rp.role = :role AND rp.permission_id = permission.id)"
                ),
                {"role": role, "code": code},
            )

    for table in _TABLES:
        _enable(table)
        _policy_org(table)


def downgrade() -> None:
    bind = op.get_bind()
    for code in PRODUCTION_PERMISSIONS:
        bind.execute(
            sa.text(
                "DELETE FROM role_permission WHERE permission_id IN "
                "(SELECT id FROM permission WHERE code = :code)"
            ),
            {"code": code},
        )
        bind.execute(sa.text("DELETE FROM permission WHERE code = :code"), {"code": code})
    op.execute("DROP TRIGGER IF EXISTS trg_production_plan_protect ON production_plan")
    op.execute("DROP TRIGGER IF EXISTS trg_production_order_protect ON production_order")
    op.execute("DROP TRIGGER IF EXISTS trg_production_event_append_only ON production_event")
    for table in (
        "production_order_material",
        "production_order_step",
        "production_batch_material",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS production_plan_protect()")
    op.execute("DROP FUNCTION IF EXISTS production_order_protect()")
    op.execute("DROP FUNCTION IF EXISTS production_snapshot_immutable()")
    op.execute("DROP FUNCTION IF EXISTS production_event_append_only()")
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_org ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
    op.execute("DROP SEQUENCE IF EXISTS production_event_seq")
    op.drop_index("uq_process_step_id_org", table_name="process_step")
