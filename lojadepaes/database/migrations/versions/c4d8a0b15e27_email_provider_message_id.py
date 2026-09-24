"""SES message id on email outbox

Revision ID: c4d8a0b15e27
Revises: a9c3e71b04d8
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4d8a0b15e27"
down_revision: Union[str, Sequence[str], None] = "a9c3e71b04d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "email_outbox",
        sa.Column("provider_message_id", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("email_outbox", "provider_message_id")
