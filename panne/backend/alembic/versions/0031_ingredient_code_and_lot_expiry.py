"""Contador de código interno de ingrediente e validade explícita do lote físico.

Aditivo. Não reescreve ingredientes, notas, saldos, movimentos nem custos.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031_ingredient_code_lot_expiry"
down_revision: str | Sequence[str] | None = "0030_ingredient_link_lot"
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
    op.create_table(
        "ingredient_code_counter",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("last_value", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_ingredient_code_counter_id_org",
        "ingredient_code_counter",
        ["id", "organization_id"],
        unique=True,
    )
    op.create_index(
        "uq_ingredient_code_counter_org",
        "ingredient_code_counter",
        ["organization_id"],
        unique=True,
    )
    _enable_rls("ingredient_code_counter")
    op.add_column(
        "fiscal_physical_line",
        sa.Column("expiry_uninformed", sa.Boolean(), server_default="false", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("fiscal_physical_line", "expiry_uninformed")
    op.execute("DROP POLICY IF EXISTS rls_ingredient_code_counter_org ON ingredient_code_counter")
    op.drop_index("uq_ingredient_code_counter_org", table_name="ingredient_code_counter")
    op.drop_index("uq_ingredient_code_counter_id_org", table_name="ingredient_code_counter")
    op.drop_table("ingredient_code_counter")
