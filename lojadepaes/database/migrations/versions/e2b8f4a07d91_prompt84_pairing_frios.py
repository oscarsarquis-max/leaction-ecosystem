"""Prompt 84: categoria frios na base de referências.

Revision ID: e2b8f4a07d91
Revises: d1a6e3b15c82
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e2b8f4a07d91"
down_revision: Union[str, Sequence[str], None] = "d1a6e3b15c82"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_gigio_pairing_category", "gigio_pairing_references", type_="check")
    op.create_check_constraint(
        "ck_gigio_pairing_category",
        "gigio_pairing_references",
        "category IN ('vinhos','queijos','azeites','frios')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_gigio_pairing_category", "gigio_pairing_references", type_="check")
    op.create_check_constraint(
        "ck_gigio_pairing_category",
        "gigio_pairing_references",
        "category IN ('vinhos','queijos','azeites')",
    )
