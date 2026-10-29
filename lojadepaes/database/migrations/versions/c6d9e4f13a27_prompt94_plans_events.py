"""Prompt 94: eventos isolados de planos da Biblioteca.

Revision ID: c6d9e4f13a27
Revises: b5c8d3e02f16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c6d9e4f13a27"
down_revision: Union[str, Sequence[str], None] = "b5c8d3e02f16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "hub_plans_events",
        sa.Column("event_id", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("subject_hmac", sa.String(length=64), nullable=True),
        sa.Column("business_status", sa.String(length=40), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("process_status", sa.String(length=20), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index(
        "ix_hub_plans_events_subject",
        "hub_plans_events",
        ["subject_hmac", "received_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_hub_plans_events_subject", table_name="hub_plans_events")
    op.drop_table("hub_plans_events")
