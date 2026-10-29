"""Confirmação explícita de entrega. Coluna nula, sem preencher o passado.

Revision ID: e8a1b7c42d19
Revises: d7e0f5a24b38
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8a1b7c42d19"
down_revision: Union[str, Sequence[str], None] = "d7e0f5a24b38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("delivery_confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "delivery_confirmed_at")
