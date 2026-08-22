"""Execução e apontamentos de produção.

Revision ID: 0011_production_execution
Revises: 0010_production_planning
Create Date: 2026-08-22
"""

# ruff: noqa: E501

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from app.modules.identity_organization.authorization import (
    PRODUCTION_EXECUTION_PERMISSIONS,
    ROLE_PERMISSIONS,
)
from app.modules.identity_organization.rls_inventory import PRODUCTION_EXECUTION_TABLES
from sqlalchemy.dialects import postgresql

revision: str = "0011_production_execution"
down_revision: Union[str, Sequence[str], None] = "0010_production_planning"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"
_TABLES = tuple(sorted(PRODUCTION_EXECUTION_TABLES))
_DROP_ORDER = (
    "production_sheet_issue",
    "production_dependency_override",
    "production_occurrence_event",
    "production_occurrence",
    "production_yield_measurement",
    "production_step_execution_event",
    "production_step_execution",
    "production_material_consumption",
    "production_weighing_verification",
    "production_weighing_entry",
    "production_weighing_session",
    "production_execution_policy",
)


def _uuid() -> sa.Column:
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _org() -> sa.Column:
    return sa.Column("organization_id", sa.Uuid(), nullable=False)


def _enable(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def _policy_org(table: str) -> None:
    op.execute(
        f"CREATE POLICY rls_{table}_org ON {table} FOR ALL USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )


def upgrade() -> None:
    op.drop_constraint("ck_production_batch_status", "production_batch", type_="check")
    op.create_check_constraint(
        "ck_production_batch_status",
        "production_batch",
        "status IN ('pending','in_weighing','ready','in_progress','on_hold',"
        "'completed','scrapped','cancelled','short_closed')",
    )
    op.drop_constraint("ck_production_code_counter_kind", "production_code_counter", type_="check")
    op.create_check_constraint(
        "ck_production_code_counter_kind",
        "production_code_counter",
        "kind IN ('plan','order','sheet')",
    )
    op.add_column("production_order", sa.Column("held_from_status", sa.Text(), nullable=True))
    op.add_column(
        "production_order", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("production_order", sa.Column("completed_by_user_id", sa.Uuid(), nullable=True))
    op.add_column(
        "production_order", sa.Column("short_closed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "production_order", sa.Column("short_closed_by_user_id", sa.Uuid(), nullable=True)
    )
    op.add_column("production_order", sa.Column("short_close_reason", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_production_order_completed_by",
        "production_order",
        "app_user",
        ["completed_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_production_order_short_closed_by",
        "production_order",
        "app_user",
        ["short_closed_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column("production_batch", sa.Column("held_from_status", sa.Text(), nullable=True))
    op.add_column(
        "production_batch", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "production_batch", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "production_batch", sa.Column("short_closed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "uq_production_batch_material_id_org",
        "production_batch_material",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "production_execution_policy",
        _uuid(),
        _org(),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("weighing_policy", sa.Text(), nullable=False),
        sa.Column("verification_policy", sa.Text(), nullable=False),
        sa.Column("absolute_tolerance", sa.Numeric(14, 6), nullable=True),
        sa.Column("percent_tolerance", sa.Numeric(14, 6), nullable=True),
        sa.Column("completion_tolerance", sa.Numeric(14, 6), nullable=False),
        sa.Column("allow_short_close", sa.Boolean(), nullable=False),
        sa.Column("require_manual_lot", sa.Boolean(), nullable=False),
        sa.Column("algorithm_code", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("frozen_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("policy_hash", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "weighing_policy IN ('required','optional','not_applicable')",
            name="ck_production_execution_policy_weighing",
        ),
        sa.CheckConstraint(
            "verification_policy IN ('none','second_person')",
            name="ck_production_execution_policy_verify",
        ),
        sa.CheckConstraint(
            "completion_tolerance >= 0", name="ck_production_execution_policy_completion"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["frozen_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("production_order_id", name="uq_production_execution_policy_order"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_execution_policy_id_org"),
    )

    op.create_table(
        "production_weighing_session",
        _uuid(),
        _org(),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("production_batch_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'open'"), nullable=False),
        sa.Column("opened_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint("status IN ('open','completed','cancelled')", name="ck_weighing_session_status"),
        sa.CheckConstraint("row_version >= 1", name="ck_weighing_session_version"),
        sa.ForeignKeyConstraint(["opened_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cancelled_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_weighing_session_id_org"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_production_weighing_session_idem"
        ),
    )
    op.create_index(
        "uq_production_weighing_session_open_batch",
        "production_weighing_session",
        ["production_batch_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    op.create_table(
        "production_weighing_entry",
        _uuid(),
        _org(),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("production_batch_material_id", sa.Uuid(), nullable=False),
        sa.Column("entry_type", sa.Text(), nullable=False),
        sa.Column("original_entry_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("measurement_unit_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("planned_quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("absolute_difference", sa.Numeric(14, 6), nullable=False),
        sa.Column("percent_difference", sa.Numeric(14, 6), nullable=False),
        sa.Column("within_tolerance", sa.Boolean(), nullable=False),
        sa.Column("lot_code", sa.Text(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("scale_reference", sa.Text(), nullable=True),
        sa.Column("operator_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "entry_type IN ('record','reversal','correction')", name="ck_weighing_entry_type"
        ),
        sa.CheckConstraint("quantity > 0", name="ck_weighing_entry_qty"),
        sa.ForeignKeyConstraint(["measurement_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operator_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["session_id", "organization_id"],
            ["production_weighing_session.id", "production_weighing_session.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_batch_material_id", "organization_id"],
            ["production_batch_material.id", "production_batch_material.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_weighing_entry_id_org"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_production_weighing_entry_idem"
        ),
    )
    op.create_foreign_key(
        "fk_weighing_entry_original",
        "production_weighing_entry",
        "production_weighing_entry",
        ["original_entry_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "production_weighing_verification",
        _uuid(),
        _org(),
        sa.Column("entry_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("verifier_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.CheckConstraint("decision IN ('accepted','rejected')", name="ck_weighing_verify_decision"),
        sa.ForeignKeyConstraint(["verifier_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["entry_id", "organization_id"],
            ["production_weighing_entry.id", "production_weighing_entry.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_weighing_verification_id_org"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_production_weighing_verification_idem"
        ),
    )

    op.create_table(
        "production_material_consumption",
        _uuid(),
        _org(),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("production_batch_id", sa.Uuid(), nullable=False),
        sa.Column("production_batch_material_id", sa.Uuid(), nullable=False),
        sa.Column("consumption_type", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("measurement_unit_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("weighing_entry_id", sa.Uuid(), nullable=True),
        sa.Column("lot_code", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("corrects_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "consumption_type IN ('consume','return','waste','correction')",
            name="ck_consumption_type",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_consumption_qty"),
        sa.ForeignKeyConstraint(["measurement_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_batch_material_id", "organization_id"],
            ["production_batch_material.id", "production_batch_material.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_material_consumption_id_org"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_production_material_consumption_idem"
        ),
    )
    op.create_foreign_key(
        "fk_consumption_weighing",
        "production_material_consumption",
        "production_weighing_entry",
        ["weighing_entry_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_consumption_corrects",
        "production_material_consumption",
        "production_material_consumption",
        ["corrects_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "production_step_execution",
        _uuid(),
        _org(),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("production_batch_id", sa.Uuid(), nullable=False),
        sa.Column("production_order_step_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operator_user_id", sa.Uuid(), nullable=True),
        sa.Column("measured_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("measured_temperature", sa.Numeric(6, 2), nullable=True),
        sa.Column("measured_time_seconds", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending','ready','in_progress','on_hold','completed','skipped','cancelled')",
            name="ck_step_execution_status",
        ),
        sa.ForeignKeyConstraint(["operator_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_order_step_id", "organization_id"],
            ["production_order_step.id", "production_order_step.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_step_execution_id_org"),
        sa.UniqueConstraint(
            "production_batch_id",
            "production_order_step_id",
            name="uq_production_step_execution_batch_step",
        ),
    )

    op.create_table(
        "production_step_execution_event",
        _uuid(),
        _org(),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.Text(), nullable=False),
        sa.Column("to_status", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["execution_id", "organization_id"],
            ["production_step_execution.id", "production_step_execution.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_step_execution_event_id_org"),
    )

    op.create_table(
        "production_yield_measurement",
        _uuid(),
        _org(),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("production_batch_id", sa.Uuid(), nullable=False),
        sa.Column("measurement_type", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(14, 6), nullable=False),
        sa.Column("measurement_unit_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reverses_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "measurement_type IN ('pre_bake_mass','post_bake_mass','good_units',"
            "'rejected_units','leftover','scrap','other')",
            name="ck_yield_type",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_yield_qty"),
        sa.ForeignKeyConstraint(["measurement_unit_id"], ["measurement_unit.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_yield_measurement_id_org"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_production_yield_measurement_idem"
        ),
    )
    op.create_foreign_key(
        "fk_yield_reverses",
        "production_yield_measurement",
        "production_yield_measurement",
        ["reverses_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "production_occurrence",
        _uuid(),
        _org(),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("production_batch_id", sa.Uuid(), nullable=True),
        sa.Column("production_order_step_id", sa.Uuid(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_blocking", sa.Boolean(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'open'"), nullable=False),
        sa.Column("opened_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column(
            "evidence_refs",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('material','substitution','equipment','quality','process',"
            "'safety','allergen','time','temperature','other')",
            name="ck_occurrence_category",
        ),
        sa.CheckConstraint(
            "severity IN ('low','medium','high','critical')", name="ck_occurrence_severity"
        ),
        sa.CheckConstraint("status IN ('open','resolved')", name="ck_occurrence_status"),
        sa.ForeignKeyConstraint(["opened_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_order_step_id", "organization_id"],
            ["production_order_step.id", "production_order_step.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_occurrence_id_org"),
    )

    op.create_table(
        "production_occurrence_event",
        _uuid(),
        _org(),
        sa.Column("occurrence_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("event_type IN ('opened','resolved')", name="ck_occurrence_event_type"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["occurrence_id", "organization_id"],
            ["production_occurrence.id", "production_occurrence.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_occurrence_event_id_org"),
    )

    op.create_table(
        "production_dependency_override",
        _uuid(),
        _org(),
        sa.Column("dependency_id", sa.Uuid(), nullable=False),
        sa.Column("predecessor_status", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["dependency_id", "organization_id"],
            ["production_order_dependency.id", "production_order_dependency.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_dependency_override_id_org"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_production_dependency_override_idem"
        ),
    )

    op.create_table(
        "production_sheet_issue",
        _uuid(),
        _org(),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("production_batch_id", sa.Uuid(), nullable=True),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("template_version", sa.Text(), nullable=False),
        sa.Column("canonical_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("payload_sha256", sa.Text(), nullable=False),
        sa.Column("issued_by_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("order_status_at_issue", sa.Text(), nullable=False),
        sa.Column("previous_issue_id", sa.Uuid(), nullable=True),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.CheckConstraint("purpose IN ('operational','contingency')", name="ck_sheet_purpose"),
        sa.CheckConstraint("issue_number >= 1", name="ck_sheet_number"),
        sa.ForeignKeyConstraint(["issued_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_batch_id", "organization_id"],
            ["production_batch.id", "production_batch.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_production_sheet_issue_id_org"),
        sa.UniqueConstraint("organization_id", "issue_number", name="uq_production_sheet_issue_number"),
        sa.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_production_sheet_issue_idem"
        ),
    )
    op.create_foreign_key(
        "fk_sheet_previous",
        "production_sheet_issue",
        "production_sheet_issue",
        ["previous_issue_id", "organization_id"],
        ["id", "organization_id"],
        ondelete="RESTRICT",
    )

    op.execute(
        """
        CREATE FUNCTION production_execution_no_delete() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'nao_excluivel';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION production_execution_append_only() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'registro_imutavel';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION production_execution_org_immutable() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.organization_id IS DISTINCT FROM NEW.organization_id THEN
            RAISE EXCEPTION 'organizacao_imutavel';
          END IF;
          RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION production_execution_policy_protect() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'nao_excluivel';
          END IF;
          IF OLD.organization_id IS DISTINCT FROM NEW.organization_id THEN
            RAISE EXCEPTION 'organizacao_imutavel';
          END IF;
          IF OLD.frozen_at IS NOT NULL THEN
            RAISE EXCEPTION 'politica_imutavel';
          END IF;
          RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_production_execution_policy_protect
        BEFORE UPDATE OR DELETE ON production_execution_policy
        FOR EACH ROW EXECUTE FUNCTION production_execution_policy_protect()
        """
    )
    for table in (
        "production_weighing_entry",
        "production_weighing_verification",
        "production_material_consumption",
        "production_step_execution_event",
        "production_yield_measurement",
        "production_occurrence_event",
        "production_dependency_override",
        "production_sheet_issue",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION production_execution_append_only()
            """
        )
    for table in (
        "production_weighing_session",
        "production_step_execution",
        "production_occurrence",
    ):
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_no_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION production_execution_no_delete()
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_org
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION production_execution_org_immutable()
            """
        )

    bind = op.get_bind()
    for role, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            if code not in PRODUCTION_EXECUTION_PERMISSIONS:
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO permission (code, description) "
                    "SELECT :code, :description WHERE NOT EXISTS "
                    "(SELECT 1 FROM permission WHERE code = :code)"
                ),
                {
                    "code": code,
                    "description": {
                        "production.weighing.record": "Registrar pesagem de produção",
                        "production.weighing.verify": "Conferir pesagem de produção",
                        "production.consumption.record": "Registrar consumo real de material",
                        "production.step.execute": "Executar etapa de produção",
                        "production.occurrence.record": "Registrar ocorrência de produção",
                        "production.occurrence.resolve": "Resolver ocorrência de produção",
                        "production.batch.complete": "Concluir batelada de produção",
                        "production.order.complete": "Concluir ordem de produção",
                        "production.order.short_close": "Encerrar ordem abaixo do planejado",
                        "production.sheet.issue": "Emitir registro auditável da ficha",
                        "production.traceability.read": "Ler rastreabilidade de produção",
                    }[code],
                },
            )
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
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO panne_runtime;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO panne_runtime;
          END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    for code in PRODUCTION_EXECUTION_PERMISSIONS:
        bind.execute(
            sa.text(
                "DELETE FROM role_permission WHERE permission_id IN "
                "(SELECT id FROM permission WHERE code = :code)"
            ),
            {"code": code},
        )
        bind.execute(sa.text("DELETE FROM permission WHERE code = :code"), {"code": code})
    for table in _DROP_ORDER:
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_org ON {table}")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        op.drop_table(table)
    op.execute("DROP FUNCTION IF EXISTS production_execution_policy_protect()")
    op.execute("DROP FUNCTION IF EXISTS production_execution_org_immutable()")
    op.execute("DROP FUNCTION IF EXISTS production_execution_append_only()")
    op.execute("DROP FUNCTION IF EXISTS production_execution_no_delete()")
    op.drop_index("uq_production_batch_material_id_org", table_name="production_batch_material")
    op.drop_constraint("fk_production_order_short_closed_by", "production_order", type_="foreignkey")
    op.drop_constraint("fk_production_order_completed_by", "production_order", type_="foreignkey")
    op.drop_column("production_order", "short_close_reason")
    op.drop_column("production_order", "short_closed_by_user_id")
    op.drop_column("production_order", "short_closed_at")
    op.drop_column("production_order", "completed_by_user_id")
    op.drop_column("production_order", "completed_at")
    op.drop_column("production_order", "held_from_status")
    op.drop_column("production_batch", "short_closed_at")
    op.drop_column("production_batch", "completed_at")
    op.drop_column("production_batch", "started_at")
    op.drop_column("production_batch", "held_from_status")
    op.execute("DELETE FROM production_code_counter WHERE kind = 'sheet'")
    op.drop_constraint("ck_production_code_counter_kind", "production_code_counter", type_="check")
    op.create_check_constraint(
        "ck_production_code_counter_kind",
        "production_code_counter",
        "kind IN ('plan','order')",
    )
    op.drop_constraint("ck_production_batch_status", "production_batch", type_="check")
    op.create_check_constraint(
        "ck_production_batch_status",
        "production_batch",
        "status IN ('pending','in_weighing','in_progress','on_hold','completed','scrapped','cancelled')",
    )
