"""Improvement cases — business problem aggregate (ISOI-002).

Revision ID: 20260819_0019
Revises: 20260817_0018
Create Date: 2026-08-19
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260819_0019"
down_revision = "20260817_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS improvement_cases (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL
                REFERENCES organizations (id) ON DELETE CASCADE,
              problem_statement text NOT NULL,
              impact_statement text NOT NULL,
              related_process text NOT NULL,
              status text NOT NULL DEFAULT 'open'
                CHECK (status IN (
                  'open', 'analyzing', 'acting', 'reviewing', 'closed'
                )),
              created_by uuid NOT NULL REFERENCES users (id),
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS ix_improvement_cases_org_updated
              ON improvement_cases (organization_id, updated_at DESC);

            ALTER TABLE improvement_cases ENABLE ROW LEVEL SECURITY;
            ALTER TABLE improvement_cases FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON improvement_cases;
            CREATE POLICY tenant_isolation ON improvement_cases
              FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE ON improvement_cases TO qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS improvement_cases;"))
