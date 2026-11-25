"""P1-Loja: cache do estado Mercado Pago do parceiro.

- marketplace.partners.mp_connected (bool not null default false)
- marketplace.partners.mp_nickname (text null)
- marketplace.partners.mp_checked_at (timestamptz null)

Revision ID: f7c2e9a14b60
Revises: e1f4a2b90c83
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7c2e9a14b60"
down_revision: Union[str, Sequence[str], None] = "e1f4a2b90c83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "marketplace"


def upgrade() -> None:
    op.add_column(
        "partners",
        sa.Column("mp_connected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        schema=_SCHEMA,
    )
    op.add_column(
        "partners",
        sa.Column("mp_nickname", sa.Text(), nullable=True),
        schema=_SCHEMA,
    )
    op.add_column(
        "partners",
        sa.Column("mp_checked_at", sa.DateTime(timezone=True), nullable=True),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("partners", "mp_checked_at", schema=_SCHEMA)
    op.drop_column("partners", "mp_nickname", schema=_SCHEMA)
    op.drop_column("partners", "mp_connected", schema=_SCHEMA)
