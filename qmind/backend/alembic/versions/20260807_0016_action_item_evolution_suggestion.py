"""Link ActionItem to EvolutionSuggestion (typed origin).

Revision ID: 20260807_0016
Revises: 20260807_0015
Create Date: 2026-08-07
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260807_0016"
down_revision = "20260807_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE action_items
              ADD COLUMN IF NOT EXISTS source_evolution_suggestion_id uuid;

            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_action_items_evolution_suggestion_same_org'
              ) THEN
                ALTER TABLE action_items
                  ADD CONSTRAINT fk_action_items_evolution_suggestion_same_org
                  FOREIGN KEY (source_evolution_suggestion_id, organization_id)
                  REFERENCES evolution_suggestions (id, organization_id);
              END IF;
            END $$;

            CREATE UNIQUE INDEX IF NOT EXISTS uq_action_items_source_evolution_suggestion
              ON action_items (organization_id, source_evolution_suggestion_id)
              WHERE source_evolution_suggestion_id IS NOT NULL;

            CREATE INDEX IF NOT EXISTS ix_action_items_org_evolution_suggestion
              ON action_items (organization_id, source_evolution_suggestion_id)
              WHERE source_evolution_suggestion_id IS NOT NULL;

            ALTER TABLE evolution_suggestions
              ADD COLUMN IF NOT EXISTS investigate_note text;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE evolution_suggestions
              DROP COLUMN IF EXISTS investigate_note;
            DROP INDEX IF EXISTS ix_action_items_org_evolution_suggestion;
            DROP INDEX IF EXISTS uq_action_items_source_evolution_suggestion;
            ALTER TABLE action_items
              DROP CONSTRAINT IF EXISTS fk_action_items_evolution_suggestion_same_org;
            ALTER TABLE action_items
              DROP COLUMN IF EXISTS source_evolution_suggestion_id;
            """
        )
    )
