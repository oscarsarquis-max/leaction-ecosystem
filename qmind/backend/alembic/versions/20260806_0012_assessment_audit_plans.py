"""Assessment audit plan (1:1 operational plan document)

Revision ID: 20260806_0012
Revises: 20260806_0011
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260806_0012"
down_revision = "20260806_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS assessment_audit_plans (
              id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
              organization_id uuid NOT NULL REFERENCES organizations (id),
              assessment_id uuid NOT NULL,
              objective text NOT NULL DEFAULT '',
              modality text NOT NULL DEFAULT 'diagnosis'
                CHECK (modality IN (
                  'diagnosis', 'internal_audit', 'external_audit',
                  'certification_prep', 'other'
                )),
              scope_text text NOT NULL DEFAULT '',
              criteria jsonb NOT NULL DEFAULT '{
                "iso9001_2015": true,
                "internal_processes": true,
                "legal_contractual": false,
                "legal_contractual_text": "",
                "additional_text": ""
              }'::jsonb,
              sites jsonb NOT NULL DEFAULT '[]'::jsonb,
              processes jsonb NOT NULL DEFAULT '[]'::jsonb,
              lead_membership_id uuid,
              team_membership_ids uuid[] NOT NULL DEFAULT '{}',
              org_representatives jsonb NOT NULL DEFAULT '[]'::jsonb,
              planned_start date,
              planned_end date,
              preparation_notes text NOT NULL DEFAULT '',
              risks_notes text NOT NULL DEFAULT '',
              plan_status text NOT NULL DEFAULT 'draft'
                CHECK (plan_status IN ('draft', 'ready', 'amended')),
              field_sources jsonb NOT NULL DEFAULT '{}'::jsonb,
              last_amendment_reason text NOT NULL DEFAULT '',
              updated_by_user_id uuid,
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now(),
              CONSTRAINT uq_assessment_audit_plans_id_org UNIQUE (id, organization_id),
              CONSTRAINT uq_assessment_audit_plans_assessment_org
                UNIQUE (assessment_id, organization_id),
              CONSTRAINT fk_aap_assessment_same_org
                FOREIGN KEY (assessment_id, organization_id)
                REFERENCES assessments (id, organization_id) ON DELETE CASCADE,
              CONSTRAINT fk_aap_lead_same_org
                FOREIGN KEY (lead_membership_id, organization_id)
                REFERENCES memberships (id, organization_id),
              CONSTRAINT ck_aap_dates CHECK (
                planned_start IS NULL OR planned_end IS NULL
                OR planned_end >= planned_start
              )
            );

            CREATE INDEX IF NOT EXISTS ix_aap_org_status
              ON assessment_audit_plans (organization_id, plan_status);

            ALTER TABLE assessment_audit_plans ENABLE ROW LEVEL SECURITY;
            ALTER TABLE assessment_audit_plans FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON assessment_audit_plans;
            CREATE POLICY tenant_isolation ON assessment_audit_plans FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE ON assessment_audit_plans TO qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS assessment_audit_plans;"))
