"""Estoque quantitativo e compras internas.

Revision ID: 0020_inventory_procurement
Revises: 0019_reporting_analytics
Create Date: 2026-08-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from app.modules.identity_organization.authorization import (
    INVENTORY_PERMISSION_DEFINITIONS,
    PROCUREMENT_PERMISSION_DEFINITIONS,
    ROLE_PERMISSIONS,
)
from sqlalchemy.dialects import postgresql

revision: str = "0020_inventory_procurement"
down_revision: Union[str, Sequence[str], None] = "0019_reporting_analytics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFINITIONS = INVENTORY_PERMISSION_DEFINITIONS + PROCUREMENT_PERMISSION_DEFINITIONS
_CODES = {code for code, _ in _DEFINITIONS}
_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"
_TABLES = (
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
)
_APPEND = (
    "inventory_movement",
    "inventory_reservation_allocation",
    "inventory_pick_line",
    "inventory_count_scope",
    "inventory_count_entry",
    "inventory_count_review",
    "inventory_replenishment_suggestion",
    "inventory_replenishment_item",
    "procurement_order_revision",
    "inventory_command",
)


def _uuid() -> sa.Column:
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _now() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY rls_{table}_org ON {table} FOR ALL "
        f"USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )


def upgrade() -> None:
    op.create_table(
        "inventory_policy",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("status IN ('draft','published','retired')", name="ck_inventory_policy_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_policy_id_org", "inventory_policy", ["id", "organization_id"], unique=True)
    op.create_index("uq_inventory_policy_org_code", "inventory_policy", ["organization_id", "code"], unique=True)

    op.create_table(
        "inventory_policy_version",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_policy_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("allow_negative_balance", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("lot_mode", sa.Text(), server_default="optional", nullable=False),
        sa.Column("expiry_required", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("lot_consumption", sa.Text(), server_default="fefo_suggest", nullable=False),
        sa.Column("receipt_tolerance_percent", sa.Numeric(8, 4), server_default="0", nullable=False),
        sa.Column("count_tolerance_percent", sa.Numeric(8, 4), server_default="0", nullable=False),
        sa.Column("reserve_on_release", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("cancelled_order_treatment", sa.Text(), server_default="release_reservation", nullable=False),
        sa.Column("return_restores_available", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("waste_reduces_physical", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("adjust_requires_approval", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("lock_location_on_count", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("expiry_alert_days", sa.Integer(), server_default="7", nullable=False),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("algorithm_name", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("status IN ('draft','published','retired')", name="ck_inventory_policy_ver_status"),
        sa.CheckConstraint("lot_mode IN ('required','optional','not_applicable')", name="ck_inventory_lot_mode"),
        sa.CheckConstraint("lot_consumption IN ('manual','fefo_suggest')", name="ck_inventory_lot_consumption"),
        sa.CheckConstraint(
            "cancelled_order_treatment IN ('release_reservation')",
            name="ck_inventory_cancel_treatment",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_policy_id", "organization_id"],
            ["inventory_policy.id", "inventory_policy.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_policy_version_id_org",
        "inventory_policy_version",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_inventory_policy_version_number",
        "inventory_policy_version",
        ["inventory_policy_id", "version_number"],
        unique=True,
    )

    op.create_table(
        "inventory_location",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("responsible_user_id", sa.Uuid(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("kind IN ('warehouse','production','quarantine','other')", name="ck_inventory_location_kind"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_inventory_location_status"),
        sa.ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_location_id_org", "inventory_location", ["id", "organization_id"], unique=True)
    op.create_index("uq_inventory_location_org_code", "inventory_location", ["organization_id", "code"], unique=True)

    op.create_table(
        "inventory_item",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ingredient_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("lot_control", sa.Text(), server_default="optional", nullable=False),
        sa.Column("expiry_control", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reorder_point", sa.Numeric(18, 6), nullable=True),
        sa.Column("safety_stock", sa.Numeric(18, 6), nullable=True),
        sa.Column("target_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("preferred_supplier_id", sa.Uuid(), nullable=True),
        sa.Column("preferred_supplier_item_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("lot_control IN ('required','optional','not_applicable')", name="ck_inventory_item_lot"),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_inventory_item_status"),
        sa.ForeignKeyConstraint(
            ["ingredient_id", "organization_id"],
            ["ingredient.id", "ingredient.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["preferred_supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_item_id_org", "inventory_item", ["id", "organization_id"], unique=True)
    op.create_index(
        "uq_inventory_item_ingredient",
        "inventory_item",
        ["organization_id", "ingredient_id"],
        unique=True,
    )

    op.create_table(
        "inventory_lot",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_location_id", sa.Uuid(), nullable=False),
        sa.Column("internal_lot_code", sa.Text(), nullable=False),
        sa.Column("supplier_lot_code", sa.Text(), nullable=True),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("supplier_item_id", sa.Uuid(), nullable=True),
        sa.Column("manufactured_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("procurement_receipt_id", sa.Uuid(), nullable=True),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("received_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("status", sa.Text(), server_default="available", nullable=False),
        sa.Column("block_reason", sa.Text(), nullable=True),
        sa.Column("blocked_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint(
            "status IN ('available','quarantined','blocked','expired','exhausted','closed')",
            name="ck_inventory_lot_status",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id", "organization_id"],
            ["inventory_item.id", "inventory_item.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_location_id", "organization_id"],
            ["inventory_location.id", "inventory_location.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_lot_id_org", "inventory_lot", ["id", "organization_id"], unique=True)
    op.create_index("uq_inventory_lot_internal", "inventory_lot", ["organization_id", "internal_lot_code"], unique=True)
    op.create_index("ix_inventory_lot_expiry", "inventory_lot", ["organization_id", "expires_on", "status"])

    op.create_table(
        "inventory_movement",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_lot_id", sa.Uuid(), nullable=True),
        sa.Column("from_location_id", sa.Uuid(), nullable=True),
        sa.Column("to_location_id", sa.Uuid(), nullable=True),
        sa.Column("movement_type", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("canonical_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("conversion_factor", sa.Numeric(28, 10), nullable=False),
        sa.Column("sign", sa.Integer(), nullable=False),
        sa.Column("nature", sa.Text(), nullable=False),
        sa.Column("origin_type", sa.Text(), nullable=False),
        sa.Column("origin_id", sa.Uuid(), nullable=True),
        sa.Column("production_order_id", sa.Uuid(), nullable=True),
        sa.Column("production_batch_id", sa.Uuid(), nullable=True),
        sa.Column("production_material_consumption_id", sa.Uuid(), nullable=True),
        sa.Column("procurement_receipt_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_count_session_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.Uuid(), nullable=True),
        sa.Column("causation_id", sa.Uuid(), nullable=True),
        sa.Column("reverses_id", sa.Uuid(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=False),
        _now(),
        sa.CheckConstraint(
            "movement_type IN ('receipt','transfer_out','transfer_in','production_consume',"
            "'production_return','waste','supplier_return','adjust_plus','adjust_minus','reverse','opening')",
            name="ck_inventory_movement_type",
        ),
        sa.CheckConstraint("sign IN (-1, 1)", name="ck_inventory_movement_sign"),
        sa.CheckConstraint("nature IN ('physical_in','physical_out')", name="ck_inventory_movement_nature"),
        sa.ForeignKeyConstraint(
            ["inventory_item_id", "organization_id"],
            ["inventory_item.id", "inventory_item.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_policy_version_id", "organization_id"],
            ["inventory_policy_version.id", "inventory_policy_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_movement_id_org", "inventory_movement", ["id", "organization_id"], unique=True)
    op.create_index(
        "ix_inventory_movement_item",
        "inventory_movement",
        ["organization_id", "inventory_item_id", "created_at"],
    )
    op.create_index("ix_inventory_movement_lot", "inventory_movement", ["organization_id", "inventory_lot_id"])

    op.create_table(
        "inventory_balance",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_location_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_lot_id", sa.Uuid(), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("physical_quantity", sa.Numeric(18, 6), server_default="0", nullable=False),
        sa.Column("reserved_quantity", sa.Numeric(18, 6), server_default="0", nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        _now(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_balance_id_org", "inventory_balance", ["id", "organization_id"], unique=True)
    op.create_index(
        "uq_inventory_balance_grain",
        "inventory_balance",
        ["organization_id", "inventory_location_id", "inventory_item_id", "inventory_lot_id"],
        unique=True,
    )
    op.create_index("ix_inventory_balance_item", "inventory_balance", ["organization_id", "inventory_item_id"])

    op.create_table(
        "inventory_reservation",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("production_batch_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("required_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("reserved_quantity", sa.Numeric(18, 6), server_default="0", nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("adopted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("shortage_quantity", sa.Numeric(18, 6), server_default="0", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("inventory_policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint(
            "status IN ('pending','partial','reserved','released','consumed','cancelled','expired')",
            name="ck_inventory_reservation_status",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id", "organization_id"],
            ["inventory_item.id", "inventory_item.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_reservation_id_org", "inventory_reservation", ["id", "organization_id"], unique=True)
    op.create_index(
        "ix_inventory_reservation_order",
        "inventory_reservation",
        ["organization_id", "production_order_id", "status"],
    )

    op.create_table(
        "inventory_reservation_allocation",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_reservation_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_lot_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_location_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["inventory_reservation_id", "organization_id"],
            ["inventory_reservation.id", "inventory_reservation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_res_alloc_id_org",
        "inventory_reservation_allocation",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "inventory_pick",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("public_code", sa.Text(), nullable=False),
        sa.Column("production_order_id", sa.Uuid(), nullable=False),
        sa.Column("production_batch_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("inventory_policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("status IN ('draft','confirmed','cancelled')", name="ck_inventory_pick_status"),
        sa.ForeignKeyConstraint(
            ["production_order_id", "organization_id"],
            ["production_order.id", "production_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_pick_id_org", "inventory_pick", ["id", "organization_id"], unique=True)
    op.create_index("uq_inventory_pick_code", "inventory_pick", ["organization_id", "public_code"], unique=True)

    op.create_table(
        "inventory_pick_line",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_pick_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_lot_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_location_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("suggested", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("substituted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        _now(),
        sa.ForeignKeyConstraint(
            ["inventory_pick_id", "organization_id"],
            ["inventory_pick.id", "inventory_pick.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_pick_line_id_org", "inventory_pick_line", ["id", "organization_id"], unique=True)

    op.create_table(
        "inventory_consumption_posting",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("production_material_consumption_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_movement_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("status IN ('pending','posted','failed')", name="ck_inventory_posting_status"),
        sa.ForeignKeyConstraint(
            ["production_material_consumption_id", "organization_id"],
            ["production_material_consumption.id", "production_material_consumption.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_cons_post_id_org",
        "inventory_consumption_posting",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_inventory_cons_post_origin",
        "inventory_consumption_posting",
        ["organization_id", "production_material_consumption_id"],
        unique=True,
    )

    op.create_table(
        "inventory_count_session",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("public_code", sa.Text(), nullable=False),
        sa.Column("inventory_location_id", sa.Uuid(), nullable=False),
        sa.Column("cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("require_second_count", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("lock_location", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("inventory_policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint(
            "status IN ('draft','scoped','counting','review','approved','closed')",
            name="ck_inventory_count_status",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_location_id", "organization_id"],
            ["inventory_location.id", "inventory_location.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_count_id_org", "inventory_count_session", ["id", "organization_id"], unique=True)
    op.create_index("uq_inventory_count_code", "inventory_count_session", ["organization_id", "public_code"], unique=True)

    op.create_table(
        "inventory_count_scope",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_count_session_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_lot_id", sa.Uuid(), nullable=False),
        sa.Column("expected_quantity", sa.Numeric(18, 6), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["inventory_count_session_id", "organization_id"],
            ["inventory_count_session.id", "inventory_count_session.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_count_scope_id_org",
        "inventory_count_scope",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "inventory_count_entry",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_count_session_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_count_scope_id", sa.Uuid(), nullable=False),
        sa.Column("pass_number", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("pass_number IN (1, 2)", name="ck_inventory_count_pass"),
        sa.ForeignKeyConstraint(
            ["inventory_count_session_id", "organization_id"],
            ["inventory_count_session.id", "inventory_count_session.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_count_entry_id_org",
        "inventory_count_entry",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "inventory_count_review",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_count_session_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["inventory_count_session_id", "organization_id"],
            ["inventory_count_session.id", "inventory_count_session.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_count_review_id_org",
        "inventory_count_review",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "inventory_replenishment_suggestion",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("public_code", sa.Text(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inventory_policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_replenish_id_org",
        "inventory_replenishment_suggestion",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_inventory_replenish_code",
        "inventory_replenishment_suggestion",
        ["organization_id", "public_code"],
        unique=True,
    )

    op.create_table(
        "inventory_replenishment_item",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_replenishment_suggestion_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("physical_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("reserved_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("available_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("in_transit_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("planned_demand", sa.Numeric(18, 6), nullable=True),
        sa.Column("suggested_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("formula", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("gaps", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["inventory_replenishment_suggestion_id", "organization_id"],
            ["inventory_replenishment_suggestion.id", "inventory_replenishment_suggestion.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_replenish_item_id_org",
        "inventory_replenishment_item",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "procurement_requisition",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("public_code", sa.Text(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_location_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("needed_by", sa.Date(), nullable=True),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("origin_type", sa.Text(), nullable=False),
        sa.Column("origin_id", sa.Uuid(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint(
            "status IN ('draft','submitted','approved','rejected','converted','cancelled')",
            name="ck_procurement_req_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_procurement_req_id_org", "procurement_requisition", ["id", "organization_id"], unique=True)
    op.create_index("uq_procurement_req_code", "procurement_requisition", ["organization_id", "public_code"], unique=True)

    op.create_table(
        "procurement_requisition_item",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("procurement_requisition_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["procurement_requisition_id", "organization_id"],
            ["procurement_requisition.id", "procurement_requisition.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_procurement_req_item_id_org",
        "procurement_requisition_item",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "procurement_quotation",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("evidence_ref", sa.Text(), nullable=True),
        sa.Column("currency", sa.Text(), server_default="BRL", nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("currency = 'BRL'", name="ck_procurement_quote_currency"),
        sa.ForeignKeyConstraint(
            ["supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_procurement_quote_id_org", "procurement_quotation", ["id", "organization_id"], unique=True)

    op.create_table(
        "procurement_quotation_item",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("procurement_quotation_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_item_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("package_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.Text(), server_default="BRL", nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["procurement_quotation_id", "organization_id"],
            ["procurement_quotation.id", "procurement_quotation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_procurement_quote_item_id_org",
        "procurement_quotation_item",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "procurement_order",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("public_code", sa.Text(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_location_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("currency", sa.Text(), server_default="BRL", nullable=False),
        sa.Column("expected_at", sa.Date(), nullable=True),
        sa.Column("current_revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint(
            "status IN ('draft','approved','issued','partially_received','received','cancelled','closed')",
            name="ck_procurement_order_status",
        ),
        sa.CheckConstraint("currency = 'BRL'", name="ck_procurement_order_currency"),
        sa.ForeignKeyConstraint(
            ["supplier_id", "organization_id"],
            ["supplier.id", "supplier.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_procurement_order_id_org", "procurement_order", ["id", "organization_id"], unique=True)
    op.create_index("uq_procurement_order_code", "procurement_order", ["organization_id", "public_code"], unique=True)

    op.create_table(
        "procurement_order_revision",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("procurement_order_id", sa.Uuid(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["procurement_order_id", "organization_id"],
            ["procurement_order.id", "procurement_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_procurement_order_rev_id_org",
        "procurement_order_revision",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_procurement_order_rev_number",
        "procurement_order_revision",
        ["procurement_order_id", "revision_number"],
        unique=True,
    )

    op.create_table(
        "procurement_order_item",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("procurement_order_id", sa.Uuid(), nullable=False),
        sa.Column("procurement_order_revision_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_item_id", sa.Uuid(), nullable=True),
        sa.Column("procurement_requisition_item_id", sa.Uuid(), nullable=True),
        sa.Column("procurement_quotation_item_id", sa.Uuid(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("package_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.Text(), server_default="BRL", nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["procurement_order_id", "organization_id"],
            ["procurement_order.id", "procurement_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["procurement_order_revision_id", "organization_id"],
            ["procurement_order_revision.id", "procurement_order_revision.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_procurement_order_item_id_org",
        "procurement_order_item",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "procurement_receipt",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("public_code", sa.Text(), nullable=False),
        sa.Column("procurement_order_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_location_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("evidence_ref", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("status IN ('draft','posted','cancelled')", name="ck_procurement_receipt_status"),
        sa.ForeignKeyConstraint(
            ["procurement_order_id", "organization_id"],
            ["procurement_order.id", "procurement_order.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_procurement_receipt_id_org", "procurement_receipt", ["id", "organization_id"], unique=True)
    op.create_index(
        "uq_procurement_receipt_code",
        "procurement_receipt",
        ["organization_id", "public_code"],
        unique=True,
    )

    op.create_table(
        "procurement_receipt_item",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("procurement_receipt_id", sa.Uuid(), nullable=False),
        sa.Column("procurement_order_item_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("supplier_lot_code", sa.Text(), nullable=True),
        sa.Column("manufactured_on", sa.Date(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("observed_unit_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("currency", sa.Text(), server_default="BRL", nullable=False),
        sa.Column("inventory_lot_id", sa.Uuid(), nullable=True),
        sa.Column("divergence", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["procurement_receipt_id", "organization_id"],
            ["procurement_receipt.id", "procurement_receipt.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_procurement_receipt_item_id_org",
        "procurement_receipt_item",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "procurement_return",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("public_code", sa.Text(), nullable=False),
        sa.Column("procurement_receipt_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_lot_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("inventory_movement_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), server_default="posted", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("status IN ('draft','posted')", name="ck_procurement_return_status"),
        sa.ForeignKeyConstraint(
            ["procurement_receipt_id", "organization_id"],
            ["procurement_receipt.id", "procurement_receipt.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_procurement_return_id_org", "procurement_return", ["id", "organization_id"], unique=True)
    op.create_index("uq_procurement_return_code", "procurement_return", ["organization_id", "public_code"], unique=True)

    op.create_table(
        "inventory_command",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("payload_digest", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_inventory_command_id_org", "inventory_command", ["id", "organization_id"], unique=True)
    op.create_index(
        "uq_inventory_command_idempotency",
        "inventory_command",
        ["organization_id", "idempotency_key"],
        unique=True,
    )

    op.create_table(
        "inventory_code_counter",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("last_value", sa.Integer(), server_default="0", nullable=False),
        _now(),
        sa.CheckConstraint(
            "kind IN ('LOT','REQ','PO','RCP','RET','PICK','CNT','RPL')",
            name="ck_inventory_code_kind",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_code_counter_id_org",
        "inventory_code_counter",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_inventory_code_counter_kind",
        "inventory_code_counter",
        ["organization_id", "kind"],
        unique=True,
    )

    for table in _TABLES:
        _enable_rls(table)

    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_inventory_append_only() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'append_only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in _APPEND:
        op.execute(
            f"""
            CREATE TRIGGER {table}_append_only
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_inventory_append_only();
            """
        )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_inventory_published_immutable() RETURNS trigger AS $$
        BEGIN
          IF OLD.status = 'published' THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER inventory_policy_version_published_immutable
        BEFORE UPDATE ON inventory_policy_version
        FOR EACH ROW EXECUTE FUNCTION panne_inventory_published_immutable();
        """
    )
    for table in _TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_forbid_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_physical_delete();
            """
        )

    bind = op.get_bind()
    for code, description in _DEFINITIONS:
        bind.execute(
            sa.text(
                "INSERT INTO permission (code, description) "
                "SELECT :code, :description WHERE NOT EXISTS "
                "(SELECT 1 FROM permission WHERE code = :code)"
            ),
            {"code": code, "description": description},
        )
    reporting_inventory = "reporting.inventory.read"
    bind.execute(
        sa.text(
            "INSERT INTO permission (code, description) "
            "SELECT :code, :description WHERE NOT EXISTS "
            "(SELECT 1 FROM permission WHERE code = :code)"
        ),
        {"code": reporting_inventory, "description": "Ler relatórios de estoque e compras"},
    )
    grant_codes = set(_CODES) | {reporting_inventory}
    for role, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            if code not in grant_codes:
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

    table_list = ", ".join(_TABLES)
    op.execute(
        f"""
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON {table_list} TO panne_runtime;
          END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    for code in _CODES:
        bind.execute(
            sa.text(
                "DELETE FROM role_permission WHERE permission_id IN "
                "(SELECT id FROM permission WHERE code = :code)"
            ),
            {"code": code},
        )
        bind.execute(sa.text("DELETE FROM permission WHERE code = :code"), {"code": code})
    for table in reversed(_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_forbid_delete ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_org ON {table}")
    op.execute("DROP TRIGGER IF EXISTS inventory_policy_version_published_immutable ON inventory_policy_version")
    op.execute("DROP FUNCTION IF EXISTS panne_inventory_published_immutable()")
    op.execute("DROP FUNCTION IF EXISTS panne_inventory_append_only()")
    for table in reversed(_TABLES):
        op.drop_table(table)
