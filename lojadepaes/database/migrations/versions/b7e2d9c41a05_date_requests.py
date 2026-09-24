"""Date evaluation requests and outbox kinds

Revision ID: b7e2d9c41a05
Revises: f1a8c6d23b90
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b7e2d9c41a05"
down_revision: Union[str, Sequence[str], None] = "f1a8c6d23b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "date_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("desired_date", sa.Date(), nullable=False),
        sa.Column("customer_name", sa.String(length=160), nullable=False),
        sa.Column("customer_email", sa.String(length=254), nullable=False),
        sa.Column("intended_quantity", sa.Integer(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("proposed_date", sa.Date(), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column("cart_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("client_host", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','alternative_proposed','closed')",
            name="ck_date_requests_status",
        ),
        sa.CheckConstraint(
            "intended_quantity IS NULL OR intended_quantity >= 1",
            name="ck_date_requests_quantity",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_date_requests_idempotency"),
    )
    op.create_index("ix_date_requests_status_created", "date_requests", ["status", "created_at"])
    op.create_index("ix_date_requests_email_created", "date_requests", ["customer_email", "created_at"])
    op.create_table(
        "date_request_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("actor_ref", sa.String(length=80), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["date_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_date_request_events_request", "date_request_events", ["request_id", "created_at"])
    op.alter_column("email_outbox", "order_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("email_outbox", sa.Column("date_request_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_email_outbox_date_request",
        "email_outbox",
        "date_requests",
        ["date_request_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted')",
    )
    op.drop_constraint("fk_email_outbox_date_request", "email_outbox", type_="foreignkey")
    op.drop_column("email_outbox", "date_request_id")
    op.alter_column("email_outbox", "order_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_index("ix_date_request_events_request", table_name="date_request_events")
    op.drop_table("date_request_events")
    op.drop_index("ix_date_requests_email_created", table_name="date_requests")
    op.drop_index("ix_date_requests_status_created", table_name="date_requests")
    op.drop_table("date_requests")
