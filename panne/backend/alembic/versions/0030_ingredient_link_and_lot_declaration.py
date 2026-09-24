"""Vínculo manual de compras, conteúdo de embalagem e custo declarado do lote.

Aditivo. Não reescreve nota, saldo, movimento nem custo já lançados.
Não funde registros. A consolidação acontece só pela API, com confirmação.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0030_ingredient_link_lot"
down_revision: str | Sequence[str] | None = "0029_fiscal_review_without_stock"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY rls_{table}_org ON {table} FOR ALL "
        f"USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )


def upgrade() -> None:
    op.add_column(
        "inventory_lot",
        sa.Column("package_content_quantity", sa.Numeric(18, 6), nullable=True),
    )
    op.add_column("inventory_lot", sa.Column("package_content_unit", sa.Text(), nullable=True))
    op.add_column(
        "inventory_lot",
        sa.Column("package_content_declared_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("inventory_lot", sa.Column("package_content_declared_by", sa.Uuid(), nullable=True))
    op.add_column(
        "inventory_lot",
        sa.Column("cost_status", sa.Text(), server_default="known", nullable=False),
    )
    op.add_column("inventory_lot", sa.Column("declared_unit_cost", sa.Numeric(18, 6), nullable=True))
    op.add_column("inventory_lot", sa.Column("declared_cost_currency", sa.Text(), nullable=True))
    op.add_column("inventory_lot", sa.Column("opening_origin", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_inventory_lot_cost_status",
        "inventory_lot",
        "cost_status IN ('known','unknown')",
    )

    op.create_table(
        "ingredient_link_reassignment",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("destination_ingredient_id", sa.Uuid(), nullable=False),
        sa.Column("source_ingredient_id", sa.Uuid(), nullable=True),
        sa.Column("fiscal_inbound_item_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_lot_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_item_from_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_item_to_id", sa.Uuid(), nullable=False),
        sa.Column("before_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("after_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("digest", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "inventory_lot_id",
            "destination_ingredient_id",
            "digest",
            name="uq_ingredient_link_reassignment_idempotent",
        ),
    )
    op.create_index(
        "ix_ingredient_link_reassignment_org_dest",
        "ingredient_link_reassignment",
        ["organization_id", "destination_ingredient_id"],
    )
    _enable_rls("ingredient_link_reassignment")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_ingredient_link_reassignment_org ON ingredient_link_reassignment")
    op.drop_table("ingredient_link_reassignment")
    op.drop_constraint("ck_inventory_lot_cost_status", "inventory_lot", type_="check")
    op.drop_column("inventory_lot", "opening_origin")
    op.drop_column("inventory_lot", "declared_cost_currency")
    op.drop_column("inventory_lot", "declared_unit_cost")
    op.drop_column("inventory_lot", "cost_status")
    op.drop_column("inventory_lot", "package_content_declared_by")
    op.drop_column("inventory_lot", "package_content_declared_at")
    op.drop_column("inventory_lot", "package_content_unit")
    op.drop_column("inventory_lot", "package_content_quantity")
