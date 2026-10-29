"""Prompt 84A: avaliação de guia distinta da harmonização.

Revision ID: f3c9a1b28e04
Revises: e2b8f4a07d91
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f3c9a1b28e04"
down_revision: Union[str, Sequence[str], None] = "e2b8f4a07d91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_gigio_pairing_evidence", "gigio_pairing_references", type_="check")
    op.create_check_constraint(
        "ck_gigio_pairing_evidence",
        "gigio_pairing_references",
        "evidence_type IN ('pairing_recommendation','official_register',"
        "'research_project','method_help','style_unverified','guide_evaluation')",
    )
    op.drop_constraint("ck_gigio_pairing_retrieval", "gigio_pairing_references", type_="check")
    op.create_check_constraint(
        "ck_gigio_pairing_retrieval",
        "gigio_pairing_references",
        "retrieval_role IN ('pairing','informational','excluded','evaluation')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_gigio_pairing_retrieval", "gigio_pairing_references", type_="check")
    op.create_check_constraint(
        "ck_gigio_pairing_retrieval",
        "gigio_pairing_references",
        "retrieval_role IN ('pairing','informational','excluded')",
    )
    op.drop_constraint("ck_gigio_pairing_evidence", "gigio_pairing_references", type_="check")
    op.create_check_constraint(
        "ck_gigio_pairing_evidence",
        "gigio_pairing_references",
        "evidence_type IN ('pairing_recommendation','official_register',"
        "'research_project','method_help','style_unverified')",
    )
