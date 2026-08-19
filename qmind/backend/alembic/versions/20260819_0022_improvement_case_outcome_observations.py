"""Improvement case outcome observations (ISOI-005).

Revision ID: 20260819_0022
Revises: 20260819_0021
Create Date: 2026-08-19
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260819_0022"
down_revision = "20260819_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS improvement_case_outcome_observations (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL
                REFERENCES organizations (id) ON DELETE CASCADE,
              improvement_case_id uuid NOT NULL,
              result_direction text NOT NULL
                CHECK (result_direction IN (
                  'improved', 'unchanged', 'worsened', 'not_yet_measured'
                )),
              observation_statement text NOT NULL,
              measurement_basis text NOT NULL,
              observed_at timestamptz NOT NULL,
              created_by uuid NOT NULL REFERENCES users (id),
              created_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT fk_outcome_obs_case_same_org
                FOREIGN KEY (improvement_case_id, organization_id)
                REFERENCES improvement_cases (id, organization_id)
                ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS ix_outcome_obs_case_observed
              ON improvement_case_outcome_observations (
                improvement_case_id, observed_at DESC
              );

            ALTER TABLE improvement_case_outcome_observations
              ENABLE ROW LEVEL SECURITY;
            ALTER TABLE improvement_case_outcome_observations
              FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation
              ON improvement_case_outcome_observations;
            CREATE POLICY tenant_isolation ON improvement_case_outcome_observations
              FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE
              ON improvement_case_outcome_observations TO qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS improvement_case_outcome_observations;"))
