"""Execution Intelligence immutable history (ISOI-009).

Revision ID: 20260826_0025
Revises: 20260824_0024
Create Date: 2026-08-26
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260826_0025"
down_revision = "20260824_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS improvement_case_execution_intelligence_runs (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL REFERENCES organizations (id),
              improvement_case_id uuid NOT NULL,
              schema_version text NOT NULL,
              mechanism_version text NOT NULL,
              request_id text NOT NULL,
              correlation_id text NOT NULL,
              generated_at timestamptz NOT NULL,
              input_snapshot jsonb NOT NULL,
              input_fingerprint text NOT NULL,
              result jsonb NOT NULL,
              idempotency_scope text,
              idempotency_key_hash text,
              request_fingerprint text,
              created_by uuid NOT NULL REFERENCES users (id),
              created_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT fk_ic_ei_case_same_org
                FOREIGN KEY (improvement_case_id, organization_id)
                REFERENCES improvement_cases (id, organization_id),
              CONSTRAINT ck_ic_ei_idempotency_pair CHECK (
                (
                  idempotency_scope IS NULL
                  AND idempotency_key_hash IS NULL
                  AND request_fingerprint IS NULL
                )
                OR (
                  idempotency_scope IS NOT NULL
                  AND idempotency_key_hash IS NOT NULL
                  AND request_fingerprint IS NOT NULL
                )
              )
            );
            CREATE INDEX IF NOT EXISTS ix_ic_ei_runs_case_created
              ON improvement_case_execution_intelligence_runs
                (improvement_case_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS ix_ic_ei_runs_org_created
              ON improvement_case_execution_intelligence_runs
                (organization_id, created_at DESC);
            CREATE UNIQUE INDEX IF NOT EXISTS uq_ic_ei_runs_idempotency
              ON improvement_case_execution_intelligence_runs
                (organization_id, idempotency_scope, idempotency_key_hash)
              WHERE idempotency_key_hash IS NOT NULL;

            ALTER TABLE improvement_case_execution_intelligence_runs
              ENABLE ROW LEVEL SECURITY;
            ALTER TABLE improvement_case_execution_intelligence_runs
              FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation
              ON improvement_case_execution_intelligence_runs;
            CREATE POLICY tenant_isolation
              ON improvement_case_execution_intelligence_runs
              FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT
              ON improvement_case_execution_intelligence_runs TO qmind_app;
            REVOKE UPDATE, DELETE
              ON improvement_case_execution_intelligence_runs FROM qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            DO $$
            DECLARE n bigint := 0;
            BEGIN
              SELECT count(*) INTO n
                FROM improvement_case_execution_intelligence_runs;
              IF n > 0 THEN
                RAISE EXCEPTION
                  'ISOI-009 downgrade refused: % execution intelligence runs '
                  'would be destroyed. Downgrade is supported only when history is empty.',
                  n;
              END IF;
            END $$;
            DROP TABLE IF EXISTS improvement_case_execution_intelligence_runs;
            """
        )
    )
