"""Evolution suggestion packages — deterministic advisory map (no generative AI).

Revision ID: 20260807_0015
Revises: 20260807_0014
Create Date: 2026-08-07
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260807_0015"
down_revision = "20260807_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS evolution_suggestion_packages (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL,
              assessment_id uuid NOT NULL,
              package_version int NOT NULL,
              generation_mode text NOT NULL
                CHECK (generation_mode IN ('preliminary', 'analysis_ready')),
              status text NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'superseded')),
              supersedes_id uuid,
              source_fingerprint text NOT NULL,
              source_snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
              catalog_version text NOT NULL,
              generated_by uuid NOT NULL,
              generated_at timestamptz NOT NULL DEFAULT now(),
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_evolution_packages_id_org UNIQUE (id, organization_id),
              CONSTRAINT uq_evolution_packages_version
                UNIQUE (organization_id, assessment_id, package_version),
              CONSTRAINT fk_evolution_packages_assessment_same_org
                FOREIGN KEY (assessment_id, organization_id)
                REFERENCES assessments (id, organization_id),
              CONSTRAINT fk_evolution_packages_author_same_org
                FOREIGN KEY (generated_by, organization_id)
                REFERENCES memberships (id, organization_id),
              CONSTRAINT fk_evolution_packages_supersedes_same_org
                FOREIGN KEY (supersedes_id, organization_id)
                REFERENCES evolution_suggestion_packages (id, organization_id)
            );

            CREATE UNIQUE INDEX IF NOT EXISTS uq_evolution_packages_active
              ON evolution_suggestion_packages (organization_id, assessment_id)
              WHERE status = 'active';

            CREATE INDEX IF NOT EXISTS ix_evolution_packages_org_assessment
              ON evolution_suggestion_packages (organization_id, assessment_id, package_version DESC);

            CREATE TABLE IF NOT EXISTS evolution_suggestions (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL,
              assessment_id uuid NOT NULL,
              package_id uuid NOT NULL,
              package_version int NOT NULL,
              rule_id text NOT NULL,
              rule_version text NOT NULL,
              category text NOT NULL
                CHECK (category IN (
                  'direction_governance',
                  'planning_risks',
                  'people_resources',
                  'operations_customers',
                  'measurement_decisions',
                  'correction_improvement'
                )),
              title text NOT NULL,
              observation text NOT NULL,
              business_rationale text NOT NULL,
              suggested_evolution text NOT NULL,
              expected_benefit text NOT NULL,
              first_step text NOT NULL,
              impact text NOT NULL
                CHECK (impact IN ('high', 'medium', 'low')),
              effort text NOT NULL
                CHECK (effort IN ('high', 'medium', 'low')),
              priority text NOT NULL
                CHECK (priority IN ('now', 'next_cycle', 'future', 'investigate')),
              confidence text NOT NULL
                CHECK (confidence IN ('high', 'medium', 'low')),
              is_priority boolean NOT NULL DEFAULT false,
              source_references jsonb NOT NULL DEFAULT '[]'::jsonb,
              status text NOT NULL DEFAULT 'proposed'
                CHECK (status IN (
                  'proposed',
                  'accepted',
                  'dismissed',
                  'converted_to_action',
                  'superseded'
                )),
              dismiss_reason text,
              generated_at timestamptz NOT NULL DEFAULT now(),
              generated_by uuid NOT NULL,
              reviewed_at timestamptz,
              reviewed_by uuid,
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_evolution_suggestions_id_org UNIQUE (id, organization_id),
              CONSTRAINT fk_evolution_suggestions_package_same_org
                FOREIGN KEY (package_id, organization_id)
                REFERENCES evolution_suggestion_packages (id, organization_id),
              CONSTRAINT fk_evolution_suggestions_assessment_same_org
                FOREIGN KEY (assessment_id, organization_id)
                REFERENCES assessments (id, organization_id),
              CONSTRAINT fk_evolution_suggestions_author_same_org
                FOREIGN KEY (generated_by, organization_id)
                REFERENCES memberships (id, organization_id),
              CONSTRAINT fk_evolution_suggestions_reviewer_same_org
                FOREIGN KEY (reviewed_by, organization_id)
                REFERENCES memberships (id, organization_id),
              CONSTRAINT ck_evolution_dismiss_reason
                CHECK (
                  (status <> 'dismissed')
                  OR (dismiss_reason IS NOT NULL AND length(trim(dismiss_reason)) > 0)
                )
            );

            CREATE INDEX IF NOT EXISTS ix_evolution_suggestions_package
              ON evolution_suggestions (organization_id, package_id, is_priority DESC, priority);

            CREATE INDEX IF NOT EXISTS ix_evolution_suggestions_assessment
              ON evolution_suggestions (organization_id, assessment_id, status);

            ALTER TABLE evolution_suggestion_packages ENABLE ROW LEVEL SECURITY;
            ALTER TABLE evolution_suggestion_packages FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON evolution_suggestion_packages;
            CREATE POLICY tenant_isolation ON evolution_suggestion_packages
              FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            ALTER TABLE evolution_suggestions ENABLE ROW LEVEL SECURITY;
            ALTER TABLE evolution_suggestions FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON evolution_suggestions;
            CREATE POLICY tenant_isolation ON evolution_suggestions
              FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE ON evolution_suggestion_packages TO qmind_app;
            GRANT SELECT, INSERT, UPDATE, DELETE ON evolution_suggestions TO qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            DROP TABLE IF EXISTS evolution_suggestions;
            DROP TABLE IF EXISTS evolution_suggestion_packages;
            """
        )
    )
