"""Web Push administrativo. Não apaga pedido nem aviso antigo.

Revision ID: c4d8e1f07a22
Revises: f9c2a6e81b04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d8e1f07a22"
down_revision: Union[str, Sequence[str], None] = "f9c2a6e81b04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_push_subscriptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("actor_ref", sa.String(length=120), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("p256dh", sa.String(length=200), nullable=False),
        sa.Column("auth_secret", sa.String(length=200), nullable=False),
        sa.Column("label", sa.String(length=40), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=280), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("endpoint_hash", name="uq_admin_push_endpoint"),
    )
    op.create_index("ix_admin_push_actor_active", "admin_push_subscriptions", ["actor_ref", "active"])
    op.create_table(
        "ops_push_deliveries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_key", sa.String(length=160), nullable=False),
        sa.Column("subscription_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.String(length=180), nullable=False),
        sa.Column("path", sa.String(length=200), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=280), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('awaiting','accepted','failed','inactive')",
            name="ck_ops_push_deliveries_status",
        ),
        sa.UniqueConstraint("event_key", "subscription_id", name="uq_ops_push_event_device"),
    )


def downgrade() -> None:
    op.drop_table("ops_push_deliveries")
    op.drop_index("ix_admin_push_actor_active", table_name="admin_push_subscriptions")
    op.drop_table("admin_push_subscriptions")
