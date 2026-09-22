"""Campo aditivo para religar aceite e pagamento à sessão do pedido.

Revision ID: a8d4c1e07b33
Revises: f7a4e2c19b08
Create Date: 2026-09-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a8d4c1e07b33"
down_revision: Union[str, Sequence[str], None] = "f7a4e2c19b08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("crm_id_sessao", sa.String(length=36), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "crm_id_sessao")
