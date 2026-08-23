"""Assistente de receitas: referências por versão e proposta estendida.

Revision ID: 0016_recipe_ai_assistant
Revises: 0015_formulation_http
Create Date: 2026-08-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.modules.identity_organization.authorization import (
    RECIPE_PERMISSION_DEFINITIONS,
    ROLE_PERMISSIONS,
)

revision: str = "0016_recipe_ai_assistant"
down_revision: Union[str, Sequence[str], None] = "0015_formulation_http"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_AI_CODES = {
    "recipe.ai.propose",
    "recipe.ai.review",
    "recipe.ai.materialize",
}
_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"
_NEW_STATUSES = (
    "requested",
    "retrieving_evidence",
    "grounding_insufficient",
    "generating",
    "validation_failed",
    "awaiting_review",
    "draft",
    "accepted",
    "rejected",
    "materialized",
    "cancelled",
    "expired",
    "invalid",
)


def _enable_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY rls_{table}_org ON {table} FOR ALL "
        f"USING ({_ORG_EQ}) WITH CHECK ({_ORG_EQ})"
    )


def upgrade() -> None:
    op.create_table(
        "formulation_version_recipe_reference",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_version_id", sa.Uuid(), nullable=False),
        sa.Column("recipe_reference_id", sa.Uuid(), nullable=True),
        sa.Column("knowledge_source_version_id", sa.Uuid(), nullable=True),
        sa.Column("knowledge_fragment_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("source_version_label", sa.Text(), nullable=True),
        sa.Column("locator_type", sa.Text(), nullable=True),
        sa.Column("locator_value", sa.Text(), nullable=True),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("copied_from_version_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "recipe_reference_id IS NOT NULL OR knowledge_fragment_id IS NOT NULL",
            name="ck_version_ref_target",
        ),
        sa.CheckConstraint("jsonb_typeof(snapshot) = 'object'", name="ck_version_ref_snapshot"),
        sa.ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_reference_id", "organization_id"],
            ["recipe_reference.id", "recipe_reference.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_source_version_id"],
            ["knowledge_source_version.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_fragment_id"],
            ["knowledge_fragment.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_formulation_version_recipe_reference",
        "formulation_version_recipe_reference",
        ["formulation_version_id", "recipe_reference_id"],
        unique=True,
        postgresql_where=sa.text("recipe_reference_id IS NOT NULL"),
    )
    op.create_index(
        "uq_formulation_version_fragment_ref",
        "formulation_version_recipe_reference",
        ["formulation_version_id", "knowledge_fragment_id"],
        unique=True,
        postgresql_where=sa.text("knowledge_fragment_id IS NOT NULL"),
    )
    op.create_index(
        "uq_formulation_version_ref_id_org",
        "formulation_version_recipe_reference",
        ["id", "organization_id"],
        unique=True,
    )
    _enable_rls("formulation_version_recipe_reference")

    op.execute(
        """
        INSERT INTO formulation_version_recipe_reference (
            organization_id, formulation_version_id, recipe_reference_id, role,
            accessed_at, snapshot
        )
        SELECT
            fr.organization_id,
            fv.id,
            fr.recipe_reference_id,
            fr.role,
            rr.accessed_at,
            jsonb_build_object(
                'title', rr.title,
                'source_type', rr.source_type,
                'source_url', rr.source_url,
                'author', rr.author,
                'notes', rr.notes,
                'accessed_at', to_jsonb(rr.accessed_at)
            )
        FROM formulation_recipe_reference fr
        JOIN formulation_version fv
          ON fv.formulation_id = fr.formulation_id
         AND fv.organization_id = fr.organization_id
        JOIN recipe_reference rr
          ON rr.id = fr.recipe_reference_id
         AND rr.organization_id = fr.organization_id
        """
    )

    for column, default in (
        ("intent", None),
        ("prompt_template_name", None),
        ("output_hash", None),
    ):
        op.add_column("ai_proposal", sa.Column(column, sa.Text(), nullable=True))
    for column in (
        "constraints",
        "missing_data",
        "human_decisions",
        "accepted_changes",
        "rejected_changes",
    ):
        op.add_column(
            "ai_proposal",
            sa.Column(
                column,
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            ),
        )
    for column in (
        "retrieval_profile",
        "guided_input",
        "model_parameters",
        "input_canonical",
        "output_canonical",
        "guardrail_result",
    ):
        op.add_column(
            "ai_proposal",
            sa.Column(
                column,
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
        )
    op.add_column(
        "ai_proposal",
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
    )

    op.drop_constraint("ck_ai_proposal_status", "ai_proposal", type_="check")
    op.create_check_constraint(
        "ck_ai_proposal_status",
        "ai_proposal",
        "status IN (" + ",".join(f"'{item}'" for item in _NEW_STATUSES) + ")",
    )

    op.create_table(
        "ai_proposal_change",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ai_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("change_key", sa.Text(), nullable=False),
        sa.Column("change_kind", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.Column("before_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "citation_tokens",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("decision", sa.Text(), server_default="pending", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "change_kind IN ('added','removed','changed','unresolved')",
            name="ck_ai_proposal_change_kind",
        ),
        sa.CheckConstraint(
            "decision IN ('pending','accepted','rejected')",
            name="ck_ai_proposal_change_decision",
        ),
        sa.ForeignKeyConstraint(
            ["ai_proposal_id", "organization_id"],
            ["ai_proposal.id", "ai_proposal.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_ai_proposal_change_key",
        "ai_proposal_change",
        ["ai_proposal_id", "change_key"],
        unique=True,
    )
    _enable_rls("ai_proposal_change")

    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_ai_proposal_guard() RETURNS trigger AS $$
        BEGIN
          IF NEW.ai_interaction_id IS DISTINCT FROM OLD.ai_interaction_id
             OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
             OR NEW.proposal_type IS DISTINCT FROM OLD.proposal_type
             OR NEW.base_formulation_version_id IS DISTINCT FROM OLD.base_formulation_version_id
             OR NEW.title IS DISTINCT FROM OLD.title
             OR NEW.objective_summary IS DISTINCT FROM OLD.objective_summary
             OR NEW.assumptions IS DISTINCT FROM OLD.assumptions
             OR NEW.unresolved_questions IS DISTINCT FROM OLD.unresolved_questions
             OR NEW.warnings IS DISTINCT FROM OLD.warnings
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
             OR NEW.expires_at IS DISTINCT FROM OLD.expires_at
             OR NEW.intent IS DISTINCT FROM OLD.intent
             OR NEW.constraints IS DISTINCT FROM OLD.constraints
             OR NEW.retrieval_profile IS DISTINCT FROM OLD.retrieval_profile
             OR NEW.guided_input IS DISTINCT FROM OLD.guided_input
             OR NEW.prompt_template_name IS DISTINCT FROM OLD.prompt_template_name
             OR NEW.model_parameters IS DISTINCT FROM OLD.model_parameters
             OR NEW.input_canonical IS DISTINCT FROM OLD.input_canonical
             OR NEW.output_canonical IS DISTINCT FROM OLD.output_canonical
             OR NEW.output_hash IS DISTINCT FROM OLD.output_hash
             OR NEW.guardrail_result IS DISTINCT FROM OLD.guardrail_result
             OR NEW.missing_data IS DISTINCT FROM OLD.missing_data
          THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF OLD.status IN ('materialized','rejected','cancelled','expired','invalid',
                            'grounding_insufficient','validation_failed')
             AND NEW.status IS DISTINCT FROM OLD.status THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF OLD.status = 'accepted'
             AND NEW.status IS DISTINCT FROM OLD.status
             AND NEW.status <> 'materialized' THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF OLD.materialized_formulation_version_id IS NOT NULL
             AND NEW.materialized_formulation_version_id IS DISTINCT FROM
                 OLD.materialized_formulation_version_id THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_ai_proposal_change_guard() RETURNS trigger AS $$
        BEGIN
          IF NEW.change_key IS DISTINCT FROM OLD.change_key
             OR NEW.change_kind IS DISTINCT FROM OLD.change_kind
             OR NEW.path IS DISTINCT FROM OLD.path
             OR NEW.before_value IS DISTINCT FROM OLD.before_value
             OR NEW.after_value IS DISTINCT FROM OLD.after_value
             OR NEW.citation_tokens IS DISTINCT FROM OLD.citation_tokens
             OR NEW.ai_proposal_id IS DISTINCT FROM OLD.ai_proposal_id THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF OLD.decision <> 'pending'
             AND NEW.decision IS DISTINCT FROM OLD.decision THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER ai_proposal_change_guard
        BEFORE UPDATE ON ai_proposal_change
        FOR EACH ROW EXECUTE FUNCTION panne_ai_proposal_change_guard();
        """
    )

    bind = op.get_bind()
    for code, description in RECIPE_PERMISSION_DEFINITIONS:
        if code not in _AI_CODES:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO permission (code, description) "
                "SELECT :code, :description WHERE NOT EXISTS "
                "(SELECT 1 FROM permission WHERE code = :code)"
            ),
            {"code": code, "description": description},
        )
    for role, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            if code not in _AI_CODES:
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO role_permission (role, permission_id) "
                    "SELECT :role, id FROM permission WHERE code = :code "
                    "AND NOT EXISTS ("
                    "SELECT 1 FROM role_permission rp "
                    "WHERE rp.role = :role AND rp.permission_id = permission.id)"
                ),
                {"role": role, "code": code},
            )

    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
            GRANT SELECT, INSERT, UPDATE, DELETE
              ON formulation_version_recipe_reference, ai_proposal_change TO panne_runtime;
          END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    for code in _AI_CODES:
        bind.execute(
            sa.text(
                "DELETE FROM role_permission WHERE permission_id IN "
                "(SELECT id FROM permission WHERE code = :code)"
            ),
            {"code": code},
        )
        bind.execute(sa.text("DELETE FROM permission WHERE code = :code"), {"code": code})
    op.execute("DROP TRIGGER IF EXISTS ai_proposal_change_guard ON ai_proposal_change")
    op.execute("DROP FUNCTION IF EXISTS panne_ai_proposal_change_guard()")
    op.execute("DROP POLICY IF EXISTS rls_ai_proposal_change_org ON ai_proposal_change")
    op.execute("DROP TABLE IF EXISTS ai_proposal_change")
    op.execute("ALTER TABLE ai_proposal DISABLE TRIGGER ai_proposal_guard")
    op.execute("UPDATE ai_proposal SET status = 'accepted' WHERE status = 'materialized'")
    op.execute(
        "UPDATE ai_proposal SET status = 'rejected' "
        "WHERE status IN ('cancelled','grounding_insufficient','validation_failed')"
    )
    op.execute(
        "UPDATE ai_proposal SET status = 'draft' "
        "WHERE status IN ("
        "'requested','retrieving_evidence','generating','awaiting_review')"
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_ai_proposal_guard() RETURNS trigger AS $$
        BEGIN
          IF NEW.ai_interaction_id IS DISTINCT FROM OLD.ai_interaction_id
             OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
             OR NEW.proposal_type IS DISTINCT FROM OLD.proposal_type
             OR NEW.base_formulation_version_id IS DISTINCT FROM OLD.base_formulation_version_id
             OR NEW.title IS DISTINCT FROM OLD.title
             OR NEW.objective_summary IS DISTINCT FROM OLD.objective_summary
             OR NEW.assumptions IS DISTINCT FROM OLD.assumptions
             OR NEW.unresolved_questions IS DISTINCT FROM OLD.unresolved_questions
             OR NEW.warnings IS DISTINCT FROM OLD.warnings
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
             OR NEW.expires_at IS DISTINCT FROM OLD.expires_at
          THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF OLD.status <> 'draft'
             AND NEW.status IS DISTINCT FROM OLD.status THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF NEW.status NOT IN ('draft','accepted','rejected','expired','invalid') THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF OLD.materialized_formulation_version_id IS NOT NULL
             AND NEW.materialized_formulation_version_id IS DISTINCT FROM
                 OLD.materialized_formulation_version_id THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.drop_constraint("ck_ai_proposal_status", "ai_proposal", type_="check")
    op.create_check_constraint(
        "ck_ai_proposal_status",
        "ai_proposal",
        "status IN ('draft','accepted','rejected','expired','invalid')",
    )
    op.execute("ALTER TABLE ai_proposal ENABLE TRIGGER ai_proposal_guard")
    for column in (
        "row_version",
        "guardrail_result",
        "output_canonical",
        "input_canonical",
        "model_parameters",
        "guided_input",
        "retrieval_profile",
        "rejected_changes",
        "accepted_changes",
        "human_decisions",
        "missing_data",
        "constraints",
        "output_hash",
        "prompt_template_name",
        "intent",
    ):
        op.drop_column("ai_proposal", column)
    op.execute(
        "DROP POLICY IF EXISTS rls_formulation_version_recipe_reference_org "
        "ON formulation_version_recipe_reference"
    )
    op.drop_table("formulation_version_recipe_reference")
