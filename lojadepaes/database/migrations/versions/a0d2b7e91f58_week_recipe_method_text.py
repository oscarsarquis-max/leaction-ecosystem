"""Prompt 49: texto único de preparo, sem apagar passos.

Revision ID: a0d2b7e91f58
Revises: f9c1a6d80e47
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a0d2b7e91f58"
down_revision: Union[str, Sequence[str], None] = "f9c1a6d80e47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("week_recipes", sa.Column("method_text", sa.Text(), nullable=True))
    op.alter_column(
        "week_recipe_steps",
        "body",
        existing_type=sa.String(length=2000),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "week_recipe_steps",
        "body",
        existing_type=sa.Text(),
        type_=sa.String(length=2000),
        existing_nullable=False,
    )
    op.drop_column("week_recipes", "method_text")
