"""admin sessions, capacity hold flag and order history actor

Revision ID: b4e8d2a91c70
Revises: 28420c077dcd
Create Date: 2026-09-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4e8d2a91c70"
down_revision: Union[str, Sequence[str], None] = "28420c077dcd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("holds_capacity", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(
        """
        UPDATE orders
        SET holds_capacity = true
        WHERE status IN ('confirmed', 'in_production', 'ready', 'completed')
           OR (status = 'cancelled' AND production_started_at IS NOT NULL)
        """
    )
    op.create_index(
        "ix_orders_batch_holds_capacity",
        "orders",
        ["production_batch_id"],
        postgresql_where=sa.text("holds_capacity"),
    )
    op.create_index(
        "ix_orders_slot_holds_capacity",
        "orders",
        ["fulfillment_slot_id"],
        postgresql_where=sa.text("holds_capacity"),
    )
    op.add_column("order_status_history", sa.Column("actor_ref", sa.String(length=80), nullable=True))
    op.create_check_constraint(
        "ck_order_internal_notes_body",
        "order_internal_notes",
        "char_length(body) BETWEEN 1 AND 2000",
    )
    op.create_table(
        "admin_sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_host", sa.String(length=80), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_admin_sessions_expires_at", "admin_sessions", ["expires_at"])
    op.create_table(
        "admin_login_attempts",
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("client_host", sa.String(length=80), nullable=False),
        sa.Column("succeeded", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_login_attempts_user_created",
        "admin_login_attempts",
        ["username", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_admin_login_attempts_user_created", table_name="admin_login_attempts")
    op.drop_table("admin_login_attempts")
    op.drop_index("ix_admin_sessions_expires_at", table_name="admin_sessions")
    op.drop_table("admin_sessions")
    op.drop_constraint("ck_order_internal_notes_body", "order_internal_notes", type_="check")
    op.drop_column("order_status_history", "actor_ref")
    op.drop_index("ix_orders_slot_holds_capacity", table_name="orders")
    op.drop_index("ix_orders_batch_holds_capacity", table_name="orders")
    op.drop_column("orders", "holds_capacity")
