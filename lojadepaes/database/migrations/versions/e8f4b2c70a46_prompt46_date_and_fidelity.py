"""Prompt 46: data mínima, elegibilidade da vitrine e histórico de regras.

Revision ID: e8f4b2c70a46
Revises: d6b2e9f15c38
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8f4b2c70a46"
down_revision: Union[str, Sequence[str], None] = "d6b2e9f15c38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FOCACCIA_SLUG = "focaccia-alta-italian-focaccia"
_RULES_46 = (
    '{"valid_order":"closed_and_paid","closed_means":"admin_accept_confirmed_at",'
    '"paid_means":"server_reconciled_bread_net","credit_size":4,'
    '"reward":"one_500g_showcase_loaf_excluding_focaccia","freight_separate":true,'
    '"no_price_cap":true,"timezone":"America/Sao_Paulo",'
    '"cycle":"civil_month","credits_do_not_expire":true,'
    '"no_historical_import":true,"no_retroactive_link":true,'
    '"delivery_not_required_for_stamp":true,'
    '"partial_refund":"admin_review_pending_no_auto_decision",'
    '"custom_loaf_does_not_qualify":true,'
    '"eligibility_field":"products.fidelity_eligible"}'
)


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("fidelity_eligible", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column("products", "fidelity_eligible", server_default=None)
    op.execute(
        sa.text("UPDATE products SET fidelity_eligible = false WHERE slug = :slug").bindparams(
            slug=FOCACCIA_SLUG
        )
    )
    op.add_column("orders", sa.Column("fidelity_qualifies", sa.Boolean(), nullable=True))
    op.add_column(
        "house_fidelity_campaigns",
        sa.Column("rules_effective_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "house_fidelity_rule_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("previous_rules_version", sa.String(length=20), nullable=False),
        sa.Column("new_rules_version", sa.String(length=20), nullable=False),
        sa.Column("previous_rules_json", sa.Text(), nullable=False),
        sa.Column("new_rules_json", sa.Text(), nullable=False),
        sa.Column("starts_at_preserved", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["campaign_id"], ["house_fidelity_campaigns.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    conn = op.get_bind()
    row = conn.execute(
        sa.text(
            "SELECT id, rules_version, rules_json, starts_at FROM house_fidelity_campaigns "
            "WHERE slug = 'carimbos-da-casa' ORDER BY version DESC LIMIT 1"
        )
    ).first()
    if row is not None and row.rules_version != "46":
        conn.execute(
            sa.text(
                "INSERT INTO house_fidelity_rule_changes "
                "(id, campaign_id, previous_rules_version, new_rules_version, previous_rules_json, "
                "new_rules_json, starts_at_preserved, effective_at) "
                "VALUES (gen_random_uuid(), :campaign_id, :prev, '46', :prev_json, :new_json, :starts, now())"
            ),
            {
                "campaign_id": row.id,
                "prev": row.rules_version,
                "prev_json": row.rules_json,
                "new_json": _RULES_46,
                "starts": row.starts_at,
            },
        )
        conn.execute(
            sa.text(
                "UPDATE house_fidelity_campaigns SET rules_version = '46', rules_json = :rules, "
                "rules_effective_at = now() WHERE id = :campaign_id"
            ),
            {"rules": _RULES_46, "campaign_id": row.id},
        )


def downgrade() -> None:
    op.drop_table("house_fidelity_rule_changes")
    op.drop_column("house_fidelity_campaigns", "rules_effective_at")
    op.drop_column("orders", "fidelity_qualifies")
    op.drop_column("products", "fidelity_eligible")
