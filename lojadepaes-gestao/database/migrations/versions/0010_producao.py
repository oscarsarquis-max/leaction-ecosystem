"""fornadas, programação e ordens de produção

Revision ID: 0010_producao
Revises: 0009_perdas
Create Date: 2026-11-07

SÓ ADITIVA (GESTAO-014). Não apaga coluna e não reescreve receita.
Cada organização que já existe recebe as fornadas Manhã 05:00 e Tarde 13:00.
"""

from datetime import time
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "0010_producao"
down_revision: Union[str, None] = "0009_perdas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEMENTES = (("Manhã 05:00", time(5, 0), 1), ("Tarde 13:00", time(13, 0), 2))


def upgrade() -> None:
    op.create_table(
        "fornadas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("horario", sa.Time(), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("organizacao_id", "nome", name="uq_fornadas_org_nome"),
        sa.CheckConstraint("ordem > 0", name="ck_fornadas_ordem"),
    )
    op.create_index("ix_fornadas_organizacao_id", "fornadas", ["organizacao_id"])
    op.create_table(
        "programacoes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False),
        sa.Column("produto_id", sa.Uuid(), sa.ForeignKey("produtos.id"), nullable=False),
        sa.Column("quantidade_por_fornada", sa.Integer(), nullable=False),
        sa.Column("fornada_ids", sa.JSON(), nullable=False),
        sa.Column("dias_semana", sa.JSON(), nullable=False),
        sa.Column("inicio", sa.Date()),
        sa.Column("fim", sa.Date()),
        sa.Column("ativa", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("quantidade_por_fornada > 0", name="ck_programacoes_quantidade"),
    )
    op.create_index("ix_programacoes_organizacao_id", "programacoes", ["organizacao_id"])
    op.create_table(
        "ordens_producao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("fornada_id", sa.Uuid(), sa.ForeignKey("fornadas.id"), nullable=False),
        sa.Column("produto_id", sa.Uuid(), sa.ForeignKey("produtos.id"), nullable=False),
        sa.Column("unidades", sa.Integer(), nullable=False),
        sa.Column("origem", sa.String(12), nullable=False),
        sa.Column("programacao_id", sa.Uuid(), sa.ForeignKey("programacoes.id")),
        sa.Column("loja_pedido_ids", sa.JSON()),
        sa.Column("situacao", sa.String(16), nullable=False, server_default="planejada"),
        sa.Column("foto", sa.JSON()),
        sa.Column("observacao", sa.Text()),
        sa.Column("demanda_diferenca", sa.Integer()),
        sa.Column("via", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comanda_numero", sa.Integer()),
        sa.Column("impressa_em", sa.DateTime(timezone=True)),
        sa.Column("impressa_por", sa.String(120)),
        sa.Column("criada_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "organizacao_id",
            "data",
            "fornada_id",
            "produto_id",
            "origem",
            name="uq_ordens_org_data_fornada_produto_origem",
        ),
        sa.CheckConstraint("unidades > 0", name="ck_ordens_unidades"),
        sa.CheckConstraint("origem IN ('programada','loja','avulsa')", name="ck_ordens_origem"),
        sa.CheckConstraint(
            "situacao IN ('planejada','impressa','em_producao','concluida','cancelada')",
            name="ck_ordens_situacao",
        ),
    )
    op.create_index("ix_ordens_producao_organizacao_id", "ordens_producao", ["organizacao_id"])
    ligacao = op.get_bind()
    orgs = ligacao.execute(sa.text("SELECT id FROM organizacoes")).fetchall()
    if orgs:
        tabela = sa.table(
            "fornadas",
            sa.column("id", sa.Uuid()),
            sa.column("organizacao_id", sa.Uuid()),
            sa.column("nome", sa.String()),
            sa.column("horario", sa.Time()),
            sa.column("ordem", sa.Integer()),
            sa.column("ativa", sa.Boolean()),
        )
        op.bulk_insert(
            tabela,
            [
                {
                    "id": uuid4(),
                    "organizacao_id": org_id,
                    "nome": nome,
                    "horario": horario,
                    "ordem": ordem,
                    "ativa": True,
                }
                for (org_id,) in orgs
                for nome, horario, ordem in SEMENTES
            ],
        )


def downgrade() -> None:
    op.drop_index("ix_ordens_producao_organizacao_id", table_name="ordens_producao")
    op.drop_table("ordens_producao")
    op.drop_index("ix_programacoes_organizacao_id", table_name="programacoes")
    op.drop_table("programacoes")
    op.drop_index("ix_fornadas_organizacao_id", table_name="fornadas")
    op.drop_table("fornadas")
