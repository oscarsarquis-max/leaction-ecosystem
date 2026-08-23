"""Custos de produção e formação de preços.

Revision ID: 0018_costing_pricing
Revises: 0017_labeling_compliance
Create Date: 2026-08-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.modules.identity_organization.authorization import (
    COSTING_PERMISSION_DEFINITIONS,
    ROLE_PERMISSIONS,
)

revision: str = "0018_costing_pricing"
down_revision: Union[str, Sequence[str], None] = "0017_labeling_compliance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CODES = {code for code, _ in COSTING_PERMISSION_DEFINITIONS}
_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"
_TABLES = (
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
    "practiced_price",
    "pricing_decision",
    "costing_command",
)
_APPEND = (
    "costing_assumption",
    "costing_calculation",
    "costing_component",
    "costing_evidence",
    "costing_gap",
    "costing_invalidation",
    "pricing_simulation",
    "pricing_simulation_component",
    "pricing_decision",
    "costing_command",
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
        "costing_policy",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("status IN ('draft','published','retired')", name="ck_costing_policy_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_costing_policy_id_org", "costing_policy", ["id", "organization_id"], unique=True)
    op.create_index("uq_costing_policy_org_code", "costing_policy", ["organization_id", "code"], unique=True)

    op.create_table(
        "costing_policy_version",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("costing_policy_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("currency", sa.Text(), server_default="BRL", nullable=False),
        sa.Column("timezone", sa.Text(), server_default="America/Sao_Paulo", nullable=False),
        sa.Column("price_criterion", sa.Text(), nullable=False),
        sa.Column("use_gross_quantity", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("include_return", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("include_waste", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("include_leftover", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("include_scrap", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("use_sellable_yield", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "enabled_categories",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("allocation_notes", sa.Text(), nullable=True),
        sa.Column("presentation_decimals", sa.Integer(), server_default="2", nullable=False),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("algorithm_name", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("status IN ('draft','published','retired')", name="ck_costing_policy_version_status"),
        sa.CheckConstraint(
            "price_criterion IN ('latest_observed','explicit_item')",
            name="ck_costing_price_criterion",
        ),
        sa.ForeignKeyConstraint(
            ["costing_policy_id", "organization_id"],
            ["costing_policy.id", "costing_policy.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_costing_policy_version_id_org",
        "costing_policy_version",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_costing_policy_version_number",
        "costing_policy_version",
        ["costing_policy_id", "version_number"],
        unique=True,
    )

    op.create_table(
        "costing_assumption",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("costing_policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_code", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("nature", sa.Text(), nullable=False),
        sa.Column("behavior", sa.Text(), nullable=False),
        sa.Column("quality", sa.Text(), server_default="manual_assumption", nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["costing_policy_version_id", "organization_id"],
            ["costing_policy_version.id", "costing_policy_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_costing_assumption_id_org",
        "costing_assumption",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "costing_calculation",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=True),
        sa.Column("costing_policy_version_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("completeness", sa.Text(), nullable=False),
        sa.Column("technical_product_id", sa.Uuid(), nullable=True),
        sa.Column("formulation_id", sa.Uuid(), nullable=True),
        sa.Column("formulation_version_id", sa.Uuid(), nullable=True),
        sa.Column("scale_calculation_id", sa.Uuid(), nullable=True),
        sa.Column("production_order_id", sa.Uuid(), nullable=True),
        sa.Column("production_batch_id", sa.Uuid(), nullable=True),
        sa.Column("valuation_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("batch_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("mass_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("produced_unit_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("sellable_unit_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("produced_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("sellable_quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column(
            "snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("algorithm_name", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("kind IN ('planned','standard','actual')", name="ck_costing_kind"),
        sa.CheckConstraint(
            "completeness IN ('complete','partial','insufficient_data','invalidated')",
            name="ck_costing_completeness",
        ),
        sa.ForeignKeyConstraint(
            ["costing_policy_version_id", "organization_id"],
            ["costing_policy_version.id", "costing_policy_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_costing_calculation_id_org",
        "costing_calculation",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "costing_component",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("costing_calculation_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("origin_type", sa.Text(), nullable=False),
        sa.Column("origin_id", sa.Text(), nullable=False),
        sa.Column("nature", sa.Text(), nullable=False),
        sa.Column("behavior", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit_code", sa.Text(), nullable=True),
        sa.Column("rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("quality", sa.Text(), nullable=False),
        sa.Column("allocation_rule", sa.Text(), nullable=True),
        _now(),
        sa.ForeignKeyConstraint(
            ["costing_calculation_id", "organization_id"],
            ["costing_calculation.id", "costing_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_costing_component_id_org",
        "costing_component",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_costing_component_origin",
        "costing_component",
        ["costing_calculation_id", "origin_type", "origin_id"],
        unique=True,
    )

    op.create_table(
        "costing_evidence",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("costing_component_id", sa.Uuid(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        _now(),
        sa.ForeignKeyConstraint(
            ["costing_component_id", "organization_id"],
            ["costing_component.id", "costing_component.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_costing_evidence_id_org", "costing_evidence", ["id", "organization_id"], unique=True)

    op.create_table(
        "costing_gap",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("costing_calculation_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["costing_calculation_id", "organization_id"],
            ["costing_calculation.id", "costing_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_costing_gap_id_org", "costing_gap", ["id", "organization_id"], unique=True)

    op.create_table(
        "costing_invalidation",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("costing_calculation_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["costing_calculation_id", "organization_id"],
            ["costing_calculation.id", "costing_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_costing_invalidation_id_org",
        "costing_invalidation",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "pricing_simulation",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("costing_calculation_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("suggested_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("warning", sa.Text(), nullable=True),
        sa.Column(
            "snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["costing_calculation_id", "organization_id"],
            ["costing_calculation.id", "costing_calculation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_pricing_simulation_id_org",
        "pricing_simulation",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "pricing_simulation_component",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("pricing_simulation_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("rate", sa.Numeric(18, 6), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        _now(),
        sa.ForeignKeyConstraint(
            ["pricing_simulation_id", "organization_id"],
            ["pricing_simulation.id", "pricing_simulation.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_pricing_sim_component_id_org",
        "pricing_simulation_component",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "practiced_price",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=True),
        sa.Column("technical_product_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("currency", sa.Text(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pricing_simulation_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint(
            "status IN ('draft','approved','active','retired','cancelled')",
            name="ck_practiced_price_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_practiced_price_id_org", "practiced_price", ["id", "organization_id"], unique=True)

    op.create_table(
        "pricing_decision",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("practiced_price_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["practiced_price_id", "organization_id"],
            ["practiced_price.id", "practiced_price.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_pricing_decision_id_org", "pricing_decision", ["id", "organization_id"], unique=True)

    op.create_table(
        "costing_command",
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
    op.create_index("uq_costing_command_id_org", "costing_command", ["id", "organization_id"], unique=True)
    op.create_index(
        "uq_costing_command_idempotency",
        "costing_command",
        ["organization_id", "idempotency_key"],
        unique=True,
    )

    for table in _TABLES:
        _enable_rls(table)

    op.execute(
        """
        CREATE FUNCTION panne_costing_append_only() RETURNS trigger AS $$
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
            FOR EACH ROW EXECUTE FUNCTION panne_costing_append_only();
            """
        )
    op.execute(
        """
        CREATE FUNCTION panne_costing_policy_version_guard() RETURNS trigger AS $$
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
        CREATE TRIGGER costing_policy_version_guard
        BEFORE UPDATE ON costing_policy_version
        FOR EACH ROW EXECUTE FUNCTION panne_costing_policy_version_guard();
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
    for code, description in COSTING_PERMISSION_DEFINITIONS:
        bind.execute(
            sa.text(
                "INSERT INTO permission (code, description) "
                "SELECT :code, :description WHERE NOT EXISTS "
                "(SELECT 1 FROM permission WHERE code = :code)"
            ),
            {"code": code, "description": description},
        )
    for role, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            if code not in _CODES:
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

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE
              ON costing_policy, costing_policy_version, costing_assumption,
                 costing_calculation, costing_component, costing_evidence,
                 costing_gap, costing_invalidation, pricing_simulation,
                 pricing_simulation_component, practiced_price, pricing_decision,
                 costing_command
              TO panne_runtime;
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
    op.execute("DROP TRIGGER IF EXISTS costing_policy_version_guard ON costing_policy_version")
    op.execute("DROP FUNCTION IF EXISTS panne_costing_policy_version_guard()")
    op.execute("DROP FUNCTION IF EXISTS panne_costing_append_only()")
    for table in reversed(_TABLES):
        op.drop_table(table)
