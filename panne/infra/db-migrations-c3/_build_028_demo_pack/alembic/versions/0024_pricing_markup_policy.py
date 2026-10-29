"""Pricing markup/margin policy persistence (org-scoped). UI may remain unavailable.

Revision ID: 0024_pricing_markup_policy
Revises: 0023_practiced_sale_basis
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024_pricing_markup_policy"
down_revision: Union[str, Sequence[str], None] = "0023_practiced_sale_basis"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"


def upgrade() -> None:
    op.create_table(
        "pricing_markup_policy",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),  # markup_factor | margin_rate
        sa.Column("value", sa.Numeric(18, 8), nullable=False),
        sa.Column("scope_level", sa.Text(), nullable=False),  # organization|family|product|channel
        sa.Column("product_family_id", sa.Uuid(), nullable=True),
        sa.Column("technical_product_id", sa.Uuid(), nullable=True),
        sa.Column("channel", sa.Text(), nullable=True),
        sa.Column("establishment_id", sa.Uuid(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("status", sa.Text(), nullable=False, server_default="'draft'"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("kind IN ('markup_factor','margin_rate')", name="ck_pricing_markup_policy_kind"),
        sa.CheckConstraint(
            "scope_level IN ('organization','family','product','channel')",
            name="ck_pricing_markup_policy_scope",
        ),
        sa.CheckConstraint("status IN ('draft','active','retired')", name="ck_pricing_markup_policy_status"),
        sa.CheckConstraint("value > 0", name="ck_pricing_markup_policy_value"),
        sa.UniqueConstraint("organization_id", "code", name="uq_pricing_markup_policy_org_code"),
        sa.UniqueConstraint("id", "organization_id", name="uq_pricing_markup_policy_id_org"),
    )
    op.create_index(
        "ix_pricing_markup_policy_org_status",
        "pricing_markup_policy",
        ["organization_id", "status"],
    )
    op.execute("ALTER TABLE pricing_markup_policy ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pricing_markup_policy FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY rls_pricing_markup_policy_org ON pricing_markup_policy FOR ALL "
        f"USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON pricing_markup_policy TO panne_runtime;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_demo_runtime') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON pricing_markup_policy TO panne_demo_runtime;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_pricing_markup_policy_org ON pricing_markup_policy")
    op.execute("ALTER TABLE pricing_markup_policy NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pricing_markup_policy DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_pricing_markup_policy_org_status", table_name="pricing_markup_policy")
    op.drop_table("pricing_markup_policy")
