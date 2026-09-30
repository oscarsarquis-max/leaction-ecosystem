"""Prompt 53: aviso administrativo na outbox.

Revision ID: b3f7a1c82e09
Revises: a0d2b7e91f58
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b3f7a1c82e09"
down_revision: Union[str, Sequence[str], None] = "a0d2b7e91f58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed','adaptation_proposed',"
        "'customer_verify','customer_resume','order_submitted_admin')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_email_outbox_kind", "email_outbox", type_="check")
    op.create_check_constraint(
        "ck_email_outbox_kind",
        "email_outbox",
        "kind IN ('order_submitted','payment_approved','order_accepted',"
        "'date_request_received','date_request_proposed','adaptation_proposed',"
        "'customer_verify','customer_resume')",
    )
