"""Remove o default produced de technical_product.supply_mode.

Revision ID: 0026_supply_mode_no_default
Revises: 0025_economic_audit_policy
Create Date: 2026-09-22

Não altera linhas existentes. Quem já está gravado como produced ou purchased
permanece assim. Inserção nova sem modalidade deixa de herdar produced.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026_supply_mode_no_default"
down_revision: Union[str, Sequence[str], None] = "0025_economic_audit_policy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("technical_product", "supply_mode", server_default=None)


def downgrade() -> None:
    op.alter_column(
        "technical_product",
        "supply_mode",
        server_default=sa.text("'produced'"),
    )
