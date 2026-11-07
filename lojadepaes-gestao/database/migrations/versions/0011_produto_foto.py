"""foto enviada do produto, no banco

Revision ID: 0011_produto_foto
Revises: 0010_producao
Create Date: 2026-11-07

SÓ ADITIVA (GESTAO-014A). A foto e a miniatura ficam na mesma linha.
Não cria bucket e não grava arquivo fora do banco.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0011_produto_foto"
down_revision: Union[str, None] = "0010_producao"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "produto_fotos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False),
        sa.Column("produto_id", sa.Uuid(), sa.ForeignKey("produtos.id"), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("largura", sa.Integer(), nullable=False),
        sa.Column("altura", sa.Integer(), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("conteudo", sa.LargeBinary(), nullable=False),
        sa.Column("mini_largura", sa.Integer(), nullable=False),
        sa.Column("mini_altura", sa.Integer(), nullable=False),
        sa.Column("mini_bytes", sa.Integer(), nullable=False),
        sa.Column("mini_conteudo", sa.LargeBinary(), nullable=False),
        sa.Column("enviado_por", sa.String(120), nullable=False),
        sa.Column("enviado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("produto_id", name="uq_produto_fotos_produto"),
        sa.CheckConstraint("tipo = 'image/webp'", name="ck_produto_fotos_tipo"),
        sa.CheckConstraint("largura > 0 AND altura > 0", name="ck_produto_fotos_medida"),
        sa.CheckConstraint("largura <= 1200 AND altura <= 1200", name="ck_produto_fotos_teto"),
        sa.CheckConstraint("bytes > 0", name="ck_produto_fotos_bytes"),
        sa.CheckConstraint("mini_largura > 0 AND mini_altura > 0", name="ck_produto_fotos_mini"),
        sa.CheckConstraint("mini_largura <= 96 AND mini_altura <= 96", name="ck_produto_fotos_mini_teto"),
    )
    op.create_index("ix_produto_fotos_organizacao_id", "produto_fotos", ["organizacao_id"])


def downgrade() -> None:
    op.drop_index("ix_produto_fotos_organizacao_id", table_name="produto_fotos")
    op.drop_table("produto_fotos")
