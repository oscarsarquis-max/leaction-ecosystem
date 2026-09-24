"""Admin accounts and one-time activation tokens

Revision ID: c3a9f0b18d22
Revises: b7e2d9c41a05
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3a9f0b18d22"
down_revision: Union[str, Sequence[str], None] = "b7e2d9c41a05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("password_set_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_admin_accounts_username"),
    )
    op.create_table(
        "admin_activation_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=40), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_admin_activation_token_hash"),
    )
    op.create_index(
        "ix_admin_activation_username_created",
        "admin_activation_tokens",
        ["username", "created_at"],
    )
    op.create_table(
        "admin_activation_dispatches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("recipient", sa.String(length=254), nullable=False),
        sa.Column("provider_message_id", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_activation_dispatch_sent",
        "admin_activation_dispatches",
        ["username", "sent_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_admin_activation_dispatch_sent", table_name="admin_activation_dispatches")
    op.drop_table("admin_activation_dispatches")
    op.drop_index("ix_admin_activation_username_created", table_name="admin_activation_tokens")
    op.drop_table("admin_activation_tokens")
    op.drop_table("admin_accounts")
