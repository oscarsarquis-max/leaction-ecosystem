"""Maturity catalog immutability + one current approved package

Revision ID: 20260803_0004
Revises: 20260803_0003
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260803_0004"
down_revision = "20260803_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            -- Catalog is global seed; app role may only read while in use
            REVOKE INSERT, UPDATE, DELETE ON TABLE maturity_models FROM qmind_app;
            REVOKE INSERT, UPDATE, DELETE ON TABLE maturity_dimensions FROM qmind_app;
            REVOKE INSERT, UPDATE, DELETE ON TABLE maturity_criteria FROM qmind_app;
            GRANT SELECT ON TABLE maturity_models TO qmind_app;
            GRANT SELECT ON TABLE maturity_dimensions TO qmind_app;
            GRANT SELECT ON TABLE maturity_criteria TO qmind_app;

            -- At most one approved (current) maturity package per assessment
            CREATE UNIQUE INDEX IF NOT EXISTS uq_maturity_one_approved_per_assessment
              ON maturity_assessments (assessment_id)
              WHERE status = 'approved';

            -- Freeze maturity_model_id after Assessment leaves draft
            CREATE OR REPLACE FUNCTION qmind_app.prevent_maturity_model_unfreeze()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
              IF TG_OP = 'UPDATE'
                 AND NEW.maturity_model_id IS DISTINCT FROM OLD.maturity_model_id
                 AND OLD.status <> 'draft' THEN
                RAISE EXCEPTION 'maturity_model_id is frozen after plan'
                  USING ERRCODE = 'check_violation';
              END IF;
              RETURN NEW;
            END;
            $$;

            DROP TRIGGER IF EXISTS trg_assessments_freeze_maturity_model ON assessments;
            CREATE TRIGGER trg_assessments_freeze_maturity_model
              BEFORE UPDATE ON assessments
              FOR EACH ROW
              EXECUTE FUNCTION qmind_app.prevent_maturity_model_unfreeze();

            -- Formal report waiver for Assessment.close without published report
            ALTER TABLE assessments
              ADD COLUMN IF NOT EXISTS close_waiver_reason text;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            ALTER TABLE assessments DROP COLUMN IF EXISTS close_waiver_reason;

            DROP TRIGGER IF EXISTS trg_assessments_freeze_maturity_model ON assessments;
            DROP FUNCTION IF EXISTS qmind_app.prevent_maturity_model_unfreeze();

            DROP INDEX IF EXISTS uq_maturity_one_approved_per_assessment;

            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE maturity_models TO qmind_app;
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE maturity_dimensions TO qmind_app;
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE maturity_criteria TO qmind_app;
            """
        )
    )
