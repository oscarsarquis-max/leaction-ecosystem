"""Initial schema — domain-docs-v0 freeze

Revision ID: 20260803_0001
Revises:
Create Date: 2026-08-03

Freeze reference: git tag **domain-docs-v0**
Sources: qmind/architecture/03_Database/{001_Data_Dictionary,002_ER_Logical}.md
Amendments: qmind/architecture/04_Docs/007_Domain_Docs_Amendment_001.md
"""

from __future__ import annotations

from pathlib import Path

from alembic import op
from sqlalchemy import text

from app.sql_split import split_sql_statements

revision = "20260803_0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_PATH = Path(__file__).resolve().parents[2] / "sql" / "0001_initial_schema_domain_docs_v0.sql"


def upgrade() -> None:
    script = SQL_PATH.read_text(encoding="utf-8")
    bind = op.get_bind()
    # exec_driver_sql: preserve %I / %L in PL/pgSQL format() (text() mangles %)
    for stmt in split_sql_statements(script):
        bind.exec_driver_sql(stmt)


def downgrade() -> None:
    op.execute(text("DROP SCHEMA IF EXISTS qmind_app CASCADE"))
    tables = [
        "break_glass_sessions",
        "platform_audit_events",
        "ai_suggestions",
        "jobs",
        "reports",
        "action_items",
        "action_plans",
        "maturity_score_evidence_links",
        "maturity_dimension_scores",
        "maturity_scores",
        "maturity_assessments",
        "finding_evidences",
        "finding_requirements",
        "findings",
        "evidence_links",
        "evidences",
        "answers",
        "interviews",
        "assessment_team_members",
        "assessment_scopes",
        "assessments",
        "org_processes",
        "person_contacts",
        "memberships",
        "units",
        "organizations",
        "maturity_criteria",
        "maturity_dimensions",
        "maturity_models",
        "assessment_model_requirements",
        "questions",
        "criteria",
        "assessment_models",
        "requirements",
        "standard_versions",
        "standards",
        "platform_admin_grants",
        "users",
    ]
    for t in tables:
        op.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE"))
    op.execute(text("DROP ROLE IF EXISTS qmind_app"))
