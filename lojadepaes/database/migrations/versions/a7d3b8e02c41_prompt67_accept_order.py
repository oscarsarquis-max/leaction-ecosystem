"""Prompt 67: aceite formaliza pedido e reserva.

Revision ID: a7d3b8e02c41
Revises: f2c8e4a91b30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7d3b8e02c41"
down_revision: Union[str, Sequence[str], None] = "f2c8e4a91b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "date_requests",
        sa.Column("converted_order_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "date_requests",
        sa.Column("accept_authorized_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("date_requests", sa.Column("complement", sa.JSON(), nullable=True))
    op.create_unique_constraint(
        "uq_date_requests_converted_order", "date_requests", ["converted_order_id"]
    )
    op.create_foreign_key(
        "fk_date_requests_converted_order",
        "date_requests",
        "orders",
        ["converted_order_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint("ck_date_requests_status", "date_requests", type_="check")
    op.create_check_constraint(
        "ck_date_requests_status",
        "date_requests",
        "status IN ('pending','alternative_proposed','awaiting_details','converted','closed')",
    )
    op.add_column("orders", sa.Column("source_date_request_id", sa.Uuid(), nullable=True))
    op.create_unique_constraint(
        "uq_orders_source_date_request", "orders", ["source_date_request_id"]
    )
    op.create_foreign_key(
        "fk_orders_source_date_request",
        "orders",
        "date_requests",
        ["source_date_request_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed','adaptation_proposed',"
        "'customer_verify','customer_resume','order_submitted_admin',"
        "'date_request_received_admin','date_request_available',"
        "'date_request_declined','adaptation_customer_replied_admin',"
        "'ops_attendance_summary','order_auto_accepted_admin',"
        "'date_request_complete')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed','adaptation_proposed',"
        "'customer_verify','customer_resume','order_submitted_admin',"
        "'date_request_received_admin','date_request_available',"
        "'date_request_declined','adaptation_customer_replied_admin',"
        "'ops_attendance_summary')",
    )
    op.drop_constraint("fk_orders_source_date_request", "orders", type_="foreignkey")
    op.drop_constraint("uq_orders_source_date_request", "orders", type_="unique")
    op.drop_column("orders", "source_date_request_id")
    op.drop_constraint("ck_date_requests_status", "date_requests", type_="check")
    op.create_check_constraint(
        "ck_date_requests_status",
        "date_requests",
        "status IN ('pending','alternative_proposed','closed')",
    )
    op.drop_constraint("fk_date_requests_converted_order", "date_requests", type_="foreignkey")
    op.drop_constraint("uq_date_requests_converted_order", "date_requests", type_="unique")
    op.drop_column("date_requests", "complement")
    op.drop_column("date_requests", "accept_authorized_at")
    op.drop_column("date_requests", "converted_order_id")
