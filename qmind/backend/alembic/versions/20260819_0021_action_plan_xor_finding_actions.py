"""ActionPlan XOR origin + ActionItem finding provenance (ISOI-004).

Revision ID: 20260819_0021
Revises: 20260819_0020
Create Date: 2026-08-19
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260819_0021"
down_revision = "20260819_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            -- Composite uniqueness for same-org FK pattern
            CREATE UNIQUE INDEX IF NOT EXISTS uq_improvement_cases_id_org
              ON improvement_cases (id, organization_id);

            ALTER TABLE action_plans
              ALTER COLUMN assessment_id DROP NOT NULL;

            ALTER TABLE action_plans
              ADD COLUMN IF NOT EXISTS improvement_case_id uuid;

            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_action_plans_improvement_case_same_org'
              ) THEN
                ALTER TABLE action_plans
                  ADD CONSTRAINT fk_action_plans_improvement_case_same_org
                  FOREIGN KEY (improvement_case_id, organization_id)
                  REFERENCES improvement_cases (id, organization_id);
              END IF;
            END $$;

            ALTER TABLE action_plans
              DROP CONSTRAINT IF EXISTS ck_action_plans_origin_xor;
            ALTER TABLE action_plans
              ADD CONSTRAINT ck_action_plans_origin_xor CHECK (
                (assessment_id IS NOT NULL AND improvement_case_id IS NULL)
                OR
                (assessment_id IS NULL AND improvement_case_id IS NOT NULL)
              );

            CREATE UNIQUE INDEX IF NOT EXISTS uq_action_plans_improvement_case
              ON action_plans (organization_id, improvement_case_id)
              WHERE improvement_case_id IS NOT NULL;

            CREATE INDEX IF NOT EXISTS ix_action_plans_improvement_case
              ON action_plans (improvement_case_id)
              WHERE improvement_case_id IS NOT NULL;

            ALTER TABLE action_items
              ADD COLUMN IF NOT EXISTS source_analysis_run_id uuid;

            ALTER TABLE action_items
              ADD COLUMN IF NOT EXISTS source_finding_code text;

            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_action_items_source_analysis_run'
              ) THEN
                ALTER TABLE action_items
                  ADD CONSTRAINT fk_action_items_source_analysis_run
                  FOREIGN KEY (source_analysis_run_id)
                  REFERENCES improvement_case_analysis_runs (id);
              END IF;
            END $$;

            ALTER TABLE action_items
              DROP CONSTRAINT IF EXISTS ck_action_items_source_finding_pair;
            ALTER TABLE action_items
              ADD CONSTRAINT ck_action_items_source_finding_pair CHECK (
                (source_analysis_run_id IS NULL AND source_finding_code IS NULL)
                OR
                (source_analysis_run_id IS NOT NULL AND source_finding_code IS NOT NULL)
              );

            CREATE UNIQUE INDEX IF NOT EXISTS uq_action_items_source_run_finding
              ON action_items (organization_id, source_analysis_run_id, source_finding_code)
              WHERE source_analysis_run_id IS NOT NULL
                AND source_finding_code IS NOT NULL;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            DROP INDEX IF EXISTS uq_action_items_source_run_finding;
            ALTER TABLE action_items
              DROP CONSTRAINT IF EXISTS ck_action_items_source_finding_pair;
            ALTER TABLE action_items
              DROP CONSTRAINT IF EXISTS fk_action_items_source_analysis_run;
            ALTER TABLE action_items DROP COLUMN IF EXISTS source_finding_code;
            ALTER TABLE action_items DROP COLUMN IF EXISTS source_analysis_run_id;

            DROP INDEX IF EXISTS ix_action_plans_improvement_case;
            DROP INDEX IF EXISTS uq_action_plans_improvement_case;
            ALTER TABLE action_plans
              DROP CONSTRAINT IF EXISTS ck_action_plans_origin_xor;
            ALTER TABLE action_plans
              DROP CONSTRAINT IF EXISTS fk_action_plans_improvement_case_same_org;
            ALTER TABLE action_plans DROP COLUMN IF EXISTS improvement_case_id;

            -- Restore NOT NULL only if no case-origin rows remain
            UPDATE action_plans SET assessment_id = assessment_id
              WHERE assessment_id IS NOT NULL;
            ALTER TABLE action_plans
              ALTER COLUMN assessment_id SET NOT NULL;

            DROP INDEX IF EXISTS uq_improvement_cases_id_org;
            """
        )
    )
