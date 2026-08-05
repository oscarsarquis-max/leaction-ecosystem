"""Guided Assessment Wizard sessions + answers (ISO 9001 pilot)

Revision ID: 20260804_0007
Revises: 20260804_0006
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260804_0007"
down_revision = "20260804_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS guided_sessions (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL REFERENCES organizations (id),
              assessment_id uuid NOT NULL,
              catalog_version text NOT NULL,
              status text NOT NULL DEFAULT 'in_progress'
                CHECK (status IN ('in_progress', 'review', 'completed', 'abandoned')),
              current_step text NOT NULL DEFAULT 'organization',
              current_question_id text,
              context jsonb NOT NULL DEFAULT '{}'::jsonb,
              created_by_user_id uuid,
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_guided_sessions_id_org UNIQUE (id, organization_id),
              CONSTRAINT uq_guided_sessions_assessment UNIQUE (organization_id, assessment_id),
              FOREIGN KEY (assessment_id, organization_id)
                REFERENCES assessments (id, organization_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS ix_guided_sessions_org
              ON guided_sessions (organization_id);

            CREATE TABLE IF NOT EXISTS guided_answers (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL REFERENCES organizations (id),
              session_id uuid NOT NULL,
              question_id text NOT NULL,
              question_version text NOT NULL,
              answer_value text
                CHECK (answer_value IS NULL OR answer_value IN (
                  'yes', 'partial', 'no', 'unknown', 'not_applicable'
                )),
              description text NOT NULL DEFAULT '',
              na_justification text NOT NULL DEFAULT '',
              evidence_mode text NOT NULL DEFAULT 'none'
                CHECK (evidence_mode IN (
                  'none', 'attach', 'link_existing', 'describe', 'provide_later'
                )),
              evidence_ids uuid[] NOT NULL DEFAULT '{}',
              evidence_note text NOT NULL DEFAULT '',
              provide_later boolean NOT NULL DEFAULT false,
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_guided_answers_session_question UNIQUE (session_id, question_id),
              FOREIGN KEY (session_id, organization_id)
                REFERENCES guided_sessions (id, organization_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS ix_guided_answers_session
              ON guided_answers (session_id);

            ALTER TABLE guided_sessions ENABLE ROW LEVEL SECURITY;
            ALTER TABLE guided_sessions FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON guided_sessions;
            CREATE POLICY tenant_isolation ON guided_sessions FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            ALTER TABLE guided_answers ENABLE ROW LEVEL SECURITY;
            ALTER TABLE guided_answers FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON guided_answers;
            CREATE POLICY tenant_isolation ON guided_answers FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE ON guided_sessions TO qmind_app;
            GRANT SELECT, INSERT, UPDATE, DELETE ON guided_answers TO qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            DROP TABLE IF EXISTS guided_answers;
            DROP TABLE IF EXISTS guided_sessions;
            """
        )
    )
