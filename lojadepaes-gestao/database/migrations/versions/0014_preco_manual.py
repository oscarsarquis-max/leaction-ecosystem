"""preço informado no produto

Revision ID: 0014_preco_manual
Revises: 0013_custos
Create Date: 2026-11-20

SÓ ADITIVA (GESTAO-020). Preço de venda informado no Gestão, para quem não tem
a Loja integrada ou vende um produto que não está na Loja. A coluna nasce nula
e nenhum dado existente é alterado.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0014_preco_manual"
down_revision: Union[str, None] = "0013_custos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("produtos", sa.Column("preco_manual", sa.Numeric(12, 2)))
    op.create_check_constraint(
        "ck_produtos_preco_manual",
        "produtos",
        "preco_manual IS NULL OR preco_manual > 0",
    )


def downgrade() -> None:
    op.drop_constraint("ck_produtos_preco_manual", "produtos", type_="check")
    op.drop_column("produtos", "preco_manual")
