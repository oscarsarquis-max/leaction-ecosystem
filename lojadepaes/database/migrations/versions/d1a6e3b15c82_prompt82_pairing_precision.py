"""Prompt 82: precisão editorial da base de referências.

Revision ID: d1a6e3b15c82
Revises: c9f5d2e04a71
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d1a6e3b15c82"
down_revision: Union[str, Sequence[str], None] = "c9f5d2e04a71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_gigio_pairing_source_kind", "gigio_pairing_references", type_="check")
    op.alter_column(
        "gigio_pairing_references",
        "source_kind",
        existing_type=sa.String(length=16),
        type_=sa.String(length=32),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_gigio_pairing_source_kind",
        "gigio_pairing_references",
        "source_kind IN ('commercial','independent','producer',"
        "'commercial_editorial','official_register','research_institution')",
    )
    op.add_column(
        "gigio_pairing_references",
        sa.Column("evidence_type", sa.String(length=32), nullable=False, server_default="style_unverified"),
    )
    op.add_column(
        "gigio_pairing_references",
        sa.Column("retrieval_role", sa.String(length=16), nullable=False, server_default="excluded"),
    )
    op.add_column(
        "gigio_pairing_references",
        sa.Column("verification_status", sa.String(length=16), nullable=False, server_default="pending"),
    )
    op.add_column(
        "gigio_pairing_references",
        sa.Column("support_locator", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "gigio_pairing_references",
        sa.Column(
            "claim_layers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_check_constraint(
        "ck_gigio_pairing_evidence",
        "gigio_pairing_references",
        "evidence_type IN ('pairing_recommendation','official_register',"
        "'research_project','method_help','style_unverified')",
    )
    op.create_check_constraint(
        "ck_gigio_pairing_retrieval",
        "gigio_pairing_references",
        "retrieval_role IN ('pairing','informational','excluded')",
    )
    op.create_check_constraint(
        "ck_gigio_pairing_verification",
        "gigio_pairing_references",
        "verification_status IN ('verified','pending','inaccessible')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_gigio_pairing_verification", "gigio_pairing_references", type_="check")
    op.drop_constraint("ck_gigio_pairing_retrieval", "gigio_pairing_references", type_="check")
    op.drop_constraint("ck_gigio_pairing_evidence", "gigio_pairing_references", type_="check")
    op.drop_column("gigio_pairing_references", "claim_layers")
    op.drop_column("gigio_pairing_references", "support_locator")
    op.drop_column("gigio_pairing_references", "verification_status")
    op.drop_column("gigio_pairing_references", "retrieval_role")
    op.drop_column("gigio_pairing_references", "evidence_type")
    op.drop_constraint("ck_gigio_pairing_source_kind", "gigio_pairing_references", type_="check")
    op.alter_column(
        "gigio_pairing_references",
        "source_kind",
        existing_type=sa.String(length=32),
        type_=sa.String(length=16),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_gigio_pairing_source_kind",
        "gigio_pairing_references",
        "source_kind IN ('commercial','independent','producer')",
    )
