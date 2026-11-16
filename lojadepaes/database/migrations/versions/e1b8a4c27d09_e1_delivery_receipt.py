"""Quem recebeu a entrega. Colunas nulas, sem preencher o passado.

Revision ID: e1b8a4c27d09
Revises: d4e7b1a90c63
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1b8a4c27d09"
down_revision: Union[str, Sequence[str], None] = "d4e7b1a90c63"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("delivery_received_by", sa.String(length=80), nullable=True))
    op.add_column("orders", sa.Column("delivery_note", sa.String(length=280), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "delivery_note")
    op.drop_column("orders", "delivery_received_by")
