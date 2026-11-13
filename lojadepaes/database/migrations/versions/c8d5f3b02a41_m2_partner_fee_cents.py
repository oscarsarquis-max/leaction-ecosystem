"""Taxa fixa por pedido no lugar do percentual. O schema está vazio.

Revision ID: c8d5f3b02a41
Revises: b7c4e2a91f30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c8d5f3b02a41"
down_revision: Union[str, Sequence[str], None] = "b7c4e2a91f30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "marketplace"


def upgrade() -> None:
    op.add_column(
        "partners",
        sa.Column("fee_cents", sa.Integer(), nullable=False, server_default="250"),
        schema=_SCHEMA,
    )
    op.create_check_constraint(
        "ck_mp_partners_fee",
        "partners",
        "fee_cents BETWEEN 0 AND 100000",
        schema=_SCHEMA,
    )
    op.drop_constraint("ck_mp_partners_commission", "partners", type_="check", schema=_SCHEMA)
    op.drop_column("partners", "commission_percent", schema=_SCHEMA)


def downgrade() -> None:
    op.add_column(
        "partners",
        sa.Column("commission_percent", sa.Integer(), nullable=False, server_default="0"),
        schema=_SCHEMA,
    )
    op.create_check_constraint(
        "ck_mp_partners_commission",
        "partners",
        "commission_percent BETWEEN 0 AND 100",
        schema=_SCHEMA,
    )
    op.alter_column("partners", "commission_percent", server_default=None, schema=_SCHEMA)
    op.drop_constraint("ck_mp_partners_fee", "partners", type_="check", schema=_SCHEMA)
    op.drop_column("partners", "fee_cents", schema=_SCHEMA)
