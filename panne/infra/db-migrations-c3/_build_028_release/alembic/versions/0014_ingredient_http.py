"""API de ingredientes: permissões, row_version, aposentadoria e idempotência.

Revision ID: 0014_ingredient_http
Revises: 0013_legacy_role_label
Create Date: 2026-08-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from app.modules.identity_organization.authorization import (
    INGREDIENT_PERMISSION_DEFINITIONS,
    ROLE_PERMISSIONS,
)

revision: str = "0014_ingredient_http"
down_revision: Union[str, Sequence[str], None] = "0013_legacy_role_label"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CODES = {code for code, _ in INGREDIENT_PERMISSION_DEFINITIONS}
_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"


def upgrade() -> None:
    for table in ("ingredient", "ingredient_version", "supplier", "supplier_item"):
        op.add_column(
            table,
            sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        )

    op.create_table(
        "ingredient_command",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("payload_digest", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_ingredient_command_idempotency",
        ),
    )
    op.execute("ALTER TABLE ingredient_command ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ingredient_command FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY rls_ingredient_command_org ON ingredient_command FOR ALL "
        f"USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_forbid_published_version_mutation() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND OLD.status = 'published' THEN
            RAISE EXCEPTION 'published_frozen';
          END IF;
          IF TG_OP = 'UPDATE' AND OLD.status = 'published' THEN
            IF NEW.status = 'retired'
               AND NEW.ingredient_id = OLD.ingredient_id
               AND NEW.organization_id = OLD.organization_id
               AND NEW.version_number = OLD.version_number
               AND NEW.nutrition_basis_type = OLD.nutrition_basis_type
               AND NEW.nutrition_basis_quantity = OLD.nutrition_basis_quantity
               AND NEW.nutrition_basis_unit_id = OLD.nutrition_basis_unit_id
               AND NEW.data_source_id IS NOT DISTINCT FROM OLD.data_source_id
               AND NEW.notes IS NOT DISTINCT FROM OLD.notes
               AND NEW.valid_from IS NOT DISTINCT FROM OLD.valid_from
               AND NEW.valid_to IS NOT DISTINCT FROM OLD.valid_to
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

    bind = op.get_bind()
    for code, description in INGREDIENT_PERMISSION_DEFINITIONS:
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
            GRANT SELECT, INSERT, UPDATE, DELETE ON ingredient_command TO panne_runtime;
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
    op.execute(
        """
        DO $$
        BEGIN
          IF to_regclass('public.ingredient_command') IS NOT NULL THEN
            DROP POLICY IF EXISTS rls_ingredient_command_org ON ingredient_command;
            ALTER TABLE ingredient_command NO FORCE ROW LEVEL SECURITY;
            ALTER TABLE ingredient_command DISABLE ROW LEVEL SECURITY;
          END IF;
        END
        $$
        """
    )
    op.execute("DROP TABLE IF EXISTS ingredient_command")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_forbid_published_version_mutation() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' AND OLD.status = 'published' THEN
            RAISE EXCEPTION 'published_frozen';
          END IF;
          IF TG_OP = 'UPDATE' AND OLD.status = 'published' THEN
            RAISE EXCEPTION 'published_frozen';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in ("supplier_item", "supplier", "ingredient_version", "ingredient"):
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS row_version")
