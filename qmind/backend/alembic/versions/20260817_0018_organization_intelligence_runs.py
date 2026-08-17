"""Organization intelligence runs — persist OI envelopes (org-scoped).

Revision ID: 20260817_0018
Revises: 20260817_0017
Create Date: 2026-08-17
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260817_0018"
down_revision = "20260817_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS organization_intelligence_runs (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL
                REFERENCES organizations (id) ON DELETE CASCADE,
              schema_version text NOT NULL,
              request_id text NOT NULL,
              correlation_id text NOT NULL,
              generated_at timestamptz NOT NULL,
              insights jsonb NOT NULL,
              created_at timestamptz NOT NULL DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS ix_organization_intelligence_runs_org_created
              ON organization_intelligence_runs (organization_id, created_at DESC);

            ALTER TABLE organization_intelligence_runs ENABLE ROW LEVEL SECURITY;
            ALTER TABLE organization_intelligence_runs FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON organization_intelligence_runs;
            CREATE POLICY tenant_isolation ON organization_intelligence_runs
              FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE ON organization_intelligence_runs TO qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            DROP TABLE IF EXISTS organization_intelligence_runs;
            """
        )
    )
