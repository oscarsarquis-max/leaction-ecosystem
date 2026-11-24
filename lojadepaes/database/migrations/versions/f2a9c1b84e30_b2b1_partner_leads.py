"""Leads da página /b2b (interesse de parceiros). Só marketplace.partner_leads.

Revision ID: f2a9c1b84e30
Revises: a5c3e8b17d42
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a9c1b84e30"
down_revision: Union[str, Sequence[str], None] = "a5c3e8b17d42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "marketplace"


def upgrade() -> None:
    op.create_table(
        "partner_leads",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("city", sa.String(length=80), nullable=False),
        sa.Column("whatsapp", sa.String(length=40), nullable=False),
        sa.Column("email", sa.String(length=160), nullable=False),
        sa.Column("link", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("message", sa.String(length=1500), nullable=False),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="new"),
        sa.CheckConstraint("status IN ('new')", name="ck_mp_partner_leads_status"),
        schema=_SCHEMA,
    )
    op.create_index(
        "ix_mp_partner_leads_ip_created",
        "partner_leads",
        ["ip_hash", "created_at"],
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("ix_mp_partner_leads_ip_created", table_name="partner_leads", schema=_SCHEMA)
    op.drop_table("partner_leads", schema=_SCHEMA)
