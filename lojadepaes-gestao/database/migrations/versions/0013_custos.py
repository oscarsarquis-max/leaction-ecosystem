"""custos fixos, parâmetros e regra de preço

Revision ID: 0013_custos
Revises: 0012_cultura_viva
Create Date: 2026-11-20

SÓ ADITIVA (GESTAO-021). Custos fixos rateados por kg; regra de preço
(margem ou markup) em geral, família e produto. Nenhum dado existente
é alterado: as colunas novas nascem nulas.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0013_custos"
down_revision: Union[str, None] = "0012_cultura_viva"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _org() -> sa.Column:
    return sa.Column(
        "organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False, index=True
    )


def _agora() -> sa.Column:
    return sa.Column(
        "criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    )


def upgrade() -> None:
    op.create_table(
        "custos_fixos",
        _pk(),
        _org(),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("valor_mensal", sa.Numeric(12, 2), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        _agora(),
        sa.CheckConstraint("valor_mensal >= 0", name="ck_custos_fixos_valor"),
    )
    op.create_table(
        "parametros_custo",
        sa.Column(
            "organizacao_id",
            sa.Uuid(),
            sa.ForeignKey("organizacoes.id"),
            primary_key=True,
        ),
        sa.Column("massa_mensal_kg", sa.Numeric(12, 3)),
        sa.Column("regra_tipo", sa.String(12)),
        sa.Column("regra_valor", sa.Numeric(12, 4)),
        sa.CheckConstraint(
            "massa_mensal_kg IS NULL OR massa_mensal_kg > 0",
            name="ck_parametros_custo_massa",
        ),
        sa.CheckConstraint(
            "regra_tipo IS NULL OR regra_tipo IN ('margem', 'markup')",
            name="ck_parametros_custo_tipo",
        ),
    )
    op.add_column("familias", sa.Column("regra_tipo", sa.String(12)))
    op.add_column("familias", sa.Column("regra_valor", sa.Numeric(12, 4)))
    op.create_check_constraint(
        "ck_familias_regra_tipo",
        "familias",
        "regra_tipo IS NULL OR regra_tipo IN ('margem', 'markup')",
    )
    op.add_column("produtos", sa.Column("regra_tipo", sa.String(12)))
    op.add_column("produtos", sa.Column("regra_valor", sa.Numeric(12, 4)))
    op.create_check_constraint(
        "ck_produtos_regra_tipo",
        "produtos",
        "regra_tipo IS NULL OR regra_tipo IN ('margem', 'markup')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_produtos_regra_tipo", "produtos", type_="check")
    op.drop_column("produtos", "regra_valor")
    op.drop_column("produtos", "regra_tipo")
    op.drop_constraint("ck_familias_regra_tipo", "familias", type_="check")
    op.drop_column("familias", "regra_valor")
    op.drop_column("familias", "regra_tipo")
    op.drop_table("parametros_custo")
    op.drop_table("custos_fixos")
