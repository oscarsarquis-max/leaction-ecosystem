"""Deprecia organization_membership.role como legacy_role_label.

Revision ID: 0013_legacy_role_label
Revises: 0012_production_api_roles
Create Date: 2026-08-22
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0013_legacy_role_label"
down_revision: Union[str, Sequence[str], None] = "0012_production_api_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "organization_membership",
        "role",
        new_column_name="legacy_role_label",
    )


def downgrade() -> None:
    op.alter_column(
        "organization_membership",
        "legacy_role_label",
        new_column_name="role",
    )
