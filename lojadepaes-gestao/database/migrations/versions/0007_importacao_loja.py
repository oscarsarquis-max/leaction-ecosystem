"""foto e origem da importação única da vitrine

Revision ID: 0007_importacao_loja
Revises: 0006_receitas
Create Date: 2026-11-06

SÓ ADITIVA (GESTAO-011). Nenhuma linha é alterada, renomeada, convertida nem apagada:

- `produtos.foto_url` nasce vazio. É a URL pública da foto, sem copiar o arquivo.
- `produtos.origem_loja_id` nasce vazio. Único por organização quando preenchido,
  para não duplicar. Não sincroniza.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_importacao_loja"
down_revision: Union[str, None] = "0006_receitas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("produtos", sa.Column("foto_url", sa.String(500)))
    op.add_column("produtos", sa.Column("origem_loja_id", sa.Uuid()))
    op.create_index(
        "uq_produtos_org_origem_loja",
        "produtos",
        ["organizacao_id", "origem_loja_id"],
        unique=True,
        postgresql_where=sa.text("origem_loja_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_produtos_org_origem_loja", table_name="produtos")
    op.drop_column("produtos", "origem_loja_id")
    op.drop_column("produtos", "foto_url")
