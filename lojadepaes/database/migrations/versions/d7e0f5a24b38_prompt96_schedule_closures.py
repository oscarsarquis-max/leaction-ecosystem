"""Prompt 96: fechamento de período com histórico.

Revision ID: d7e0f5a24b38
Revises: c6d9e4f13a27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d7e0f5a24b38"
down_revision: Union[str, Sequence[str], None] = "c6d9e4f13a27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedule_closures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("first_eligible_date", sa.Date(), nullable=False),
        sa.Column("pause_intake", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("internal_reason", sa.String(length=120), nullable=False),
        sa.Column("public_notice", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("updated_by", sa.String(length=120), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("end_date >= start_date", name="ck_schedule_closures_range"),
        sa.CheckConstraint(
            "first_eligible_date > start_date",
            name="ck_schedule_closures_first_eligible",
        ),
        sa.CheckConstraint(
            "char_length(internal_reason) BETWEEN 1 AND 120",
            name="ck_schedule_closures_reason",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_closures_active_start",
        "schedule_closures",
        ["cancelled_at", "start_date"],
    )
    op.create_index(
        "uq_schedule_closures_active_period",
        "schedule_closures",
        ["start_date", "end_date"],
        unique=True,
        postgresql_where=sa.text("cancelled_at IS NULL"),
    )
    op.create_table(
        "schedule_closure_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("closure_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("actor_ref", sa.String(length=120), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["closure_id"], ["schedule_closures.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_closure_events_closure",
        "schedule_closure_events",
        ["closure_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_schedule_closure_events_closure", table_name="schedule_closure_events")
    op.drop_table("schedule_closure_events")
    op.drop_index("uq_schedule_closures_active_period", table_name="schedule_closures")
    op.drop_index("ix_schedule_closures_active_start", table_name="schedule_closures")
    op.drop_table("schedule_closures")
