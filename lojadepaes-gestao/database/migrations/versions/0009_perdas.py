"""perdas, função da linha e rendimento

Revision ID: 0009_perdas
Revises: 0008_gigio
Create Date: 2026-11-06

SÓ ADITIVA (GESTAO-013). Não apaga coluna e não reescreve quantidade:

- `receita_linhas.funcao` nasce `massa`.
- `perda_percentual` continua. Só valor maior que zero vira perda de processo
  manual. Zero não é decisão do padeiro: a resolução (medido, padrão, referência)
  continua valendo.
- `perda_referencia` nasce vazia; a carga do YAML é outro passo.
- Cada organização que já existe recebe o padrão de processo 5 % em pães de 400 a 600 g.
"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision: str = "0009_perdas"
down_revision: Union[str, None] = "0008_gigio"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "receita_linhas",
        sa.Column("funcao", sa.String(12), nullable=False, server_default="massa"),
    )
    op.create_check_constraint(
        "ck_receita_linhas_funcao",
        "receita_linhas",
        "funcao IN ('massa', 'recheio', 'cobertura', 'finalizacao')",
    )
    op.create_table(
        "perda_referencia",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("formato", sa.String(20), nullable=False),
        sa.Column("peso_min_g", sa.Numeric(10, 2)),
        sa.Column("peso_max_g", sa.Numeric(10, 2)),
        sa.Column("faixa_min", sa.Numeric(5, 2)),
        sa.Column("faixa_max", sa.Numeric(5, 2)),
        sa.Column("sugerido", sa.Numeric(5, 2), nullable=False),
        sa.Column("confianca", sa.String(12)),
        sa.Column("fonte_id", sa.String(40), nullable=False),
        sa.Column("fonte_titulo", sa.String(200), nullable=False),
        sa.Column("fonte_url", sa.String(300)),
        sa.Column("nota", sa.Text()),
        sa.CheckConstraint("tipo IN ('processo', 'coccao', 'comercial')", name="ck_perda_referencia_tipo"),
        sa.CheckConstraint(
            "formato IN ('qualquer', 'forma', 'forma_enriquecida', 'livre', 'assadeira', 'pequeno')",
            name="ck_perda_referencia_formato",
        ),
        sa.CheckConstraint("sugerido >= 0 AND sugerido < 100", name="ck_perda_referencia_sugerido"),
    )
    op.add_column("receitas", sa.Column("formato", sa.String(20)))
    op.add_column("receitas", sa.Column("unidades_desejadas", sa.Integer()))
    op.add_column("receitas", sa.Column("perda_processo_pct", sa.Numeric(5, 2)))
    op.add_column("receitas", sa.Column("perda_processo_origem", sa.String(12)))
    op.add_column("receitas", sa.Column("perda_processo_referencia_id", sa.Uuid(), sa.ForeignKey("perda_referencia.id")))
    op.add_column("receitas", sa.Column("perda_processo_motivo", sa.Text()))
    op.add_column("receitas", sa.Column("perda_coccao_pct", sa.Numeric(5, 2)))
    op.add_column("receitas", sa.Column("perda_coccao_origem", sa.String(12)))
    op.add_column("receitas", sa.Column("perda_coccao_referencia_id", sa.Uuid(), sa.ForeignKey("perda_referencia.id")))
    op.add_column("receitas", sa.Column("perda_coccao_motivo", sa.Text()))
    op.create_check_constraint(
        "ck_receitas_formato",
        "receitas",
        "formato IS NULL OR formato IN ('forma', 'forma_enriquecida', 'livre', 'assadeira', 'pequeno')",
    )
    op.create_check_constraint(
        "ck_receitas_unidades",
        "receitas",
        "unidades_desejadas IS NULL OR unidades_desejadas > 0",
    )
    op.create_check_constraint(
        "ck_receitas_origem_processo",
        "receitas",
        "perda_processo_origem IS NULL OR perda_processo_origem IN ('medido', 'padrao', 'referencia', 'manual')",
    )
    op.create_check_constraint(
        "ck_receitas_origem_coccao",
        "receitas",
        "perda_coccao_origem IS NULL OR perda_coccao_origem IN ('medido', 'padrao', 'referencia', 'manual')",
    )
    op.create_table(
        "perda_padrao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False),
        sa.Column("familia_id", sa.Uuid(), sa.ForeignKey("familias.id")),
        sa.Column("formato", sa.String(20)),
        sa.Column("peso_min_g", sa.Numeric(10, 2)),
        sa.Column("peso_max_g", sa.Numeric(10, 2)),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("percentual", sa.Numeric(5, 2), nullable=False),
        sa.Column("observacao", sa.Text()),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("tipo IN ('processo', 'coccao', 'comercial')", name="ck_perda_padrao_tipo"),
        sa.CheckConstraint(
            "formato IS NULL OR formato IN ('forma', 'forma_enriquecida', 'livre', 'assadeira', 'pequeno')",
            name="ck_perda_padrao_formato",
        ),
        sa.CheckConstraint("percentual >= 0 AND percentual < 100", name="ck_perda_padrao_percentual"),
    )
    op.create_index("ix_perda_padrao_organizacao_id", "perda_padrao", ["organizacao_id"])
    op.create_table(
        "perda_medicao",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False),
        sa.Column("receita_id", sa.Uuid(), sa.ForeignKey("receitas.id"), nullable=False),
        sa.Column("data", sa.Date(), nullable=False, server_default=sa.func.current_date()),
        sa.Column("massa_total_g", sa.Numeric(12, 3), nullable=False),
        sa.Column("pecas", sa.Integer(), nullable=False),
        sa.Column("peso_cru_medio_g", sa.Numeric(10, 2), nullable=False),
        sa.Column("peso_final_medio_g", sa.Numeric(10, 2), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("massa_total_g > 0", name="ck_perda_medicao_massa"),
        sa.CheckConstraint("pecas > 0", name="ck_perda_medicao_pecas"),
        sa.CheckConstraint("peso_cru_medio_g > 0", name="ck_perda_medicao_cru"),
        sa.CheckConstraint("peso_final_medio_g > 0", name="ck_perda_medicao_final"),
    )
    op.create_index("ix_perda_medicao_organizacao_id", "perda_medicao", ["organizacao_id"])
    op.create_index("ix_perda_medicao_receita_id", "perda_medicao", ["receita_id"])
    op.execute(
        sa.text(
            """
            UPDATE receitas
            SET perda_processo_pct = perda_percentual,
                perda_processo_origem = 'manual',
                perda_processo_motivo = 'Valor informado antes do modelo de perdas.'
            WHERE perda_percentual > 0
            """
        )
    )
    ligacao = op.get_bind()
    orgs = ligacao.execute(sa.text("SELECT id FROM organizacoes")).fetchall()
    if orgs:
        tabela = sa.table(
            "perda_padrao",
            sa.column("id", sa.Uuid()),
            sa.column("organizacao_id", sa.Uuid()),
            sa.column("familia_id", sa.Uuid()),
            sa.column("formato", sa.String()),
            sa.column("peso_min_g", sa.Numeric()),
            sa.column("peso_max_g", sa.Numeric()),
            sa.column("tipo", sa.String()),
            sa.column("percentual", sa.Numeric()),
            sa.column("observacao", sa.Text()),
            sa.column("ativo", sa.Boolean()),
        )
        op.bulk_insert(
            tabela,
            [
                {
                    "id": uuid4(),
                    "organizacao_id": org_id,
                    "familia_id": None,
                    "formato": None,
                    "peso_min_g": 400,
                    "peso_max_g": 600,
                    "tipo": "processo",
                    "percentual": 5,
                    "observacao": "informado pelo Oscar, 06/11",
                    "ativo": True,
                }
                for (org_id,) in orgs
            ],
        )


def downgrade() -> None:
    op.drop_index("ix_perda_medicao_receita_id", table_name="perda_medicao")
    op.drop_index("ix_perda_medicao_organizacao_id", table_name="perda_medicao")
    op.drop_table("perda_medicao")
    op.drop_index("ix_perda_padrao_organizacao_id", table_name="perda_padrao")
    op.drop_table("perda_padrao")
    op.drop_constraint("ck_receitas_origem_coccao", "receitas", type_="check")
    op.drop_constraint("ck_receitas_origem_processo", "receitas", type_="check")
    op.drop_constraint("ck_receitas_unidades", "receitas", type_="check")
    op.drop_constraint("ck_receitas_formato", "receitas", type_="check")
    op.drop_column("receitas", "perda_coccao_motivo")
    op.drop_column("receitas", "perda_coccao_referencia_id")
    op.drop_column("receitas", "perda_coccao_origem")
    op.drop_column("receitas", "perda_coccao_pct")
    op.drop_column("receitas", "perda_processo_motivo")
    op.drop_column("receitas", "perda_processo_referencia_id")
    op.drop_column("receitas", "perda_processo_origem")
    op.drop_column("receitas", "perda_processo_pct")
    op.drop_column("receitas", "unidades_desejadas")
    op.drop_column("receitas", "formato")
    op.drop_table("perda_referencia")
    op.drop_constraint("ck_receita_linhas_funcao", "receita_linhas", type_="check")
    op.drop_column("receita_linhas", "funcao")
