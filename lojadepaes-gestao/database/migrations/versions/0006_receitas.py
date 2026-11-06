"""linhas, rendimento e versões da receita técnica

Revision ID: 0006_receitas
Revises: 0005_produtos
Create Date: 2026-11-05

SÓ ADITIVA (GESTAO-010). Nenhuma linha é alterada, renomeada, convertida nem apagada:

- `receitas` ganha rendimento, peso da unidade, perda, modo de fazer e versão.
  Tudo nasce vazio ou com padrão (perda 0, versão 1, modo de fazer vazio).
- o check `ck_receitas_situacao` passa a aceitar `publicada` além de `rascunho`.
  O valor que já existia (`rascunho`) continua aceito.
- `receita_linhas` e `receita_versoes` nascem vazias.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_receitas"
down_revision: Union[str, None] = "0005_produtos"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_receitas_situacao", "receitas", type_="check")
    op.create_check_constraint(
        "ck_receitas_situacao",
        "receitas",
        "situacao IN ('rascunho', 'publicada')",
    )
    op.add_column("receitas", sa.Column("rendimento_quantidade", sa.Numeric(12, 3)))
    op.add_column("receitas", sa.Column("rendimento_unidade", sa.String(2)))
    op.add_column("receitas", sa.Column("peso_unidade_g", sa.Numeric(10, 2)))
    op.add_column(
        "receitas",
        sa.Column("perda_percentual", sa.Numeric(5, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "receitas",
        sa.Column("modo_fazer", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
    )
    op.add_column(
        "receitas",
        sa.Column("versao", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_check_constraint(
        "ck_receitas_rendimento",
        "receitas",
        "rendimento_quantidade IS NULL OR rendimento_quantidade > 0",
    )
    op.create_check_constraint(
        "ck_receitas_unidade_rendimento",
        "receitas",
        "rendimento_unidade IS NULL OR rendimento_unidade IN ('g','kg','ml','l','un')",
    )
    op.create_check_constraint(
        "ck_receitas_peso",
        "receitas",
        "peso_unidade_g IS NULL OR peso_unidade_g > 0",
    )
    op.create_check_constraint(
        "ck_receitas_perda",
        "receitas",
        "perda_percentual >= 0 AND perda_percentual < 100",
    )
    op.create_check_constraint("ck_receitas_versao", "receitas", "versao >= 1")

    op.create_table(
        "receita_linhas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False),
        sa.Column("receita_id", sa.Uuid(), sa.ForeignKey("receitas.id"), nullable=False),
        sa.Column("ingrediente_id", sa.Uuid(), sa.ForeignKey("ingredientes.id")),
        sa.Column("texto", sa.String(120)),
        sa.Column("quantidade", sa.Numeric(12, 3), nullable=False),
        sa.Column("unidade", sa.String(2), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.Column("observacao", sa.Text()),
        sa.CheckConstraint("quantidade > 0", name="ck_receita_linhas_quantidade"),
        sa.CheckConstraint("unidade IN ('g','kg','ml','l','un')", name="ck_receita_linhas_unidade"),
        sa.CheckConstraint("ordem >= 1", name="ck_receita_linhas_ordem"),
    )
    op.create_index("ix_receita_linhas_organizacao_id", "receita_linhas", ["organizacao_id"])
    op.create_index("ix_receita_linhas_receita_id", "receita_linhas", ["receita_id"])

    op.create_table(
        "receita_versoes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False),
        sa.Column("receita_id", sa.Uuid(), sa.ForeignKey("receitas.id"), nullable=False),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column(
            "publicada_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("rendimento_quantidade", sa.Numeric(12, 3)),
        sa.Column("rendimento_unidade", sa.String(2)),
        sa.Column("peso_unidade_g", sa.Numeric(10, 2)),
        sa.Column("perda_percentual", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("modo_fazer", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("linhas", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.UniqueConstraint("receita_id", "versao", name="uq_receita_versoes_numero"),
        sa.CheckConstraint("versao >= 1", name="ck_receita_versoes_versao"),
    )
    op.create_index("ix_receita_versoes_organizacao_id", "receita_versoes", ["organizacao_id"])
    op.create_index("ix_receita_versoes_receita_id", "receita_versoes", ["receita_id"])


def downgrade() -> None:
    op.drop_index("ix_receita_versoes_receita_id", table_name="receita_versoes")
    op.drop_index("ix_receita_versoes_organizacao_id", table_name="receita_versoes")
    op.drop_table("receita_versoes")
    op.drop_index("ix_receita_linhas_receita_id", table_name="receita_linhas")
    op.drop_index("ix_receita_linhas_organizacao_id", table_name="receita_linhas")
    op.drop_table("receita_linhas")
    op.drop_constraint("ck_receitas_versao", "receitas", type_="check")
    op.drop_constraint("ck_receitas_perda", "receitas", type_="check")
    op.drop_constraint("ck_receitas_peso", "receitas", type_="check")
    op.drop_constraint("ck_receitas_unidade_rendimento", "receitas", type_="check")
    op.drop_constraint("ck_receitas_rendimento", "receitas", type_="check")
    op.drop_column("receitas", "versao")
    op.drop_column("receitas", "modo_fazer")
    op.drop_column("receitas", "perda_percentual")
    op.drop_column("receitas", "peso_unidade_g")
    op.drop_column("receitas", "rendimento_unidade")
    op.drop_column("receitas", "rendimento_quantidade")
    op.drop_constraint("ck_receitas_situacao", "receitas", type_="check")
    op.create_check_constraint(
        "ck_receitas_situacao",
        "receitas",
        "situacao IN ('rascunho')",
    )
