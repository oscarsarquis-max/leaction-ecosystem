"""padrões da casa, auditoria do Gigio e origem da linha

Revision ID: 0008_gigio
Revises: 0007_importacao_loja
Create Date: 2026-11-06

SÓ ADITIVA (GESTAO-012). Nenhuma linha antiga muda de quantidade, nome ou receita:

- `receita_linhas.origem` nasce `manual` nas linhas que já existiam.
- `receita_linhas.faixa_min` e `faixa_max` nascem vazias.
- `padrao_padaria` e `gigio_sugestao` nascem vazias, e cada organização que já existe
  recebe as cinco sementes. O Oscar edita depois.
"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "0008_gigio"
down_revision: Union[str, None] = "0007_importacao_loja"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEMENTES = (
    ("Hidratação", "água", 60, "Água da massa, sobre a farinha.", 1),
    (
        "Água residual do fermento",
        "água residual do fermento",
        6,
        "Cerca de 30 g para 500 g de farinha, além da hidratação.",
        2,
    ),
    ("Leite em pó ou farinha láctea", "leite em pó", 10, "Ou farinha láctea.", 3),
    ("Levain", "levain", 20, "Fermento natural.", 4),
    ("PFF", "PFF", 20, "Prefermento.", 5),
)


def upgrade() -> None:
    op.add_column(
        "receita_linhas",
        sa.Column("origem", sa.String(12), nullable=False, server_default="manual"),
    )
    op.add_column("receita_linhas", sa.Column("faixa_min", sa.Numeric(6, 2)))
    op.add_column("receita_linhas", sa.Column("faixa_max", sa.Numeric(6, 2)))
    op.create_check_constraint(
        "ck_receita_linhas_origem",
        "receita_linhas",
        "origem IN ('manual', 'estimado', 'conferido')",
    )
    op.create_table(
        "padrao_padaria",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("ingrediente_id", sa.Uuid(), sa.ForeignKey("ingredientes.id")),
        sa.Column("termo", sa.String(80), nullable=False),
        sa.Column("percentual", sa.Numeric(6, 2), nullable=False),
        sa.Column("observacao", sa.Text()),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("percentual >= 0", name="ck_padrao_padaria_percentual"),
    )
    op.create_index("ix_padrao_padaria_organizacao_id", "padrao_padaria", ["organizacao_id"])
    op.create_table(
        "gigio_sugestao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False),
        sa.Column("receita_id", sa.Uuid(), sa.ForeignKey("receitas.id"), nullable=False),
        sa.Column("usuario_id", sa.Uuid(), sa.ForeignKey("usuarios.id")),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("modelo", sa.String(120), nullable=False),
        sa.Column("tokens_entrada", sa.Integer()),
        sa.Column("tokens_saida", sa.Integer()),
        sa.Column("entrada", sa.JSON(), nullable=False),
        sa.Column("saida", sa.JSON(), nullable=False),
    )
    op.create_index("ix_gigio_sugestao_organizacao_id", "gigio_sugestao", ["organizacao_id"])
    ligacao = op.get_bind()
    orgs = ligacao.execute(sa.text("SELECT id FROM organizacoes")).fetchall()
    if orgs:
        tabela = sa.table(
            "padrao_padaria",
            sa.column("id", sa.Uuid()),
            sa.column("organizacao_id", sa.Uuid()),
            sa.column("nome", sa.String()),
            sa.column("termo", sa.String()),
            sa.column("percentual", sa.Numeric()),
            sa.column("observacao", sa.Text()),
            sa.column("ativo", sa.Boolean()),
            sa.column("ordem", sa.Integer()),
        )
        linhas = []
        for (org_id,) in orgs:
            for nome, termo, percentual, observacao, ordem in SEMENTES:
                linhas.append(
                    {
                        "id": uuid4(),
                        "organizacao_id": org_id,
                        "nome": nome,
                        "termo": termo,
                        "percentual": percentual,
                        "observacao": observacao,
                        "ativo": True,
                        "ordem": ordem,
                    }
                )
        op.bulk_insert(tabela, linhas)


def downgrade() -> None:
    op.drop_index("ix_gigio_sugestao_organizacao_id", table_name="gigio_sugestao")
    op.drop_table("gigio_sugestao")
    op.drop_index("ix_padrao_padaria_organizacao_id", table_name="padrao_padaria")
    op.drop_table("padrao_padaria")
    op.drop_constraint("ck_receita_linhas_origem", "receita_linhas", type_="check")
    op.drop_column("receita_linhas", "faixa_max")
    op.drop_column("receita_linhas", "faixa_min")
    op.drop_column("receita_linhas", "origem")
