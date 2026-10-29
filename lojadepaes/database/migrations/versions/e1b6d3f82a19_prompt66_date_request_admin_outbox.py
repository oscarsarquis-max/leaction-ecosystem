"""Prompt 66: aviso administrativo de solicitação de data.

Revision ID: e1b6d3f82a19
Revises: c8e2f1a90b64
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e1b6d3f82a19"
down_revision: Union[str, Sequence[str], None] = "c8e2f1a90b64"
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
        "'date_request_received_admin')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed','adaptation_proposed',"
        "'customer_verify','customer_resume','order_submitted_admin')",
    )
