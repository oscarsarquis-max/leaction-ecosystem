"""Organization Profile — persistent org-scoped master data (1:1).

Revision ID: 20260817_0017
Revises: 20260807_0016
Create Date: 2026-08-17
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "20260817_0017"
down_revision = "20260807_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS organization_profiles (
              organization_id uuid PRIMARY KEY
                REFERENCES organizations (id) ON DELETE CASCADE,
              trade_name text NOT NULL DEFAULT '',
              legal_name text NOT NULL DEFAULT '',
              summary text NOT NULL DEFAULT '',
              industry text NOT NULL DEFAULT '',
              business_model text NOT NULL DEFAULT ''
                CHECK (business_model IN (
                  '',
                  'b2b',
                  'b2c',
                  'b2b2c',
                  'services',
                  'manufacturing',
                  'mixed',
                  'other'
                )),
              employee_range text NOT NULL DEFAULT ''
                CHECK (employee_range IN (
                  '',
                  '1-10',
                  '11-50',
                  '51-200',
                  '201-500',
                  '501-1000',
                  '1000+'
                )),
              unit_count integer
                CHECK (unit_count IS NULL OR unit_count >= 0),
              certification_status text NOT NULL DEFAULT 'unknown'
                CHECK (certification_status IN (
                  'unknown',
                  'none',
                  'in_progress',
                  'certified',
                  'expired',
                  'not_applicable'
                )),
              quality_structure text NOT NULL DEFAULT 'unknown'
                CHECK (quality_structure IN (
                  'unknown',
                  'none',
                  'informal',
                  'formal_partial',
                  'formal'
                )),
              created_at timestamptz NOT NULL DEFAULT now(),
              updated_at timestamptz NOT NULL DEFAULT now()
            );

            CREATE INDEX IF NOT EXISTS ix_organization_profiles_updated
              ON organization_profiles (updated_at DESC);

            ALTER TABLE organization_profiles ENABLE ROW LEVEL SECURITY;
            ALTER TABLE organization_profiles FORCE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS tenant_isolation ON organization_profiles;
            CREATE POLICY tenant_isolation ON organization_profiles
              FOR ALL TO qmind_app
              USING (organization_id = qmind_app.current_organization_id())
              WITH CHECK (organization_id = qmind_app.current_organization_id());

            GRANT SELECT, INSERT, UPDATE, DELETE ON organization_profiles TO qmind_app;
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            """
            DROP TABLE IF EXISTS organization_profiles;
            """
        )
    )
