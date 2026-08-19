"""Improvement case analysis runs — ProblemAnalysis history (ISOI-003).

Revision ID: 20260819_0020
Revises: 20260819_0019
Create Date: 2026-08-19
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260819_0020"
down_revision = "20260819_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS improvement_case_analysis_runs (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL
                REFERENCES organizations (id) ON DELETE CASCADE,
              improvement_case_id uuid NOT NULL
                REFERENCES improvement_cases (id) ON DELETE CASCADE,
              schema_version text NOT NULL,
              request_id text NOT NULL,
              correlation_id text NOT NULL,
              generated_at timestamptz NOT NULL,
              input_fingerprint text NOT NULL,
              analysis jsonb NOT NULL,
              created_at timestamptz NOT NULL DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS ix_ic_analysis_runs_case_created
              ON improvement_case_analysis_runs (improvement_case_id, created_at DESC);

            CREATE INDEX IF NOT EXISTS ix_ic_analysis_runs_org_created
              ON improvement_case_analysis_runs (organization_id, created_at DESC);

            ALTER TABLE improvement_case_analysis_runs ENABLE ROW LEVEL SECURITY;
            ALTER TABLE improvement_case_analysis_runs FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON improvement_case_analysis_runs;
            CREATE POLICY tenant_isolation ON improvement_case_analysis_runs
              FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE ON improvement_case_analysis_runs TO qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS improvement_case_analysis_runs;"))
