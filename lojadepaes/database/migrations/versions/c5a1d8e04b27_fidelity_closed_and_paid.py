"""Adendo 43A: compra válida é fechada e paga, sem retroatividade.

Revision ID: c5a1d8e04b27
Revises: b2d8f4a91c30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c5a1d8e04b27"
down_revision: Union[str, Sequence[str], None] = "b2d8f4a91c30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RULES = (
    '{"valid_order":"closed_and_paid","closed_means":"admin_accept_confirmed_at",'
    '"paid_means":"server_reconciled_bread_net","credit_size":4,'
    '"reward":"one_500g_showcase_loaf","freight_separate":true,'
    '"no_price_cap":true,"timezone":"America/Sao_Paulo",'
    '"cycle":"civil_month","credits_do_not_expire":true,'
    '"no_historical_import":true,"no_retroactive_link":true,'
    '"delivery_not_required_for_stamp":true,'
    '"partial_refund":"keep_if_net_bread_paid_positive_else_reverse"}'
)


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE house_fidelity_campaigns "
            "SET rules_version = '43a', rules_json = :rules "
            "WHERE slug = 'carimbos-da-casa' AND status = 'draft'"
        ).bindparams(rules=_RULES)
    )


def downgrade() -> None:
    previous = (
        '{"valid_order":"paid_and_fulfilled","credit_size":4,'
        '"reward":"one_500g_showcase_loaf","freight_separate":true,'
        '"no_price_cap":true,"timezone":"America/Sao_Paulo",'
        '"cycle":"civil_month","credits_do_not_expire":true,'
        '"no_historical_import":true,'
        '"partial_refund":"keep_if_net_bread_paid_positive_else_reverse"}'
    )
    op.execute(
        sa.text(
            "UPDATE house_fidelity_campaigns "
            "SET rules_version = '43', rules_json = :rules "
            "WHERE slug = 'carimbos-da-casa' AND status = 'draft'"
        ).bindparams(rules=previous)
    )
