"""API de produção: papéis múltiplos e conversão de massa.

Revision ID: 0012_production_api_roles
Revises: 0011_production_execution
Create Date: 2026-08-22
"""

# ruff: noqa: E501

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from app.modules.identity_organization.authorization import API_PERMISSIONS, ROLE_PERMISSIONS

revision: str = "0012_production_api_roles"
down_revision: Union[str, Sequence[str], None] = "0011_production_execution"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"
_CONVERSION_TABLES = ("production_weighing_entry", "production_material_consumption")
_PERMISSION_TEXT = {
    "membership.role.manage": "Conceder e revogar papéis da associação",
    "production.order.policy_adopt": "Adotar política em ordem liberada sem fatos",
}


def _enable(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    op.create_index(
        "uq_membership_id_org",
        "organization_membership",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_table(
        "organization_membership_role",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("membership_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("granted_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["membership_id", "organization_id"],
            ["organization_membership.id", "organization_membership.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "role IN ("
            "'owner','administrator','technical_responsible','production','commercial',"
            "'viewer','organization_owner','organization_admin','production_manager',"
            "'baker_operator','regulatory_reviewer','restricted'"
            ")",
            name="ck_membership_role_assignment",
        ),
    )
    op.create_index(
        "uq_membership_role_id_org",
        "organization_membership_role",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_membership_role_active",
        "organization_membership_role",
        ["membership_id", "role"],
        unique=True,
        postgresql_where=sa.text("revoked_at IS NULL"),
    )
    op.execute(
        """
        INSERT INTO organization_membership_role (
            organization_id, membership_id, role, granted_at, reason
        )
        SELECT organization_id, id, role, created_at, 'migracao_0012'
        FROM organization_membership
        """
    )
    _enable("organization_membership_role")
    op.execute(
        """
        CREATE POLICY rls_organization_membership_role_select
        ON organization_membership_role FOR SELECT
        USING (
          organization_id = panne_current_org_id()
          OR EXISTS (
            SELECT 1 FROM organization_membership m
            WHERE m.id = organization_membership_role.membership_id
              AND m.user_id = panne_current_user_id()
              AND m.status = 'active'
          )
        )
        """
    )
    op.execute(
        "CREATE POLICY rls_organization_membership_role_write "
        "ON organization_membership_role FOR INSERT "
        f"WITH CHECK ({_ORG_EQ})"
    )
    op.execute(
        "CREATE POLICY rls_organization_membership_role_update "
        "ON organization_membership_role FOR UPDATE "
        f"USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )

    for table in _CONVERSION_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
        op.add_column(table, sa.Column("canonical_quantity", sa.Numeric(14, 6), nullable=True))
        op.add_column(table, sa.Column("canonical_unit_id", sa.Uuid(), nullable=True))
        op.add_column(table, sa.Column("canonical_unit_code", sa.Text(), nullable=True))
        op.add_column(table, sa.Column("conversion_factor", sa.Numeric(28, 10), nullable=True))
        op.add_column(table, sa.Column("conversion_source", sa.Text(), nullable=True))
        op.add_column(table, sa.Column("conversion_version", sa.Text(), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_canonical_unit",
            table,
            "measurement_unit",
            ["canonical_unit_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.execute(
            f"""
            UPDATE {table}
            SET canonical_quantity = quantity,
                canonical_unit_id = measurement_unit_id,
                canonical_unit_code = unit_code,
                conversion_factor = 1,
                conversion_source = 'legacy_identity',
                conversion_version = '1'
            """
        )
        op.alter_column(table, "canonical_quantity", nullable=False)
        op.alter_column(table, "canonical_unit_id", nullable=False)
        op.alter_column(table, "canonical_unit_code", nullable=False)
        op.alter_column(table, "conversion_factor", nullable=False)
        op.alter_column(table, "conversion_source", nullable=False)
        op.alter_column(table, "conversion_version", nullable=False)
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION production_execution_append_only()
            """
        )

    bind = op.get_bind()
    for role, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            if code not in API_PERMISSIONS:
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO permission (code, description) "
                    "SELECT :code, :description WHERE NOT EXISTS "
                    "(SELECT 1 FROM permission WHERE code = :code)"
                ),
                {"code": code, "description": _PERMISSION_TEXT[code]},
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
    for code in API_PERMISSIONS:
        bind.execute(
            sa.text(
                "DELETE FROM role_permission WHERE permission_id IN "
                "(SELECT id FROM permission WHERE code = :code)"
            ),
            {"code": code},
        )
        bind.execute(sa.text("DELETE FROM permission WHERE code = :code"), {"code": code})

    for table in _CONVERSION_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_append_only ON {table}")
        op.drop_constraint(f"fk_{table}_canonical_unit", table, type_="foreignkey")
        op.drop_column(table, "conversion_version")
        op.drop_column(table, "conversion_source")
        op.drop_column(table, "conversion_factor")
        op.drop_column(table, "canonical_unit_code")
        op.drop_column(table, "canonical_unit_id")
        op.drop_column(table, "canonical_quantity")
        op.execute(
            f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION production_execution_append_only()
            """
        )

    op.execute("DROP POLICY IF EXISTS rls_organization_membership_role_select ON organization_membership_role")
    op.execute("DROP POLICY IF EXISTS rls_organization_membership_role_write ON organization_membership_role")
    op.execute("DROP POLICY IF EXISTS rls_organization_membership_role_update ON organization_membership_role")
    op.execute("DROP POLICY IF EXISTS rls_organization_membership_role_org ON organization_membership_role")
    op.execute("ALTER TABLE organization_membership_role NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE organization_membership_role DISABLE ROW LEVEL SECURITY")
    op.drop_table("organization_membership_role")
    op.drop_index("uq_membership_id_org", table_name="organization_membership")
