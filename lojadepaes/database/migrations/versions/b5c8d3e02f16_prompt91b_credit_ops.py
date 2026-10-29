"""Prompt 91B: estado da operação de crédito para reconciliação.

Revision ID: b5c8d3e02f16
Revises: a4b7c2d91e05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5c8d3e02f16"
down_revision: Union[str, Sequence[str], None] = "a4b7c2d91e05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gigio_credit_operations",
        sa.Column("operation_id", sa.String(length=80), nullable=False),
        sa.Column("subject_hmac", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reply_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("operation_id"),
    )
    op.create_index(
        "ix_gigio_credit_ops_subject",
        "gigio_credit_operations",
        ["subject_hmac"],
    )


def downgrade() -> None:
    op.drop_index("ix_gigio_credit_ops_subject", table_name="gigio_credit_operations")
    op.drop_table("gigio_credit_operations")
