"""cultura viva e função inóculo na linha da receita

Revision ID: 0012_cultura_viva
Revises: 0011_produto_foto
Create Date: 2026-11-11

SÓ ADITIVA (GESTAO-015). Marca o produto como cultura viva e aceita
a função inoculo na linha. Não apaga linha e não reescreve dado.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0012_cultura_viva"
down_revision: Union[str, None] = "0011_produto_foto"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "produtos",
        sa.Column("cultura_viva", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.drop_constraint("ck_receita_linhas_funcao", "receita_linhas", type_="check")
    op.create_check_constraint(
        "ck_receita_linhas_funcao",
        "receita_linhas",
        "funcao IN ('massa', 'recheio', 'cobertura', 'finalizacao', 'inoculo')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_receita_linhas_funcao", "receita_linhas", type_="check")
    op.create_check_constraint(
        "ck_receita_linhas_funcao",
        "receita_linhas",
        "funcao IN ('massa', 'recheio', 'cobertura', 'finalizacao')",
    )
    op.drop_column("produtos", "cultura_viva")
