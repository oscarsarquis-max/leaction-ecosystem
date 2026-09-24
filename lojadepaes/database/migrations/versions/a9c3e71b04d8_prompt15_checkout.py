"""submitted checkout, occupancy on admin accept, email outbox

Revision ID: a9c3e71b04d8
Revises: d1a7c4e90b12
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9c3e71b04d8"
down_revision: Union[str, Sequence[str], None] = "d1a7c4e90b12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_orders_status", "orders", type_="check")
    op.create_check_constraint(
        "ck_orders_status",
        "orders",
        "status IN ('draft','submitted','confirmed','in_production','ready','completed','cancelled')",
    )
    op.drop_constraint("ck_order_status_history_from", "order_status_history", type_="check")
    op.create_check_constraint(
        "ck_order_status_history_from",
        "order_status_history",
        "from_status IS NULL OR from_status IN "
        "('draft','submitted','confirmed','in_production','ready','completed','cancelled')",
    )
    op.drop_constraint("ck_order_status_history_to", "order_status_history", type_="check")
    op.create_check_constraint(
        "ck_order_status_history_to",
        "order_status_history",
        "to_status IN ('draft','submitted','confirmed','in_production','ready','completed','cancelled')",
    )
    op.add_column("orders", sa.Column("access_token_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "orders", sa.Column("submit_idempotency_key", sa.String(length=120), nullable=True)
    )
    op.add_column("orders", sa.Column("proposed_production_date", sa.Date(), nullable=True))
    op.create_index(
        "uq_orders_access_token_hash",
        "orders",
        ["access_token_hash"],
        unique=True,
        postgresql_where=sa.text("access_token_hash IS NOT NULL"),
    )
    op.create_index(
        "uq_orders_submit_idempotency",
        "orders",
        ["submit_idempotency_key"],
        unique=True,
        postgresql_where=sa.text("submit_idempotency_key IS NOT NULL"),
    )
    op.add_column(
        "payment_records", sa.Column("sanitized_error", sa.Text(), nullable=True)
    )
    op.create_table(
        "email_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("to_address", sa.String(length=254), nullable=False),
        sa.Column("subject", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('order_submitted','payment_approved','order_accepted')",
            name="ck_email_outbox_kind",
        ),
        sa.CheckConstraint(
            "status IN ('pending','skipped','sent','failed')",
            name="ck_email_outbox_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_email_outbox_attempts"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key", name="uq_email_outbox_dedupe"),
    )
    op.execute(
        sa.text(
            "UPDATE schedule_settings SET occupancy_enabled = TRUE, "
            "reservation_policy = 'admin_accept' WHERE id = 1"
        )
    )
    op.add_column("payment_records", sa.Column("method", sa.String(length=20), nullable=True))
    op.add_column("payment_records", sa.Column("mp_payment_id", sa.String(length=80), nullable=True))
    op.add_column("payment_records", sa.Column("pix_qr_code", sa.Text(), nullable=True))
    op.add_column("payment_records", sa.Column("pix_qr_code_base64", sa.Text(), nullable=True))
    op.add_column("payment_records", sa.Column("pix_ticket_url", sa.Text(), nullable=True))
    op.add_column(
        "payment_records", sa.Column("pix_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        "ck_payment_records_method",
        "payment_records",
        "method IS NULL OR method IN ('pix','card')",
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE schedule_settings SET occupancy_enabled = FALSE, "
            "reservation_policy = 'unset' WHERE id = 1"
        )
    )
    op.drop_constraint("ck_payment_records_method", "payment_records", type_="check")
    op.drop_column("payment_records", "pix_expires_at")
    op.drop_column("payment_records", "pix_ticket_url")
    op.drop_column("payment_records", "pix_qr_code_base64")
    op.drop_column("payment_records", "pix_qr_code")
    op.drop_column("payment_records", "mp_payment_id")
    op.drop_column("payment_records", "method")
    op.drop_table("email_outbox")
    op.drop_column("payment_records", "sanitized_error")
    op.drop_index("uq_orders_submit_idempotency", table_name="orders")
    op.drop_index("uq_orders_access_token_hash", table_name="orders")
    op.drop_column("orders", "proposed_production_date")
    op.drop_column("orders", "submit_idempotency_key")
    op.drop_column("orders", "access_token_hash")
    op.drop_constraint("ck_order_status_history_to", "order_status_history", type_="check")
    op.create_check_constraint(
        "ck_order_status_history_to",
        "order_status_history",
        "to_status IN ('draft','confirmed','in_production','ready','completed','cancelled')",
    )
    op.drop_constraint("ck_order_status_history_from", "order_status_history", type_="check")
    op.create_check_constraint(
        "ck_order_status_history_from",
        "order_status_history",
        "from_status IS NULL OR from_status IN "
        "('draft','confirmed','in_production','ready','completed','cancelled')",
    )
    op.drop_constraint("ck_orders_status", "orders", type_="check")
    op.create_check_constraint(
        "ck_orders_status",
        "orders",
        "status IN ('draft','confirmed','in_production','ready','completed','cancelled')",
    )
