"""BLOG-025: índice único de actor_ref para carimbo idempotente LePain.

Revision ID: a8c1d9e24f70
Revises: f7c2e9a14b60
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a8c1d9e24f70"
down_revision: Union[str, Sequence[str], None] = "f7c2e9a14b60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotência só para créditos LePain (admin/outros actor_ref podem repetir).
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_house_fidelity_events_lepain_actor_ref
        ON house_fidelity_events (actor_ref)
        WHERE actor_ref LIKE 'lepain-%'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_house_fidelity_events_lepain_actor_ref")
