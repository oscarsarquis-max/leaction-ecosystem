"""Cadastro de cliente, campanha e livro da fidelidade da casa.

Revision ID: b2d8f4a91c30
Revises: a1c6e4b80d25
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2d8f4a91c30"
down_revision: Union[str, Sequence[str], None] = "a1c6e4b80d25"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RULES = (
    '{"valid_order":"paid_and_fulfilled","credit_size":4,'
    '"reward":"one_500g_showcase_loaf","freight_separate":true,'
    '"no_price_cap":true,"timezone":"America/Sao_Paulo",'
    '"cycle":"civil_month","credits_do_not_expire":true,'
    '"no_historical_import":true,'
    '"partial_refund":"keep_if_net_bread_paid_positive_else_reverse"}'
)


def upgrade() -> None:
    op.create_table(
        "customer_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column("cpf_hmac", sa.String(length=64), nullable=False),
        sa.Column("cpf_last2", sa.String(length=2), nullable=False),
        sa.Column("marketing_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_customer_accounts_email"),
        sa.UniqueConstraint("cpf_hmac", name="uq_customer_accounts_cpf_hmac"),
    )
    op.create_index("ix_customer_accounts_created", "customer_accounts", ["created_at"])
    op.create_table(
        "customer_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["account_id"], ["customer_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_customer_sessions_expires", "customer_sessions", ["expires_at"])
    op.create_table(
        "customer_challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid()),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["customer_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_customer_challenges_token"),
    )
    op.create_index(
        "ix_customer_challenges_email_created", "customer_challenges", ["email", "created_at"]
    )
    op.create_table(
        "house_fidelity_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rules_version", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("rules_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('draft','paused','active')", name="ck_house_fidelity_campaigns_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", "version", name="uq_house_fidelity_campaigns_slug_version"),
    )
    op.create_table(
        "house_fidelity_enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("rules_version", sa.String(length=20), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["customer_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["house_fidelity_campaigns.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id", "campaign_id", name="uq_house_fidelity_enrollments_account_campaign"
        ),
    )
    op.add_column(
        "orders",
        sa.Column("order_kind", sa.String(length=20), nullable=False, server_default="standard"),
    )
    op.add_column("orders", sa.Column("fulfilled_at", sa.DateTime(timezone=True)))
    op.add_column("orders", sa.Column("fidelity_account_id", sa.Uuid()))
    op.add_column("orders", sa.Column("fidelity_campaign_id", sa.Uuid()))
    op.add_column("orders", sa.Column("fidelity_rules_version", sa.String(length=20)))
    op.add_column(
        "orders",
        sa.Column("fidelity_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("orders", sa.Column("fidelity_credit_id", sa.Uuid()))
    op.create_check_constraint("ck_orders_kind", "orders", "order_kind IN ('standard','redemption')")
    op.create_foreign_key(
        "fk_orders_fidelity_account",
        "orders",
        "customer_accounts",
        ["fidelity_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_orders_fidelity_campaign",
        "orders",
        "house_fidelity_campaigns",
        ["fidelity_campaign_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_table(
        "house_fidelity_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid()),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("cycle_year", sa.Integer(), nullable=False),
        sa.Column("cycle_month", sa.Integer(), nullable=False),
        sa.Column("eligible_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=280), nullable=False, server_default=""),
        sa.Column("actor_ref", sa.String(length=80)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('qualify','reverse','manual_grant','manual_reverse')",
            name="ck_house_fidelity_events_kind",
        ),
        sa.CheckConstraint("status IN ('applied','reversed')", name="ck_house_fidelity_events_status"),
        sa.ForeignKeyConstraint(["account_id"], ["customer_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["house_fidelity_campaigns.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "order_id", "kind", name="uq_house_fidelity_events_order_kind"),
    )
    op.create_index(
        "ix_house_fidelity_events_account_cycle",
        "house_fidelity_events",
        ["account_id", "cycle_year", "cycle_month"],
    )
    op.create_table(
        "house_fidelity_credits",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("source_event_id", sa.Uuid(), nullable=False),
        sa.Column("cycle_year", sa.Integer(), nullable=False),
        sa.Column("cycle_month", sa.Integer(), nullable=False),
        sa.Column("group_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reserved_order_id", sa.Uuid()),
        sa.Column("used_order_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('available','reserved','used','returned')",
            name="ck_house_fidelity_credits_status",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["customer_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["house_fidelity_campaigns.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_event_id"], ["house_fidelity_events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reserved_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["used_order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "campaign_id",
            "account_id",
            "cycle_year",
            "cycle_month",
            "group_index",
            name="uq_house_fidelity_credits_group",
        ),
    )
    op.create_index(
        "ix_house_fidelity_credits_account_status",
        "house_fidelity_credits",
        ["account_id", "status"],
    )
    op.create_table(
        "house_fidelity_adjustments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=280), nullable=False),
        sa.Column("actor_ref", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["customer_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["house_fidelity_campaigns.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed','adaptation_proposed',"
        "'customer_verify','customer_resume')",
    )
    op.execute(
        sa.text(
            "INSERT INTO house_fidelity_campaigns "
            "(id, slug, version, status, rules_version, title, starts_at, rules_json) "
            "VALUES (gen_random_uuid(), 'carimbos-da-casa', 1, 'draft', '43', "
            "'Fidelidade da casa', NULL, :rules)"
        ).bindparams(rules=_RULES)
    )


def downgrade() -> None:
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed','adaptation_proposed')",
    )
    op.drop_table("house_fidelity_adjustments")
    op.drop_table("house_fidelity_credits")
    op.drop_table("house_fidelity_events")
    op.drop_constraint("fk_orders_fidelity_campaign", "orders", type_="foreignkey")
    op.drop_constraint("fk_orders_fidelity_account", "orders", type_="foreignkey")
    op.drop_constraint("ck_orders_kind", "orders", type_="check")
    op.drop_column("orders", "fidelity_credit_id")
    op.drop_column("orders", "fidelity_opt_in")
    op.drop_column("orders", "fidelity_rules_version")
    op.drop_column("orders", "fidelity_campaign_id")
    op.drop_column("orders", "fidelity_account_id")
    op.drop_column("orders", "fulfilled_at")
    op.drop_column("orders", "order_kind")
    op.drop_table("house_fidelity_enrollments")
    op.drop_table("house_fidelity_campaigns")
    op.drop_table("customer_challenges")
    op.drop_index("ix_customer_sessions_expires", table_name="customer_sessions")
    op.drop_table("customer_sessions")
    op.drop_index("ix_customer_accounts_created", table_name="customer_accounts")
    op.drop_table("customer_accounts")
