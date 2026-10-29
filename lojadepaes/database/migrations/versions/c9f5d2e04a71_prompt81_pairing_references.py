"""Prompt 81: referências especializadas de harmonização (aditivo).

Revision ID: c9f5d2e04a71
Revises: b8e4c1d93f50
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9f5d2e04a71"
down_revision: Union[str, Sequence[str], None] = "b8e4c1d93f50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gigio_pairing_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("profile_key", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("synthesis", sa.Text(), nullable=False),
        sa.Column("editorial_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("characteristics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("culinary_contexts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("match_hints", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("identity", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("source_title", sa.String(length=240), nullable=False),
        sa.Column("source_author", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("source_date", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("consulted_at", sa.String(length=32), nullable=False),
        sa.Column("source_kind", sa.String(length=16), nullable=False),
        sa.Column("commercial_relation", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("editorial_status", sa.String(length=16), nullable=False, server_default="draft"),
        sa.Column("reviewed_by", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("reviewed_at", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("loja_choice", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("category IN ('vinhos','queijos','azeites')", name="ck_gigio_pairing_category"),
        sa.CheckConstraint("scope IN ('general','style','product')", name="ck_gigio_pairing_scope"),
        sa.CheckConstraint(
            "editorial_status IN ('draft','reviewed','published','archived')",
            name="ck_gigio_pairing_status",
        ),
        sa.CheckConstraint(
            "source_kind IN ('commercial','independent','producer')",
            name="ck_gigio_pairing_source_kind",
        ),
        sa.CheckConstraint("char_length(profile_key) BETWEEN 1 AND 80", name="ck_gigio_pairing_profile"),
        sa.CheckConstraint("char_length(title) BETWEEN 1 AND 160", name="ck_gigio_pairing_title"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_key", name="uq_gigio_pairing_profile"),
    )


def downgrade() -> None:
    op.drop_table("gigio_pairing_references")
