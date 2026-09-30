"""Fidelidade: revisão administrativa de estorno parcial.

Revision ID: d6b2e9f15c38
Revises: c5a1d8e04b27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6b2e9f15c38"
down_revision: Union[str, Sequence[str], None] = "c5a1d8e04b27"
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
    '"partial_refund":"admin_review_pending_no_auto_decision"}'
)


def upgrade() -> None:
    op.drop_constraint("ck_house_fidelity_events_kind", "house_fidelity_events", type_="check")
    op.create_check_constraint(
        "ck_house_fidelity_events_kind",
        "house_fidelity_events",
        "kind IN ('qualify','reverse','manual_grant','manual_reverse','partial_review')",
    )
    op.drop_constraint("ck_house_fidelity_events_status", "house_fidelity_events", type_="check")
    op.create_check_constraint(
        "ck_house_fidelity_events_status",
        "house_fidelity_events",
        "status IN ('applied','reversed','pending')",
    )
    op.execute(
        sa.text(
            "UPDATE house_fidelity_campaigns "
            "SET rules_version = '44', rules_json = :rules "
            "WHERE slug = 'carimbos-da-casa' AND status = 'draft'"
        ).bindparams(rules=_RULES)
    )


def downgrade() -> None:
    previous = (
        '{"valid_order":"closed_and_paid","closed_means":"admin_accept_confirmed_at",'
        '"paid_means":"server_reconciled_bread_net","credit_size":4,'
        '"reward":"one_500g_showcase_loaf","freight_separate":true,'
        '"no_price_cap":true,"timezone":"America/Sao_Paulo",'
        '"cycle":"civil_month","credits_do_not_expire":true,'
        '"no_historical_import":true,"no_retroactive_link":true,'
        '"delivery_not_required_for_stamp":true,'
        '"partial_refund":"keep_if_net_bread_paid_positive_else_reverse"}'
    )
    op.execute(
        sa.text(
            "UPDATE house_fidelity_campaigns "
            "SET rules_version = '43a', rules_json = :rules "
            "WHERE slug = 'carimbos-da-casa' AND status = 'draft'"
        ).bindparams(rules=previous)
    )
    op.drop_constraint("ck_house_fidelity_events_status", "house_fidelity_events", type_="check")
    op.create_check_constraint(
        "ck_house_fidelity_events_status",
        "house_fidelity_events",
        "status IN ('applied','reversed')",
    )
    op.drop_constraint("ck_house_fidelity_events_kind", "house_fidelity_events", type_="check")
    op.create_check_constraint(
        "ck_house_fidelity_events_kind",
        "house_fidelity_events",
        "kind IN ('qualify','reverse','manual_grant','manual_reverse')",
    )
