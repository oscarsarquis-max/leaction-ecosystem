"""Organization agenda events (manual + auto-projected)

Revision ID: 20260805_0009
Revises: 20260805_0008
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260805_0009"
down_revision = "20260805_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS agenda_events (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL REFERENCES organizations (id),
              assessment_id uuid,
              title text NOT NULL,
              description text NOT NULL DEFAULT '',
              event_type text NOT NULL
                CHECK (event_type IN (
                  'interview', 'meeting', 'visit', 'reminder',
                  'milestone', 'deadline', 'other'
                )),
              starts_at timestamptz NOT NULL,
              ends_at timestamptz,
              timezone text NOT NULL DEFAULT 'America/Sao_Paulo',
              owner_membership_id uuid,
              participant_membership_ids uuid[] NOT NULL DEFAULT '{}',
              location_or_link text NOT NULL DEFAULT '',
              status text NOT NULL DEFAULT 'scheduled'
                CHECK (status IN ('scheduled', 'completed', 'cancelled')),
              guidance text NOT NULL DEFAULT '',
              related_action text NOT NULL DEFAULT '',
              source_kind text,
              source_id uuid,
              is_auto boolean NOT NULL DEFAULT false,
              created_by_user_id uuid,
              updated_by_user_id uuid,
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_agenda_events_id_org UNIQUE (id, organization_id),
              CONSTRAINT fk_agenda_events_assessment_same_org
                FOREIGN KEY (assessment_id, organization_id)
                REFERENCES assessments (id, organization_id) ON DELETE CASCADE,
              CONSTRAINT fk_agenda_events_owner_same_org
                FOREIGN KEY (owner_membership_id, organization_id)
                REFERENCES memberships (id, organization_id),
              CONSTRAINT ck_agenda_events_auto_source CHECK (
                (is_auto = false AND source_kind IS NULL AND source_id IS NULL)
                OR (is_auto = true AND source_kind IS NOT NULL AND source_id IS NOT NULL)
              )
            );

            CREATE UNIQUE INDEX IF NOT EXISTS uq_agenda_events_auto_source
              ON agenda_events (organization_id, source_kind, source_id)
              WHERE is_auto = true AND source_kind IS NOT NULL AND source_id IS NOT NULL;

            CREATE INDEX IF NOT EXISTS ix_agenda_events_org_starts
              ON agenda_events (organization_id, starts_at);

            CREATE INDEX IF NOT EXISTS ix_agenda_events_org_status
              ON agenda_events (organization_id, status, starts_at);

            ALTER TABLE agenda_events ENABLE ROW LEVEL SECURITY;
            ALTER TABLE agenda_events FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON agenda_events;
            CREATE POLICY tenant_isolation ON agenda_events FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE ON agenda_events TO qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS agenda_events;"))
