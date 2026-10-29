"""Prompt 91: medição de uso do Gigio e cache de autorização do Hub.

Revision ID: a4b7c2d91e05
Revises: f3c9a1b28e04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4b7c2d91e05"
down_revision: Union[str, Sequence[str], None] = "f3c9a1b28e04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gigio_usage_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("origin", sa.String(length=20), nullable=False),
        sa.Column("function", sa.String(length=32), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("fail_kind", sa.String(length=40), nullable=True),
        sa.Column("subject_hmac", sa.String(length=64), nullable=True),
        sa.Column("article_id", sa.String(length=80), nullable=True),
        sa.Column("provider", sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_gigio_usage_origin_created",
        "gigio_usage_events",
        ["origin", "created_at"],
    )
    op.create_table(
        "hub_authorization_cache",
        sa.Column("subject_hmac", sa.String(length=64), nullable=False),
        sa.Column("app_id", sa.String(length=40), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("plan_sku", sa.String(length=80), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("subject_hmac"),
    )


def downgrade() -> None:
    op.drop_table("hub_authorization_cache")
    op.drop_index("ix_gigio_usage_origin_created", table_name="gigio_usage_events")
    op.drop_table("gigio_usage_events")
