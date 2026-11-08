"""famílias, produtos e o lugar da receita técnica

Revision ID: 0005_produtos
Revises: 0004_valor_pago_correcoes
Create Date: 2026-11-05

SÓ ADITIVA (GESTAO-009). Nenhuma linha é alterada, renomeada, convertida nem apagada:

- `familias` e `produtos` nascem vazios. As sugestões de família não são gravadas sozinhas.
- `receitas` guarda o lugar (situação rascunho), sem linhas.
- `ingredientes.produto_id` liga o preparo da casa ao produto. Fica vazio em todo ingrediente que já existe.
- `organizacoes.familias_sugestoes_dispensadas` começa falso.
- o check `ck_ingredientes_categoria` só ganha o valor "Preparos da casa". Todo valor que já existia continua aceito.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_produtos"
down_revision: Union[str, None] = "0004_valor_pago_correcoes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _org() -> sa.Column:
    return sa.Column("organizacao_id", sa.Uuid(), sa.ForeignKey("organizacoes.id"), nullable=False)


def _agora() -> sa.Column:
    return sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


_CATEGORIAS = (
    "Farinhas",
    "Fermentos",
    "Açúcares e mel",
    "Gorduras",
    "Laticínios",
    "Ovos",
    "Sal e temperos",
    "Sementes e grãos",
    "Frutas secas e oleaginosas",
    "Chocolates e cacau",
    "Frios e embutidos",
    "Líquidos",
    "Preparos da casa",
    "Outros",
)
_CATEGORIAS_ANTES = tuple(c for c in _CATEGORIAS if c != "Preparos da casa")


def _lista(categorias: tuple[str, ...]) -> str:
    return ",".join("'" + c + "'" for c in categorias)


def upgrade() -> None:
    # A lista de categorias ganha "Preparos da casa". Os valores que já existem continuam válidos.
    op.drop_constraint("ck_ingredientes_categoria", "ingredientes", type_="check")
    op.create_check_constraint(
        "ck_ingredientes_categoria",
        "ingredientes",
        f"categoria IN ({_lista(_CATEGORIAS)})",
    )
    op.add_column(
        "organizacoes",
        sa.Column(
            "familias_sugestoes_dispensadas",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_table(
        "familias",
        _pk(),
        _org(),
        sa.Column("nome", sa.String(80), nullable=False),
        sa.Column("nome_normalizado", sa.String(80), nullable=False),
        _agora(),
        sa.UniqueConstraint("organizacao_id", "nome_normalizado", name="uq_familias_org_nome"),
    )
    op.create_index("ix_familias_organizacao_id", "familias", ["organizacao_id"])

    op.create_table(
        "produtos",
        _pk(),
        _org(),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("nome_normalizado", sa.String(120), nullable=False),
        sa.Column("codigo", sa.String(40)),
        sa.Column("modalidade", sa.String(12), nullable=False),
        sa.Column("uso_venda", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("uso_componente", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("familia_id", sa.Uuid(), sa.ForeignKey("familias.id")),
        sa.Column("unidade_venda", sa.String(2), nullable=False),
        sa.Column("peso_unidade_g", sa.Numeric(10, 2)),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("observacao", sa.Text()),
        sa.Column("item_estoque_id", sa.Uuid(), sa.ForeignKey("itens_estoque.id")),
        _agora(),
        sa.Column(
            "atualizado_em",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("organizacao_id", "nome_normalizado", name="uq_produtos_org_nome"),
        sa.CheckConstraint("modalidade IN ('produzido','comprado')", name="ck_produtos_modalidade"),
        sa.CheckConstraint("unidade_venda IN ('un','kg')", name="ck_produtos_unidade_venda"),
        sa.CheckConstraint("uso_venda OR uso_componente", name="ck_produtos_uso"),
        sa.CheckConstraint("peso_unidade_g IS NULL OR peso_unidade_g > 0", name="ck_produtos_peso"),
    )
    op.create_index("ix_produtos_organizacao_id", "produtos", ["organizacao_id"])
    op.create_index("ix_produtos_familia_id", "produtos", ["familia_id"])
    op.create_index("ix_produtos_item_estoque_id", "produtos", ["item_estoque_id"])

    op.create_table(
        "receitas",
        _pk(),
        _org(),
        sa.Column("produto_id", sa.Uuid(), sa.ForeignKey("produtos.id"), nullable=False),
        sa.Column("situacao", sa.String(12), nullable=False, server_default="rascunho"),
        _agora(),
        sa.UniqueConstraint("produto_id", name="uq_receitas_produto"),
        sa.CheckConstraint("situacao IN ('rascunho')", name="ck_receitas_situacao"),
    )
    op.create_index("ix_receitas_organizacao_id", "receitas", ["organizacao_id"])

    op.add_column("ingredientes", sa.Column("produto_id", sa.Uuid(), sa.ForeignKey("produtos.id")))
    op.create_index("uq_ingredientes_produto", "ingredientes", ["produto_id"], unique=True)


def downgrade() -> None:
    op.drop_constraint("ck_ingredientes_categoria", "ingredientes", type_="check")
    op.create_check_constraint(
        "ck_ingredientes_categoria",
        "ingredientes",
        f"categoria IN ({_lista(_CATEGORIAS_ANTES)})",
    )
    op.drop_index("uq_ingredientes_produto", table_name="ingredientes")
    op.drop_column("ingredientes", "produto_id")
    op.drop_table("receitas")
    op.drop_index("ix_produtos_item_estoque_id", table_name="produtos")
    op.drop_index("ix_produtos_familia_id", table_name="produtos")
    op.drop_index("ix_produtos_organizacao_id", table_name="produtos")
    op.drop_table("produtos")
    op.drop_index("ix_familias_organizacao_id", table_name="familias")
    op.drop_table("familias")
    op.drop_column("organizacoes", "familias_sugestoes_dispensadas")
