"""GATE3: economic audit + active markup policy uniqueness (legacy-safe).

Revision ID: 0025_economic_audit_policy
Revises: 0024_pricing_markup_policy
Create Date: 2026-09-01
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025_economic_audit_policy"
down_revision: Union[str, Sequence[str], None] = "0024_pricing_markup_policy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"


def upgrade() -> None:
    op.add_column(
        "pricing_markup_policy",
        sa.Column("currency", sa.Text(), server_default="BRL", nullable=False),
    )
    op.add_column(
        "pricing_markup_policy",
        sa.Column("commercial_rounding_places", sa.Integer(), server_default="2", nullable=False),
    )
    op.add_column(
        "pricing_decision",
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.add_column(
        "pricing_decision",
        sa.Column("idempotency_key", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "pricing_decision",
        sa.Column("correlation_id", sa.Text(), nullable=True),
    )

    op.create_table(
        "pricing_economic_audit",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=True),
        sa.Column("correlation_id", sa.Text(), nullable=True),
        sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("memory", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("id", "organization_id", name="uq_pricing_economic_audit_id_org"),
    )
    op.create_index(
        "ix_pricing_economic_audit_org_created",
        "pricing_economic_audit",
        ["organization_id", "created_at"],
    )
    op.execute("ALTER TABLE pricing_economic_audit ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pricing_economic_audit FORCE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY rls_pricing_economic_audit_org ON pricing_economic_audit FOR ALL "
        f"USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )

    # One open-ended active policy per scope key (channel/establishment deferred — excluded from key).
    op.execute(
        """
        CREATE UNIQUE INDEX uq_pricing_markup_policy_active_org
        ON pricing_markup_policy (organization_id)
        WHERE status = 'active' AND scope_level = 'organization' AND valid_to IS NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_pricing_markup_policy_active_family
        ON pricing_markup_policy (organization_id, product_family_id)
        WHERE status = 'active' AND scope_level = 'family'
          AND product_family_id IS NOT NULL AND valid_to IS NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_pricing_markup_policy_active_product
        ON pricing_markup_policy (organization_id, technical_product_id)
        WHERE status = 'active' AND scope_level = 'product'
          AND technical_product_id IS NOT NULL AND valid_to IS NULL
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON pricing_economic_audit TO panne_runtime;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_demo_runtime') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE ON pricing_economic_audit TO panne_demo_runtime;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_pricing_markup_policy_active_product")
    op.execute("DROP INDEX IF EXISTS uq_pricing_markup_policy_active_family")
    op.execute("DROP INDEX IF EXISTS uq_pricing_markup_policy_active_org")
    op.execute("DROP POLICY IF EXISTS rls_pricing_economic_audit_org ON pricing_economic_audit")
    op.execute("ALTER TABLE pricing_economic_audit NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pricing_economic_audit DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_pricing_economic_audit_org_created", table_name="pricing_economic_audit")
    op.drop_table("pricing_economic_audit")
    op.drop_column("pricing_decision", "correlation_id")
    op.drop_column("pricing_decision", "idempotency_key")
    op.drop_column("pricing_decision", "snapshot")
    op.drop_column("pricing_markup_policy", "commercial_rounding_places")
    op.drop_column("pricing_markup_policy", "currency")
