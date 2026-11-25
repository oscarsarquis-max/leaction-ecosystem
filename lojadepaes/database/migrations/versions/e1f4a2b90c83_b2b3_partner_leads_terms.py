"""B2B3: aceite dos termos de parceria no interessado /b2b.

- marketplace.partner_leads.terms_version (text null)
- marketplace.partner_leads.terms_accepted_at (timestamptz null)
Interessados antigos ficam nulos.

Revision ID: e1f4a2b90c83
Revises: d8b3f1a65c92
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f4a2b90c83"
down_revision: Union[str, Sequence[str], None] = "d8b3f1a65c92"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCHEMA = "marketplace"


def upgrade() -> None:
    op.add_column(
        "partner_leads",
        sa.Column("terms_version", sa.String(length=40), nullable=True),
        schema=_SCHEMA,
    )
    op.add_column(
        "partner_leads",
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column("partner_leads", "terms_accepted_at", schema=_SCHEMA)
    op.drop_column("partner_leads", "terms_version", schema=_SCHEMA)
