"""Governança regulatória e avaliações determinísticas.

Revision ID: 0008_compliance_governance
Revises: 0007_ai_orchestration
Create Date: 2026-08-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_compliance_governance"
down_revision: Union[str, Sequence[str], None] = "0007_ai_orchestration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DOMAINS = (
    "labeling,nutrition,gmp,sop,haccp,allergens,"
    "ingredients_additives_packaging,regularization,"
    "occupational_safety,state_municipal,private_technical_standards"
)
_EVAL_TYPES = (
    "evidence_presence,numeric_comparison,boolean_condition,"
    "catalog_membership,mandatory_manual_review,compound"
)


def upgrade() -> None:
    op.create_table(
        "compliance_framework",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("regulatory_domain", sa.Text(), nullable=False),
        sa.Column("scope", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            f"regulatory_domain IN ({','.join(repr(item) for item in _DOMAINS.split(','))})",
            name="ck_compliance_framework_domain",
        ),
        sa.CheckConstraint("scope IN ('global','organizational')", name="ck_compliance_scope"),
        sa.CheckConstraint(
            "status IN ('draft','active','archived')",
            name="ck_compliance_framework_status",
        ),
        sa.CheckConstraint(
            "(scope = 'global' AND organization_id IS NULL) OR "
            "(scope = 'organizational' AND organization_id IS NOT NULL)",
            name="ck_compliance_framework_owner",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_compliance_framework_id_org"),
    )
    op.create_index(
        "uq_compliance_framework_global_code",
        "compliance_framework",
        ["code"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NULL"),
    )
    op.create_index(
        "uq_compliance_framework_org_code",
        "compliance_framework",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NOT NULL"),
    )

    op.create_table(
        "compliance_framework_version",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("compliance_framework_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("jurisdiction", sa.Text(), nullable=False),
        sa.Column(
            "authorities",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("knowledge_cutoff_date", sa.Date(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("version_number >= 1", name="ck_compliance_version_number"),
        sa.CheckConstraint(
            "char_length(btrim(jurisdiction)) > 0",
            name="ck_compliance_jurisdiction",
        ),
        sa.CheckConstraint("jsonb_typeof(authorities) = 'array'", name="ck_compliance_authorities"),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until >= effective_from",
            name="ck_compliance_version_window",
        ),
        sa.CheckConstraint(
            "status IN ('draft','pending_review','active','superseded','revoked')",
            name="ck_compliance_version_status",
        ),
        sa.ForeignKeyConstraint(
            ["compliance_framework_id"],
            ["compliance_framework.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["activated_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "compliance_framework_id",
            "version_number",
            name="uq_compliance_framework_version_number",
        ),
    )
    op.create_index(
        "uq_compliance_framework_one_active",
        "compliance_framework_version",
        ["compliance_framework_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "compliance_requirement",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("compliance_framework_version_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("regulatory_domain", sa.Text(), nullable=False),
        sa.Column("normative_force", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("evaluation_type", sa.Text(), nullable=False),
        sa.Column(
            "parameters",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "applicability",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("review_status", sa.Text(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            f"regulatory_domain IN ({','.join(repr(item) for item in _DOMAINS.split(','))})",
            name="ck_compliance_requirement_domain",
        ),
        sa.CheckConstraint(
            "normative_force IN ('mandatory','recommended','informational')",
            name="ck_compliance_force",
        ),
        sa.CheckConstraint(
            "severity IN ('critical','major','minor','info')",
            name="ck_compliance_severity",
        ),
        sa.CheckConstraint(
            f"evaluation_type IN ({','.join(repr(item) for item in _EVAL_TYPES.split(','))})",
            name="ck_compliance_eval_type",
        ),
        sa.CheckConstraint("jsonb_typeof(parameters) = 'object'", name="ck_compliance_params"),
        sa.CheckConstraint("jsonb_typeof(applicability) = 'object'", name="ck_compliance_appl"),
        sa.CheckConstraint(
            "review_status IN ('pending','reviewed','rejected')",
            name="ck_compliance_req_review",
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_compliance_requirement_sequence"),
        sa.ForeignKeyConstraint(
            ["compliance_framework_version_id"],
            ["compliance_framework_version.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "compliance_framework_version_id",
            "code",
            name="uq_compliance_requirement_code",
        ),
        sa.UniqueConstraint(
            "compliance_framework_version_id",
            "sequence",
            name="uq_compliance_requirement_sequence",
        ),
    )

    op.create_table(
        "compliance_requirement_source",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("compliance_requirement_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_fragment_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_source_version_id", sa.Uuid(), nullable=False),
        sa.Column("citation_role", sa.Text(), nullable=False),
        sa.Column("normative_class", sa.Text(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "citation_role IN ('foundation','definition','threshold','exception','guidance')",
            name="ck_compliance_citation_role",
        ),
        sa.CheckConstraint(
            "normative_class IN ("
            "'in_force_act','future_act','revoked_or_superseded','proposal',"
            "'official_guidance','private_standard','non_normative_technical')",
            name="ck_compliance_normative_class",
        ),
        sa.CheckConstraint("jsonb_typeof(snapshot) = 'object'", name="ck_compliance_source_snap"),
        sa.ForeignKeyConstraint(
            ["compliance_requirement_id"],
            ["compliance_requirement.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_fragment_id"],
            ["knowledge_fragment.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_source_version_id"],
            ["knowledge_source_version.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "compliance_requirement_id",
            "knowledge_fragment_id",
            "citation_role",
            name="uq_compliance_requirement_source",
        ),
    )

    op.create_table(
        "compliance_profile",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=True),
        sa.Column("country", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("municipality", sa.Text(), nullable=True),
        sa.Column("activity", sa.Text(), nullable=False),
        sa.Column(
            "product_categories",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("sale_form", sa.Text(), nullable=True),
        sa.Column("packaging", sa.Text(), nullable=True),
        sa.Column(
            "processes",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "equipment",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column(
            "extra_context",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("is_snapshot", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source_profile_id", sa.Uuid(), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "activity IN ('food_service','producer_processor','hybrid')",
            name="ck_compliance_activity",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(product_categories) = 'array'",
            name="ck_compliance_profile_categories",
        ),
        sa.CheckConstraint("jsonb_typeof(processes) = 'array'", name="ck_compliance_profile_proc"),
        sa.CheckConstraint("jsonb_typeof(equipment) = 'array'", name="ck_compliance_profile_eq"),
        sa.CheckConstraint(
            "jsonb_typeof(extra_context) = 'object'",
            name="ck_compliance_profile_ctx",
        ),
        sa.CheckConstraint(
            "(is_snapshot = false AND frozen_at IS NULL) OR "
            "(is_snapshot = true AND frozen_at IS NOT NULL)",
            name="ck_compliance_profile_snapshot",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_profile_id"],
            ["compliance_profile.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["establishment_id", "organization_id"],
            ["establishment.id", "establishment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_compliance_profile_id_org"),
    )

    op.create_table(
        "compliance_assessment",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("compliance_profile_id", sa.Uuid(), nullable=False),
        sa.Column("compliance_framework_version_id", sa.Uuid(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("assessed_on", sa.Date(), nullable=False),
        sa.Column("algorithm_name", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("completeness", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "(target_type IS NULL AND target_id IS NULL) OR "
            "(target_type IN ("
            "'formulation_version','ingredient_version','establishment','technical_product'"
            ") AND target_id IS NOT NULL)",
            name="ck_compliance_target",
        ),
        sa.CheckConstraint(
            "status IN ('draft','evaluated','reviewed','invalidated')",
            name="ck_compliance_assessment_status",
        ),
        sa.CheckConstraint(
            "completeness IN ('complete','incomplete','insufficient_context')",
            name="ck_compliance_completeness",
        ),
        sa.ForeignKeyConstraint(
            ["compliance_profile_id", "organization_id"],
            ["compliance_profile.id", "compliance_profile.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["compliance_framework_version_id"],
            ["compliance_framework_version.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_compliance_assessment_id_org"),
    )

    op.create_table(
        "compliance_finding",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("compliance_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("compliance_requirement_id", sa.Uuid(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("technical_message", sa.Text(), nullable=False),
        sa.Column("input_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("parameter_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "result IN ('pass','fail','not_applicable','insufficient_data','manual_review')",
            name="ck_compliance_finding_result",
        ),
        sa.CheckConstraint(
            "severity IN ('critical','major','minor','info')",
            name="ck_compliance_finding_severity",
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_compliance_finding_sequence"),
        sa.CheckConstraint("jsonb_typeof(input_snapshot) = 'object'", name="ck_compliance_in_snap"),
        sa.CheckConstraint(
            "jsonb_typeof(parameter_snapshot) = 'object'",
            name="ck_compliance_param_snap",
        ),
        sa.ForeignKeyConstraint(
            ["compliance_assessment_id", "organization_id"],
            ["compliance_assessment.id", "compliance_assessment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["compliance_requirement_id"],
            ["compliance_requirement.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "compliance_assessment_id",
            "compliance_requirement_id",
            name="uq_compliance_finding_requirement",
        ),
        sa.UniqueConstraint(
            "compliance_assessment_id",
            "sequence",
            name="uq_compliance_finding_sequence",
        ),
        sa.UniqueConstraint("id", "organization_id", name="uq_compliance_finding_id_org"),
    )

    op.create_table(
        "compliance_evidence",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("compliance_finding_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_kind", sa.Text(), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("knowledge_fragment_id", sa.Uuid(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("locator", sa.Text(), nullable=True),
        sa.Column(
            "snapshot",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "evidence_kind IN ('technical','normative')",
            name="ck_compliance_evidence_kind",
        ),
        sa.CheckConstraint("jsonb_typeof(snapshot) = 'object'", name="ck_compliance_ev_snap"),
        sa.ForeignKeyConstraint(
            ["compliance_finding_id", "organization_id"],
            ["compliance_finding.id", "compliance_finding.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_fragment_id"],
            ["knowledge_fragment.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "compliance_review",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("compliance_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "decision IN ('accepted','rejected','needs_changes','revoked')",
            name="ck_compliance_review_decision",
        ),
        sa.CheckConstraint(
            "char_length(btrim(justification)) > 0",
            name="ck_compliance_justification",
        ),
        sa.ForeignKeyConstraint(
            ["compliance_assessment_id", "organization_id"],
            ["compliance_assessment.id", "compliance_assessment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.execute(
        """
        CREATE FUNCTION panne_compliance_framework_guard() RETURNS trigger AS $$
        BEGIN
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
             OR NEW.code IS DISTINCT FROM OLD.code
             OR NEW.scope IS DISTINCT FROM OLD.scope
             OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF OLD.status = 'archived' THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER compliance_framework_guard
        BEFORE UPDATE ON compliance_framework
        FOR EACH ROW EXECUTE FUNCTION panne_compliance_framework_guard();
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_compliance_version_guard() RETURNS trigger AS $$
        BEGIN
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
             OR NEW.compliance_framework_id IS DISTINCT FROM OLD.compliance_framework_id
             OR NEW.version_number IS DISTINCT FROM OLD.version_number
             OR NEW.jurisdiction IS DISTINCT FROM OLD.jurisdiction
             OR NEW.authorities IS DISTINCT FROM OLD.authorities
             OR NEW.effective_from IS DISTINCT FROM OLD.effective_from
             OR NEW.effective_until IS DISTINCT FROM OLD.effective_until
             OR NEW.knowledge_cutoff_date IS DISTINCT FROM OLD.knowledge_cutoff_date
             OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF OLD.status NOT IN ('draft','pending_review','active') THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER compliance_framework_version_guard
        BEFORE UPDATE ON compliance_framework_version
        FOR EACH ROW EXECUTE FUNCTION panne_compliance_version_guard();
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_compliance_profile_guard() RETURNS trigger AS $$
        BEGIN
          IF OLD.is_snapshot THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF NEW.organization_id IS DISTINCT FROM OLD.organization_id
             OR NEW.id IS DISTINCT FROM OLD.id THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER compliance_profile_guard
        BEFORE UPDATE ON compliance_profile
        FOR EACH ROW EXECUTE FUNCTION panne_compliance_profile_guard();
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_compliance_assessment_guard() RETURNS trigger AS $$
        BEGIN
          IF NEW.id IS DISTINCT FROM OLD.id
             OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
             OR NEW.compliance_profile_id IS DISTINCT FROM OLD.compliance_profile_id
             OR NEW.compliance_framework_version_id IS DISTINCT FROM
                OLD.compliance_framework_version_id
             OR NEW.target_type IS DISTINCT FROM OLD.target_type
             OR NEW.target_id IS DISTINCT FROM OLD.target_id
             OR NEW.assessed_on IS DISTINCT FROM OLD.assessed_on
             OR NEW.algorithm_name IS DISTINCT FROM OLD.algorithm_name
             OR NEW.algorithm_version IS DISTINCT FROM OLD.algorithm_version
             OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF OLD.status = 'invalidated' THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER compliance_assessment_guard
        BEFORE UPDATE ON compliance_assessment
        FOR EACH ROW EXECUTE FUNCTION panne_compliance_assessment_guard();
        """
    )
    for table in (
        "compliance_requirement",
        "compliance_requirement_source",
        "compliance_finding",
        "compliance_evidence",
        "compliance_review",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_append_only
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_mutation();
            """
        )
    for table in (
        "compliance_framework",
        "compliance_framework_version",
        "compliance_requirement",
        "compliance_requirement_source",
        "compliance_profile",
        "compliance_assessment",
        "compliance_finding",
        "compliance_evidence",
        "compliance_review",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_forbid_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_physical_delete();
            """
        )


def downgrade() -> None:
    tables = (
        "compliance_review",
        "compliance_evidence",
        "compliance_finding",
        "compliance_assessment",
        "compliance_profile",
        "compliance_requirement_source",
        "compliance_requirement",
        "compliance_framework_version",
        "compliance_framework",
    )
    for table in tables:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_forbid_delete ON {table}")
    for table in (
        "compliance_requirement",
        "compliance_requirement_source",
        "compliance_finding",
        "compliance_evidence",
        "compliance_review",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
    op.execute("DROP TRIGGER IF EXISTS compliance_assessment_guard ON compliance_assessment")
    op.execute("DROP TRIGGER IF EXISTS compliance_profile_guard ON compliance_profile")
    op.execute(
        "DROP TRIGGER IF EXISTS compliance_framework_version_guard "
        "ON compliance_framework_version"
    )
    op.execute("DROP TRIGGER IF EXISTS compliance_framework_guard ON compliance_framework")
    op.execute("DROP FUNCTION IF EXISTS panne_compliance_assessment_guard()")
    op.execute("DROP FUNCTION IF EXISTS panne_compliance_profile_guard()")
    op.execute("DROP FUNCTION IF EXISTS panne_compliance_version_guard()")
    op.execute("DROP FUNCTION IF EXISTS panne_compliance_framework_guard()")
    for table in tables:
        op.drop_table(table)
