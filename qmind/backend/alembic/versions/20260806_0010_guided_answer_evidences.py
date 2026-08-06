"""Typed guided_answer ↔ evidence links + backfill from evidence_ids

Revision ID: 20260806_0010
Revises: 20260805_0009
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260806_0010"
down_revision = "20260805_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            -- Composite uniqueness for same-org FKs from junction table
            ALTER TABLE guided_answers
              DROP CONSTRAINT IF EXISTS uq_guided_answers_id_org;
            ALTER TABLE guided_answers
              ADD CONSTRAINT uq_guided_answers_id_org UNIQUE (id, organization_id);

            -- Provenance for Wizard answers. Future Findings may reference these
            -- links after human review; this table does not auto-create findings.
            CREATE TABLE IF NOT EXISTS guided_answer_evidences (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL REFERENCES organizations (id),
              guided_session_id uuid NOT NULL,
              guided_answer_id uuid NOT NULL,
              assessment_id uuid NOT NULL,
              question_id text NOT NULL,
              question_version text NOT NULL,
              evidence_id uuid NOT NULL,
              link_type text NOT NULL DEFAULT 'link_existing'
                CHECK (link_type IN ('attach', 'link_existing')),
              created_by_user_id uuid,
              created_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_guided_answer_evidences_id_org UNIQUE (id, organization_id),
              CONSTRAINT uq_guided_answer_evidences_answer_evidence
                UNIQUE (guided_answer_id, evidence_id),
              CONSTRAINT fk_gae_session_same_org
                FOREIGN KEY (guided_session_id, organization_id)
                REFERENCES guided_sessions (id, organization_id) ON DELETE CASCADE,
              CONSTRAINT fk_gae_answer_same_org
                FOREIGN KEY (guided_answer_id, organization_id)
                REFERENCES guided_answers (id, organization_id) ON DELETE CASCADE,
              CONSTRAINT fk_gae_assessment_same_org
                FOREIGN KEY (assessment_id, organization_id)
                REFERENCES assessments (id, organization_id) ON DELETE CASCADE,
              CONSTRAINT fk_gae_evidence_same_org
                FOREIGN KEY (evidence_id, organization_id)
                REFERENCES evidences (id, organization_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS ix_gae_org_session
              ON guided_answer_evidences (organization_id, guided_session_id);
            CREATE INDEX IF NOT EXISTS ix_gae_org_answer
              ON guided_answer_evidences (organization_id, guided_answer_id);
            CREATE INDEX IF NOT EXISTS ix_gae_org_assessment
              ON guided_answer_evidences (organization_id, assessment_id);
            CREATE INDEX IF NOT EXISTS ix_gae_org_evidence
              ON guided_answer_evidences (organization_id, evidence_id);

            ALTER TABLE guided_answer_evidences ENABLE ROW LEVEL SECURITY;
            ALTER TABLE guided_answer_evidences FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON guided_answer_evidences;
            CREATE POLICY tenant_isolation ON guided_answer_evidences FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE ON guided_answer_evidences TO qmind_app;
            """
        )
    )

    # Backfill: only same org + same assessment; skip invalid refs.
    # Runs as migration role (bypasses RLS). Counts logged without PII.
    conn = op.get_bind()
    result = conn.execute(
        text(
            """
            WITH expanded AS (
              SELECT
                ga.id AS guided_answer_id,
                ga.organization_id,
                ga.session_id AS guided_session_id,
                ga.question_id,
                ga.question_version,
                gs.assessment_id,
                eid AS evidence_id
              FROM guided_answers ga
              JOIN guided_sessions gs
                ON gs.id = ga.session_id
               AND gs.organization_id = ga.organization_id
              CROSS JOIN LATERAL unnest(ga.evidence_ids) AS eid
              WHERE cardinality(ga.evidence_ids) > 0
            ),
            valid AS (
              SELECT e.*
              FROM expanded e
              JOIN evidences ev
                ON ev.id = e.evidence_id
               AND ev.organization_id = e.organization_id
               AND ev.assessment_id = e.assessment_id
            ),
            inserted AS (
              INSERT INTO guided_answer_evidences (
                organization_id, guided_session_id, guided_answer_id,
                assessment_id, question_id, question_version,
                evidence_id, link_type, created_by_user_id
              )
              SELECT
                v.organization_id,
                v.guided_session_id,
                v.guided_answer_id,
                v.assessment_id,
                v.question_id,
                v.question_version,
                v.evidence_id,
                'link_existing',
                NULL
              FROM valid v
              ON CONFLICT (guided_answer_id, evidence_id) DO NOTHING
              RETURNING 1
            )
            SELECT
              (SELECT count(*) FROM expanded) AS candidates,
              (SELECT count(*) FROM valid) AS valid_rows,
              (SELECT count(*) FROM inserted) AS inserted_rows,
              (SELECT count(*) FROM expanded) - (SELECT count(*) FROM valid) AS skipped_invalid
            """
        )
    ).one()
    print(
        "guided_answer_evidences backfill: "
        f"candidates={result.candidates} valid={result.valid_rows} "
        f"inserted={result.inserted_rows} skipped_invalid={result.skipped_invalid}"
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            DROP TABLE IF EXISTS guided_answer_evidences;
            ALTER TABLE guided_answers
              DROP CONSTRAINT IF EXISTS uq_guided_answers_id_org;
            """
        )
    )
