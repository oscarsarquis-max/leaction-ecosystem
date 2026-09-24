"""Per-item bakery adaptation requests

Revision ID: f7a4e2c19b08
Revises: e2c9b4a81d05
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a4e2c19b08"
down_revision: Union[str, Sequence[str], None] = "e2c9b4a81d05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "order_item_adaptations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_item_id", sa.Uuid(), nullable=False),
        sa.Column("customer_text", sa.String(length=500), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("bakery_response", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("client_decision", sa.String(length=40), nullable=True),
        sa.Column("client_decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "reason IS NULL OR reason IN ('preference','dietary_restriction')",
            name="ck_item_adaptations_reason",
        ),
        sa.CheckConstraint(
            "status IN ('pending','accepted','alternative_proposed','declined','alternative_accepted')",
            name="ck_item_adaptations_status",
        ),
        sa.CheckConstraint(
            "client_decision IS NULL OR client_decision IN ('accepted_alternative','declined')",
            name="ck_item_adaptations_client_decision",
        ),
        sa.CheckConstraint(
            "char_length(customer_text) BETWEEN 1 AND 500",
            name="ck_item_adaptations_customer_text",
        ),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_item_id", name="uq_item_adaptations_item"),
    )
    op.create_table(
        "order_item_adaptation_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("adaptation_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=40), nullable=True),
        sa.Column("to_status", sa.String(length=40), nullable=False),
        sa.Column("actor_kind", sa.String(length=20), nullable=False),
        sa.Column("actor_ref", sa.String(length=80), nullable=True),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "actor_kind IN ('customer','bakery')",
            name="ck_item_adaptation_events_actor",
        ),
        sa.ForeignKeyConstraint(["adaptation_id"], ["order_item_adaptations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_item_adaptation_events_created",
        "order_item_adaptation_events",
        ["adaptation_id", "created_at"],
    )
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed','adaptation_proposed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed')",
    )
    op.drop_index("ix_item_adaptation_events_created", table_name="order_item_adaptation_events")
    op.drop_table("order_item_adaptation_events")
    op.drop_table("order_item_adaptations")
