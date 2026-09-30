"""Preço do pão personalizado e peso no item.

Revision ID: c31a7e90b4d1
Revises: a8d4c1e07b33
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c31a7e90b4d1"
down_revision: Union[str, Sequence[str], None] = "a8d4c1e07b33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "schedule_settings",
        sa.Column("custom_loaf_price_cents", sa.Integer(), server_default="7000", nullable=False),
    )
    op.add_column(
        "schedule_settings",
        sa.Column("custom_loaf_weight_grams", sa.Integer(), server_default="500", nullable=False),
    )
    op.create_check_constraint(
        "ck_schedule_settings_custom_price", "schedule_settings", "custom_loaf_price_cents > 0"
    )
    op.create_check_constraint(
        "ck_schedule_settings_custom_weight", "schedule_settings", "custom_loaf_weight_grams > 0"
    )
    op.add_column("order_items", sa.Column("net_weight_grams", sa.Integer(), nullable=True))
    op.execute(
        """
        INSERT INTO ingredients (
            id, name, slug, description, sort_order, is_active, surcharge_cents, created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            'Farinha branca italiana',
            'farinha-branca-italiana',
            'Farinha branca de origem italiana. Propriedades, alergênicos e compatibilidades ainda pendentes de configuração.',
            80,
            true,
            NULL,
            now(),
            now()
        WHERE NOT EXISTS (
            SELECT 1 FROM ingredients WHERE slug = 'farinha-branca-italiana'
        )
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM ingredients WHERE slug = 'farinha-branca-italiana' AND surcharge_cents IS NULL")
    op.drop_column("order_items", "net_weight_grams")
    op.drop_constraint("ck_schedule_settings_custom_weight", "schedule_settings", type_="check")
    op.drop_constraint("ck_schedule_settings_custom_price", "schedule_settings", type_="check")
    op.drop_column("schedule_settings", "custom_loaf_weight_grams")
    op.drop_column("schedule_settings", "custom_loaf_price_cents")
