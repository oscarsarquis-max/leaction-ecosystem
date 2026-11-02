"""Data solicitada, exceção de data e anulação por duplicidade. Só acrescenta.

Revision ID: e7b3c9a41d06
Revises: d5e9f2a18b33
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7b3c9a41d06"
down_revision: Union[str, Sequence[str], None] = "d5e9f2a18b33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_KINDS = (
    "'order_submitted','payment_approved','order_accepted',"
    "'date_request_received','date_request_proposed','adaptation_proposed',"
    "'customer_verify','customer_resume','order_submitted_admin',"
    "'date_request_received_admin','date_request_available',"
    "'date_request_declined','adaptation_customer_replied_admin',"
    "'ops_attendance_summary','order_auto_accepted_admin',"
    "'date_request_complete','acceptance_update_admin','payment_sync_alert',"
    "'order_date_changed'"
)

_PREVIOUS = (
    "'order_submitted','payment_approved','order_accepted',"
    "'date_request_received','date_request_proposed','adaptation_proposed',"
    "'customer_verify','customer_resume','order_submitted_admin',"
    "'date_request_received_admin','date_request_available',"
    "'date_request_declined','adaptation_customer_replied_admin',"
    "'ops_attendance_summary','order_auto_accepted_admin',"
    "'date_request_complete','acceptance_update_admin','payment_sync_alert'"
)


def upgrade() -> None:
    op.add_column("orders", sa.Column("requested_date", sa.Date(), nullable=True))
    op.add_column("orders", sa.Column("date_change_origin", sa.String(length=20), nullable=True))
    op.add_column("orders", sa.Column("date_change_reason", sa.String(length=280), nullable=True))
    op.add_column("orders", sa.Column("date_change_actor", sa.String(length=120), nullable=True))
    op.execute("UPDATE orders SET requested_date = production_local_date WHERE requested_date IS NULL")
    op.create_check_constraint(
        "ck_orders_date_change_origin",
        "orders",
        "date_change_origin IS NULL OR date_change_origin IN ('customer','store')",
    )
    op.add_column(
        "managerial_exclusions",
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="test"),
    )
    op.add_column(
        "managerial_exclusions",
        sa.Column("original_order_id", sa.Uuid(), nullable=True),
    )
    op.create_check_constraint(
        "ck_managerial_exclusions_kind",
        "managerial_exclusions",
        "kind IN ('test','duplicate')",
    )
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        f"kind IN ({_KINDS})",
    )


def downgrade() -> None:
    op.execute("DELETE FROM email_outbox WHERE kind = 'order_date_changed'")
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        f"kind IN ({_PREVIOUS})",
    )
    op.drop_constraint("ck_managerial_exclusions_kind", "managerial_exclusions", type_="check")
    op.drop_column("managerial_exclusions", "original_order_id")
    op.drop_column("managerial_exclusions", "kind")
    op.drop_constraint("ck_orders_date_change_origin", "orders", type_="check")
    op.drop_column("orders", "date_change_actor")
    op.drop_column("orders", "date_change_reason")
    op.drop_column("orders", "date_change_origin")
    op.drop_column("orders", "requested_date")
