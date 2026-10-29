"""Relatórios e painéis gerenciais.

Revision ID: 0019_reporting_analytics
Revises: 0018_costing_pricing
Create Date: 2026-08-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from app.modules.identity_organization.authorization import (
    REPORTING_PERMISSION_DEFINITIONS,
    ROLE_PERMISSIONS,
)
from sqlalchemy.dialects import postgresql

revision: str = "0019_reporting_analytics"
down_revision: Union[str, Sequence[str], None] = "0018_costing_pricing"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CODES = {code for code, _ in REPORTING_PERMISSION_DEFINITIONS}
_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"
_TABLES = (
    "reporting_saved_view",
    "reporting_dashboard_preference",
    "reporting_execution",
    "reporting_snapshot",
    "reporting_coverage_item",
    "reporting_export",
    "reporting_command",
)
_APPEND = (
    "reporting_execution",
    "reporting_snapshot",
    "reporting_coverage_item",
    "reporting_export",
    "reporting_command",
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
        "reporting_saved_view",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("report_code", sa.Text(), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        _now(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_reporting_saved_view_id_org", "reporting_saved_view", ["id", "organization_id"], unique=True)
    op.create_index("uq_reporting_saved_view_org_code", "reporting_saved_view", ["organization_id", "code"], unique=True)

    op.create_table(
        "reporting_dashboard_preference",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("report_code", sa.Text(), nullable=False),
        sa.Column("layout", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        _now(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_reporting_pref_id_org", "reporting_dashboard_preference", ["id", "organization_id"], unique=True)
    op.create_index(
        "uq_reporting_pref_user_report",
        "reporting_dashboard_preference",
        ["organization_id", "user_id", "report_code"],
        unique=True,
    )

    op.create_table(
        "reporting_execution",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("report_code", sa.Text(), nullable=False),
        sa.Column("report_version", sa.Text(), nullable=False),
        sa.Column("query_version", sa.Text(), nullable=False),
        sa.Column("metrics_version", sa.Text(), nullable=False),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_cutoff_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completeness", sa.Text(), nullable=False),
        sa.Column("coverage", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint(
            "completeness IN ('complete','partial','insufficient_data')",
            name="ck_reporting_execution_completeness",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_reporting_execution_id_org", "reporting_execution", ["id", "organization_id"], unique=True)
    op.create_index("ix_reporting_execution_org_created", "reporting_execution", ["organization_id", "created_at"])

    op.create_table(
        "reporting_snapshot",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("reporting_execution_id", sa.Uuid(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["reporting_execution_id", "organization_id"],
            ["reporting_execution.id", "reporting_execution.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_reporting_snapshot_id_org", "reporting_snapshot", ["id", "organization_id"], unique=True)
    op.create_index("uq_reporting_snapshot_execution", "reporting_snapshot", ["reporting_execution_id"], unique=True)

    op.create_table(
        "reporting_coverage_item",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("reporting_execution_id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=False),
        sa.Column("universe", sa.Integer(), nullable=False),
        sa.Column("valid_count", sa.Integer(), nullable=False),
        sa.Column("missing_count", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["reporting_execution_id", "organization_id"],
            ["reporting_execution.id", "reporting_execution.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_reporting_coverage_id_org", "reporting_coverage_item", ["id", "organization_id"], unique=True)

    op.create_table(
        "reporting_export",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("reporting_execution_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint("kind IN ('csv','html')", name="ck_reporting_export_kind"),
        sa.ForeignKeyConstraint(
            ["reporting_execution_id", "organization_id"],
            ["reporting_execution.id", "reporting_execution.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_reporting_export_id_org", "reporting_export", ["id", "organization_id"], unique=True)

    op.create_table(
        "reporting_command",
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
    op.create_index("uq_reporting_command_id_org", "reporting_command", ["id", "organization_id"], unique=True)
    op.create_index("uq_reporting_command_idempotency", "reporting_command", ["organization_id", "idempotency_key"], unique=True)

    for table in _TABLES:
        _enable_rls(table)

    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_reporting_append_only() RETURNS trigger AS $$
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
            FOR EACH ROW EXECUTE FUNCTION panne_reporting_append_only();
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_forbid_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_physical_delete();
            """
        )
    for table in ("reporting_saved_view", "reporting_dashboard_preference"):
        op.execute(
            f"""
            CREATE TRIGGER {table}_forbid_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_physical_delete();
            """
        )

    bind = op.get_bind()
    for code, description in REPORTING_PERMISSION_DEFINITIONS:
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
              ON reporting_saved_view, reporting_dashboard_preference, reporting_execution,
                 reporting_snapshot, reporting_coverage_item, reporting_export, reporting_command
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
    op.execute("DROP FUNCTION IF EXISTS panne_reporting_append_only()")
    for table in reversed(_TABLES):
        op.drop_table(table)
