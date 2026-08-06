"""Audit plan schedule — extend interviews + agenda plan_activity_kind

Revision ID: 20260806_0013
Revises: 20260806_0012
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260806_0013"
down_revision = "20260806_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            -- Interview scheduling fields (Interview remains SoT for interviews)
            ALTER TABLE interviews
              ADD COLUMN IF NOT EXISTS title text NOT NULL DEFAULT '',
              ADD COLUMN IF NOT EXISTS objective text NOT NULL DEFAULT '',
              ADD COLUMN IF NOT EXISTS process_name text NOT NULL DEFAULT '',
              ADD COLUMN IF NOT EXISTS org_contact_name text NOT NULL DEFAULT '',
              ADD COLUMN IF NOT EXISTS interviewer_membership_id uuid,
              ADD COLUMN IF NOT EXISTS participant_membership_ids uuid[] NOT NULL DEFAULT '{}',
              ADD COLUMN IF NOT EXISTS scheduled_at timestamptz,
              ADD COLUMN IF NOT EXISTS duration_minutes int,
              ADD COLUMN IF NOT EXISTS location text NOT NULL DEFAULT '',
              ADD COLUMN IF NOT EXISTS remote_link text NOT NULL DEFAULT '',
              ADD COLUMN IF NOT EXISTS preparation text NOT NULL DEFAULT '',
              ADD COLUMN IF NOT EXISTS outside_period_justification text NOT NULL DEFAULT '';

            ALTER TABLE interviews DROP CONSTRAINT IF EXISTS interviews_status_check;
            ALTER TABLE interviews
              ADD CONSTRAINT interviews_status_check
              CHECK (status IN (
                'planned', 'confirmed', 'in_progress', 'completed', 'cancelled'
              ));

            ALTER TABLE interviews DROP CONSTRAINT IF EXISTS ck_interviews_duration;
            ALTER TABLE interviews
              ADD CONSTRAINT ck_interviews_duration
              CHECK (duration_minutes IS NULL OR duration_minutes > 0);

            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_interviews_interviewer_same_org'
              ) THEN
                ALTER TABLE interviews
                  ADD CONSTRAINT fk_interviews_interviewer_same_org
                  FOREIGN KEY (interviewer_membership_id, organization_id)
                  REFERENCES memberships (id, organization_id);
              END IF;
            END $$;

            CREATE INDEX IF NOT EXISTS ix_interviews_org_scheduled
              ON interviews (organization_id, scheduled_at)
              WHERE scheduled_at IS NOT NULL;

            -- Agenda: classify plan meetings/milestones (AgendaEvent SoT)
            ALTER TABLE agenda_events
              ADD COLUMN IF NOT EXISTS plan_activity_kind text;

            ALTER TABLE agenda_events DROP CONSTRAINT IF EXISTS ck_agenda_plan_activity_kind;
            ALTER TABLE agenda_events
              ADD CONSTRAINT ck_agenda_plan_activity_kind
              CHECK (
                plan_activity_kind IS NULL
                OR plan_activity_kind IN (
                  'opening_meeting',
                  'closing_meeting',
                  'additional_meeting',
                  'milestone_preparation_done',
                  'milestone_plan_approved',
                  'milestone_field_start',
                  'milestone_field_done',
                  'milestone_analysis_done',
                  'milestone_report_due',
                  'milestone_closure_due',
                  'milestone_custom'
                )
              );

            -- At most one opening / closing meeting per assessment (active)
            CREATE UNIQUE INDEX IF NOT EXISTS uq_agenda_opening_meeting_per_assessment
              ON agenda_events (organization_id, assessment_id)
              WHERE plan_activity_kind = 'opening_meeting'
                AND status <> 'cancelled'
                AND assessment_id IS NOT NULL;

            CREATE UNIQUE INDEX IF NOT EXISTS uq_agenda_closing_meeting_per_assessment
              ON agenda_events (organization_id, assessment_id)
              WHERE plan_activity_kind = 'closing_meeting'
                AND status <> 'cancelled'
                AND assessment_id IS NOT NULL;

            CREATE INDEX IF NOT EXISTS ix_agenda_events_assessment_plan_kind
              ON agenda_events (organization_id, assessment_id, plan_activity_kind)
              WHERE assessment_id IS NOT NULL;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            DROP INDEX IF EXISTS ix_agenda_events_assessment_plan_kind;
            DROP INDEX IF EXISTS uq_agenda_closing_meeting_per_assessment;
            DROP INDEX IF EXISTS uq_agenda_opening_meeting_per_assessment;
            ALTER TABLE agenda_events DROP CONSTRAINT IF EXISTS ck_agenda_plan_activity_kind;
            ALTER TABLE agenda_events DROP COLUMN IF EXISTS plan_activity_kind;

            DROP INDEX IF EXISTS ix_interviews_org_scheduled;
            ALTER TABLE interviews DROP CONSTRAINT IF EXISTS fk_interviews_interviewer_same_org;
            ALTER TABLE interviews DROP CONSTRAINT IF EXISTS ck_interviews_duration;
            ALTER TABLE interviews DROP CONSTRAINT IF EXISTS interviews_status_check;
            ALTER TABLE interviews
              ADD CONSTRAINT interviews_status_check
              CHECK (status IN ('planned', 'completed', 'cancelled'));

            ALTER TABLE interviews
              DROP COLUMN IF EXISTS title,
              DROP COLUMN IF EXISTS objective,
              DROP COLUMN IF EXISTS process_name,
              DROP COLUMN IF EXISTS org_contact_name,
              DROP COLUMN IF EXISTS interviewer_membership_id,
              DROP COLUMN IF EXISTS participant_membership_ids,
              DROP COLUMN IF EXISTS scheduled_at,
              DROP COLUMN IF EXISTS duration_minutes,
              DROP COLUMN IF EXISTS location,
              DROP COLUMN IF EXISTS remote_link,
              DROP COLUMN IF EXISTS preparation,
              DROP COLUMN IF EXISTS outside_period_justification;
            """
        )
    )
