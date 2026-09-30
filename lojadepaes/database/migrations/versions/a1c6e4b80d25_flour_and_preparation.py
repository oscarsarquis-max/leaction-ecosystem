"""Farinha e fermentação/preparo separados no criador.

Revision ID: a1c6e4b80d25
Revises: e5f1c3a82b19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c6e4b80d25"
down_revision: Union[str, Sequence[str], None] = "e5f1c3a82b19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RETIRED_DOUGHS = ("sourdough-classico", "integral", "multigraos")

_PREPARATIONS = (
    (
        "fermentacao-natural-curta",
        "Fermentação natural curta (Classic sourdough)",
        "Massa de fermentação natural, de preparo mais curto.",
        "FERMENTACAO-NATURAL-CURTA",
        0,
    ),
    (
        "maturada",
        "Maturada (Long fermentation)",
        "Massa que descansa mais tempo antes de assar.",
        "MATURADA",
        1,
    ),
    (
        "sovada",
        "Sovada (Kneaded dough)",
        "Massa trabalhada à mão, de miolo mais regular.",
        "SOVADA",
        2,
    ),
)

_FLOURS = (
    ("farinha-branca-strong-white", "Branca (Strong white)", "Farinha branca de trigo.", 1),
    ("farinha-integral-trigo", "Integral de trigo (Whole wheat)", "Farinha de trigo integral.", 2),
    ("farinha-integral-centeio", "Integral de centeio (Whole rye)", "Farinha de centeio integral.", 3),
    ("farinha-fuba", "Fubá (Corn)", "Farinha de milho.", 4),
)


def upgrade() -> None:
    op.add_column("dough_types", sa.Column("creator_kind", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        "ck_dough_types_creator_kind",
        "dough_types",
        "creator_kind IS NULL OR creator_kind IN ('preparation', 'retired_mass')",
    )
    op.execute(
        """
        UPDATE dough_types
        SET creator_kind = 'retired_mass', is_active = false
        WHERE slug IN ('sourdough-classico', 'integral', 'multigraos')
        """
    )
    op.execute(
        """
        UPDATE ingredients
        SET is_active = false
        WHERE slug = 'farinha-branca-italiana'
        """
    )
    for slug, name, description, code, sort_order in _PREPARATIONS:
        op.execute(
            sa.text(
                """
                INSERT INTO recipe_bases (id, code, name, is_active, created_at, updated_at)
                SELECT gen_random_uuid(), :code, :name, true, now(), now()
                WHERE NOT EXISTS (SELECT 1 FROM recipe_bases WHERE code = :code)
                """
            ).bindparams(code=code, name=name)
        )
        op.execute(
            sa.text(
                """
                INSERT INTO dough_types (
                    id, name, slug, short_description, sort_order, is_active, creator_kind,
                    recipe_base_id, created_at, updated_at
                )
                SELECT
                    gen_random_uuid(),
                    :name,
                    :slug,
                    :description,
                    :sort_order,
                    true,
                    'preparation',
                    (SELECT id FROM recipe_bases WHERE code = :code),
                    now(),
                    now()
                WHERE NOT EXISTS (SELECT 1 FROM dough_types WHERE slug = :slug)
                """
            ).bindparams(
                name=name,
                slug=slug,
                description=description,
                sort_order=sort_order,
                code=code,
            )
        )
        op.execute(
            sa.text(
                """
                UPDATE dough_types
                SET creator_kind = 'preparation',
                    is_active = true,
                    name = :name,
                    short_description = :description,
                    recipe_base_id = COALESCE(
                        recipe_base_id,
                        (SELECT id FROM recipe_bases WHERE code = :code)
                    )
                WHERE slug = :slug
                """
            ).bindparams(name=name, description=description, code=code, slug=slug)
        )
    op.execute(
        """
        INSERT INTO dough_shape_compatibilities (id, dough_type_id, bread_shape_id)
        SELECT gen_random_uuid(), dough.id, shape.id
        FROM dough_types dough
        CROSS JOIN bread_shapes shape
        WHERE dough.creator_kind = 'preparation'
          AND dough.is_active
          AND shape.is_active
          AND NOT EXISTS (
              SELECT 1 FROM dough_shape_compatibilities link
              WHERE link.dough_type_id = dough.id AND link.bread_shape_id = shape.id
          )
        """
    )
    for slug, name, description, sort_order in _FLOURS:
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
                    'flour',
                    now(),
                    now()
                WHERE NOT EXISTS (SELECT 1 FROM ingredients WHERE slug = :slug)
                """
            ).bindparams(name=name, slug=slug, description=description, sort_order=sort_order)
        )
        op.execute(
            sa.text(
                """
                UPDATE ingredients
                SET assistant_role = 'flour',
                    is_active = true,
                    name = :name,
                    description = :description
                WHERE slug = :slug
                  AND slug <> 'farinha-branca-italiana'
                """
            ).bindparams(name=name, description=description, slug=slug)
        )


def downgrade() -> None:
    op.drop_constraint("ck_dough_types_creator_kind", "dough_types", type_="check")
    op.drop_column("dough_types", "creator_kind")
