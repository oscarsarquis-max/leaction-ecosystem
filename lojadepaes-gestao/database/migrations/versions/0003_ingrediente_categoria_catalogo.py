"""ingrediente: categoria, apelidos e quem confirmou "não existe"; catálogo de referência (global)

Revision ID: 0003_ingrediente_catalogo
Revises: 0002_organizacoes_estoque
Create Date: 2026-11-03

- `ingredientes` ganha `categoria` (lista fixa; "Outros" por padrão), `apelidos` (texto[]) e o
  registro de quem confirmou "não existe" (e quando) ao cadastrar algo parecido com outro.
- `catalogo_ingrediente` é GLOBAL (sem `organizacao_id`): só sugere. Carregado pelo comando
  `carregar-catalogo`, nunca pela tela.
- Sem extensões do Postgres: a comparação por semelhança é feita em Python.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_ingrediente_catalogo"
down_revision: Union[str, None] = "0002_organizacoes_estoque"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CATEGORIAS = (
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
    "Outros",
)

def upgrade() -> None:
    op.add_column(
        "ingredientes",
        sa.Column("categoria", sa.String(40), nullable=False, server_default="Outros"),
    )
    op.add_column(
        "ingredientes",
        sa.Column(
            "apelidos",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
    )
    op.add_column(
        "ingredientes",
        sa.Column("confirmado_inexistente_por", sa.Uuid(), sa.ForeignKey("usuarios.id")),
    )
    op.add_column(
        "ingredientes",
        sa.Column("confirmado_inexistente_em", sa.DateTime(timezone=True)),
    )
    lista = ",".join("'" + c + "'" for c in CATEGORIAS)
    op.create_check_constraint("ck_ingredientes_categoria", "ingredientes", f"categoria IN ({lista})")

    op.create_table(
        "catalogo_ingrediente",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("nome_normalizado", sa.String(120), nullable=False),
        sa.Column("categoria", sa.String(40), nullable=False),
        sa.Column("unidade_base", sa.String(2), nullable=False),
        sa.Column(
            "apelidos",
            postgresql.ARRAY(sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::text[]"),
        ),
        sa.Column("versao", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("nome_normalizado", name="uq_catalogo_ingrediente_nome"),
        sa.CheckConstraint("unidade_base IN ('g','ml','un')", name="ck_catalogo_unidade_base"),
        sa.CheckConstraint(f"categoria IN ({lista})", name="ck_catalogo_categoria"),
    )


def downgrade() -> None:
    op.drop_table("catalogo_ingrediente")
    op.drop_constraint("ck_ingredientes_categoria", "ingredientes", type_="check")
    op.drop_column("ingredientes", "confirmado_inexistente_em")
    op.drop_column("ingredientes", "confirmado_inexistente_por")
    op.drop_column("ingredientes", "apelidos")
    op.drop_column("ingredientes", "categoria")
