"""valor pago na entrada, correção de custo do lote e troca de ingrediente do item

Revision ID: 0004_valor_pago_correcoes
Revises: 0003_ingrediente_catalogo
Create Date: 2026-11-03

SÓ ADITIVA (GESTAO-006). Nada existente é alterado, renomeado, convertido nem apagado:

- `entrada_linhas` ganha `valor_pago` (o total pago, como digitado) e `modo_custo`. As linhas que já
  existem ficam com os dois vazios: continuam valendo `custo_informado`/`custo_por`/`valor_total`.
- `lotes.custo_unidade_base` JÁ guarda R$ por g, ml ou un: nenhum valor é reescrito.
- `correcoes_custo`: histórico (quem, quando, antes, depois, motivo) de "Corrigir custo".
- `trocas_ingrediente`: histórico de "Trocar ingrediente" de um item.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_valor_pago_correcoes"
down_revision: Union[str, None] = "0003_ingrediente_catalogo"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _org() -> sa.Column:
    return sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False)


def _agora() -> sa.Column:
    return sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.add_column("entrada_linhas", sa.Column("valor_pago", sa.Numeric(14, 4)))
    op.add_column("entrada_linhas", sa.Column("modo_custo", sa.String(14)))
    op.create_check_constraint(
        "ck_entrada_linhas_modo_custo",
        "entrada_linhas",
        "modo_custo IS NULL OR modo_custo IN ('valor_pago','preco_unidade')",
    )

    op.create_table(
        "correcoes_custo",
        _pk(),
        _org(),
        sa.Column("lote_id", sa.Uuid(), sa.ForeignKey("lotes.id"), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("quantidade_base", sa.Numeric(18, 4), nullable=False),
        sa.Column("modo", sa.String(14), nullable=False),
        sa.Column("valor_pago", sa.Numeric(14, 4)),
        sa.Column("preco_informado", sa.Numeric(14, 4)),
        sa.Column("custo_antes", sa.Numeric(18, 8)),
        sa.Column("custo_depois", sa.Numeric(18, 8), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        _agora(),
        sa.CheckConstraint("modo IN ('valor_pago','preco_unidade')", name="ck_correcoes_custo_modo"),
    )
    op.create_index("ix_correcoes_custo_organizacao_id", "correcoes_custo", ["organizacao_id"])
    op.create_index("ix_correcoes_custo_lote_id", "correcoes_custo", ["lote_id"])

    op.create_table(
        "trocas_ingrediente",
        _pk(),
        _org(),
        sa.Column("item_id", sa.Uuid(), sa.ForeignKey("itens_estoque.id"), nullable=False),
        sa.Column("de_ingrediente_id", sa.Uuid(), sa.ForeignKey("ingredientes.id"), nullable=False),
        sa.Column("para_ingrediente_id", sa.Uuid(), sa.ForeignKey("ingredientes.id"), nullable=False),
        sa.Column("movimento_id", sa.Uuid(), sa.ForeignKey("movimentos.id")),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        _agora(),
    )
    op.create_index("ix_trocas_ingrediente_organizacao_id", "trocas_ingrediente", ["organizacao_id"])
    op.create_index("ix_trocas_ingrediente_item_id", "trocas_ingrediente", ["item_id"])


def downgrade() -> None:
    op.drop_table("trocas_ingrediente")
    op.drop_table("correcoes_custo")
    op.drop_constraint("ck_entrada_linhas_modo_custo", "entrada_linhas", type_="check")
    op.drop_column("entrada_linhas", "modo_custo")
    op.drop_column("entrada_linhas", "valor_pago")
