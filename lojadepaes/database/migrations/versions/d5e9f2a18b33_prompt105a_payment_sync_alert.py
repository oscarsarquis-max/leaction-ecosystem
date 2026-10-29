"""Aviso operacional de falha persistente de verificação. Não altera pedido antigo.

Revision ID: d5e9f2a18b33
Revises: c4d8e1f07a22
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d5e9f2a18b33"
down_revision: Union[str, Sequence[str], None] = "c4d8e1f07a22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_KINDS = (
    "'order_submitted','payment_approved','order_accepted',"
    "'date_request_received','date_request_proposed','adaptation_proposed',"
    "'customer_verify','customer_resume','order_submitted_admin',"
    "'date_request_received_admin','date_request_available',"
    "'date_request_declined','adaptation_customer_replied_admin',"
    "'ops_attendance_summary','order_auto_accepted_admin',"
    "'date_request_complete','acceptance_update_admin','payment_sync_alert'"
)

_PREVIOUS = (
    "'order_submitted','payment_approved','order_accepted',"
    "'date_request_received','date_request_proposed','adaptation_proposed',"
    "'customer_verify','customer_resume','order_submitted_admin',"
    "'date_request_received_admin','date_request_available',"
    "'date_request_declined','adaptation_customer_replied_admin',"
    "'ops_attendance_summary','order_auto_accepted_admin',"
    "'date_request_complete','acceptance_update_admin'"
)


def upgrade() -> None:
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        f"kind IN ({_KINDS})",
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM email_outbox WHERE kind = 'payment_sync_alert'"
    )
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        f"kind IN ({_PREVIOUS})",
    )
