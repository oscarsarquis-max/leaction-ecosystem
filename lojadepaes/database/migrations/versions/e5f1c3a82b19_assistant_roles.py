"""Papel da farinha e complementos no criador.

Revision ID: e5f1c3a82b19
Revises: d4e8b2c91a07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f1c3a82b19"
down_revision: Union[str, Sequence[str], None] = "d4e8b2c91a07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INCLUSIONS = (
    ("nozes", "Nozes", "Crocância delicada na fatia."),
    ("castanha-de-caju", "Castanha de caju", "Sabor amanteigado e textura macia."),
    ("granola", "Granola", "Crocância de cereais e um toque adocicado."),
    ("tomate-seco", "Tomate seco", "Acidez e doçura concentradas."),
    ("berinjela", "Berinjela", "Sabor suave e miolo mais úmido."),
    ("queijo-parmesao", "Queijo parmesão", "Salgado e aromático no miolo."),
)


def upgrade() -> None:
    op.add_column(
        "ingredients",
        sa.Column("assistant_role", sa.String(length=20), server_default="inclusion", nullable=False),
    )
    op.create_check_constraint(
        "ck_ingredients_assistant_role",
        "ingredients",
        "assistant_role IN ('flour', 'inclusion')",
    )
    op.execute(
        """
        UPDATE ingredients
        SET assistant_role = 'flour'
        WHERE slug = 'farinha-branca-italiana'
        """
    )
    op.execute(
        """
        UPDATE ingredients
        SET description = 'Farinha branca de origem italiana, para uma massa mais clara.'
        WHERE slug = 'farinha-branca-italiana'
          AND description LIKE '%pendentes de configuração%'
        """
    )
    for index, (slug, name, description) in enumerate(_INCLUSIONS):
        op.execute(
            sa.text(
                """
                INSERT INTO ingredients (
                    id, name, slug, description, sort_order, is_active, surcharge_cents,
                    assistant_role, created_at, updated_at
                )
                SELECT
                    gen_random_uuid(),
                    :name,
                    :slug,
                    :description,
                    :sort_order,
                    true,
                    NULL,
                    'inclusion',
                    now(),
                    now()
                WHERE NOT EXISTS (
                    SELECT 1 FROM ingredients WHERE slug = :slug
                )
                """
            ).bindparams(name=name, slug=slug, description=description, sort_order=index + 1)
        )
        op.execute(
            sa.text(
                """
                UPDATE ingredients
                SET assistant_role = 'inclusion', is_active = true
                WHERE slug = :slug AND assistant_role <> 'flour'
                """
            ).bindparams(slug=slug)
        )


def downgrade() -> None:
    op.drop_constraint("ck_ingredients_assistant_role", "ingredients", type_="check")
    op.drop_column("ingredients", "assistant_role")
