"""Prompt 67: respostas de data e resumo operacional.

Revision ID: f2c8e4a91b30
Revises: e1b6d3f82a19
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f2c8e4a91b30"
down_revision: Union[str, Sequence[str], None] = "e1b6d3f82a19"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed','adaptation_proposed',"
        "'customer_verify','customer_resume','order_submitted_admin',"
        "'date_request_received_admin')",
    )
