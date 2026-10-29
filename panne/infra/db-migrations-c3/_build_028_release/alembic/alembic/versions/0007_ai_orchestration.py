"""Orquestração assistiva Bedrock e propostas.

Revision ID: 0007_ai_orchestration
Revises: 0006_knowledge_grounding
Create Date: 2026-08-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_ai_orchestration"
down_revision: Union[str, Sequence[str], None] = "0006_knowledge_grounding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_interaction",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("interaction_type", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("region", sa.Text(), nullable=False),
        sa.Column("prompt_template_version", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.Text(), nullable=False),
        sa.Column("grounding_query_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("input_token_count", sa.Integer(), nullable=True),
        sa.Column("output_token_count", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("stop_reason", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "interaction_type IN ("
            "'create_formulation_proposal','adapt_formulation_proposal','explain_proposal')",
            name="ck_ai_interaction_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending','completed','failed','rejected_by_validation')",
            name="ck_ai_interaction_status",
        ),
        sa.CheckConstraint("char_length(request_hash) = 64", name="ck_ai_interaction_hash"),
        sa.CheckConstraint(
            "input_token_count IS NULL OR input_token_count >= 0",
            name="ck_ai_interaction_in_tokens",
        ),
        sa.CheckConstraint(
            "output_token_count IS NULL OR output_token_count >= 0",
            name="ck_ai_interaction_out_tokens",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["grounding_query_id"], ["grounding_query.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_ai_interaction_id_org"),
    )
    op.create_index(
        "ix_ai_interaction_org_created",
        "ai_interaction",
        ["organization_id", "created_at"],
    )

    op.create_table(
        "ai_proposal",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ai_interaction_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_type", sa.Text(), nullable=False),
        sa.Column("base_formulation_version_id", sa.Uuid(), nullable=True),
        sa.Column("materialized_formulation_version_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("objective_summary", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "assumptions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "unresolved_questions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("proposal_type IN ('create','adapt')", name="ck_ai_proposal_type"),
        sa.CheckConstraint(
            "status IN ('draft','accepted','rejected','expired','invalid')",
            name="ck_ai_proposal_status",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(assumptions) = 'array'",
            name="ck_ai_proposal_assumptions",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(unresolved_questions) = 'array'",
            name="ck_ai_proposal_questions",
        ),
        sa.CheckConstraint("jsonb_typeof(warnings) = 'array'", name="ck_ai_proposal_warnings"),
        sa.ForeignKeyConstraint(
            ["ai_interaction_id", "organization_id"],
            ["ai_interaction.id", "ai_interaction.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["base_formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["materialized_formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "organization_id", name="uq_ai_proposal_id_org"),
        sa.UniqueConstraint("ai_interaction_id", name="uq_ai_proposal_interaction"),
    )

    op.create_table(
        "ai_proposal_item",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ai_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("ingredient_version_id", sa.Uuid(), nullable=True),
        sa.Column("proposed_ingredient_name", sa.Text(), nullable=False),
        sa.Column("resolution_status", sa.Text(), nullable=False),
        sa.Column("net_quantity_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("correction_factor", sa.Numeric(20, 10), nullable=True),
        sa.Column("is_flour_basis", sa.Boolean(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("confidence_note", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_ai_proposal_item_sequence"),
        sa.CheckConstraint(
            "resolution_status IN ('resolved','unresolved','ambiguous','not_allowed')",
            name="ck_ai_proposal_item_resolution",
        ),
        sa.CheckConstraint(
            "net_quantity_g IS NULL OR net_quantity_g > 0",
            name="ck_ai_proposal_item_qty",
        ),
        sa.CheckConstraint(
            "correction_factor IS NULL OR correction_factor > 0",
            name="ck_ai_proposal_item_factor",
        ),
        sa.CheckConstraint(
            "resolution_status <> 'resolved' OR ingredient_version_id IS NOT NULL",
            name="ck_ai_proposal_item_resolved",
        ),
        sa.ForeignKeyConstraint(
            ["ai_proposal_id", "organization_id"],
            ["ai_proposal.id", "ai_proposal.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_version_id", "organization_id"],
            ["ingredient_version.id", "ingredient_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ai_proposal_id", "sequence", name="uq_ai_proposal_item_sequence"),
    )

    op.create_table(
        "ai_proposal_process_step",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ai_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("temperature_celsius", sa.Numeric(6, 2), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_ai_proposal_step_sequence"),
        sa.CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 1",
            name="ck_ai_proposal_step_duration",
        ),
        sa.CheckConstraint(
            "temperature_celsius IS NULL OR "
            "(temperature_celsius >= -20 AND temperature_celsius <= 400)",
            name="ck_ai_proposal_step_temp",
        ),
        sa.ForeignKeyConstraint(
            ["ai_proposal_id", "organization_id"],
            ["ai_proposal.id", "ai_proposal.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ai_proposal_id", "sequence", name="uq_ai_proposal_step_sequence"),
    )

    op.create_table(
        "ai_proposal_citation",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ai_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_fragment_id", sa.Uuid(), nullable=False),
        sa.Column("grounding_citation_id", sa.Uuid(), nullable=False),
        sa.Column("claim_path", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("char_length(btrim(claim_path)) > 0", name="ck_ai_proposal_claim"),
        sa.ForeignKeyConstraint(
            ["ai_proposal_id", "organization_id"],
            ["ai_proposal.id", "ai_proposal.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_fragment_id"], ["knowledge_fragment.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["grounding_citation_id"], ["grounding_citation.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ai_proposal_id",
            "knowledge_fragment_id",
            "claim_path",
            name="uq_ai_proposal_citation_claim",
        ),
    )

    op.create_table(
        "ai_proposal_review",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ai_proposal_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "decision IN ('accepted','rejected','revision_requested')",
            name="ck_ai_proposal_review_decision",
        ),
        sa.ForeignKeyConstraint(
            ["ai_proposal_id", "organization_id"],
            ["ai_proposal.id", "ai_proposal.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_ai_proposal_review_accepted",
        "ai_proposal_review",
        ["ai_proposal_id"],
        unique=True,
        postgresql_where=sa.text("decision = 'accepted'"),
    )

    op.execute(
        """
        CREATE FUNCTION panne_ai_proposal_guard() RETURNS trigger AS $$
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
    op.execute(
        """
        CREATE TRIGGER ai_proposal_guard
        BEFORE UPDATE ON ai_proposal
        FOR EACH ROW EXECUTE FUNCTION panne_ai_proposal_guard();
        """
    )
    for table in (
        "ai_interaction",
        "ai_proposal_item",
        "ai_proposal_process_step",
        "ai_proposal_citation",
        "ai_proposal_review",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_append_only
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_mutation();
            """
        )
    for table in (
        "ai_interaction",
        "ai_proposal",
        "ai_proposal_item",
        "ai_proposal_process_step",
        "ai_proposal_citation",
        "ai_proposal_review",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_forbid_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_physical_delete();
            """
        )


def downgrade() -> None:
    for table in (
        "ai_proposal_review",
        "ai_proposal_citation",
        "ai_proposal_process_step",
        "ai_proposal_item",
        "ai_proposal",
        "ai_interaction",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_forbid_delete ON {table}")
    for table in (
        "ai_proposal_review",
        "ai_proposal_citation",
        "ai_proposal_process_step",
        "ai_proposal_item",
        "ai_interaction",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
    op.execute("DROP TRIGGER IF EXISTS ai_proposal_guard ON ai_proposal")
    op.execute("DROP FUNCTION IF EXISTS panne_ai_proposal_guard()")
    op.drop_index("uq_ai_proposal_review_accepted", table_name="ai_proposal_review")
    op.drop_table("ai_proposal_review")
    op.drop_table("ai_proposal_citation")
    op.drop_table("ai_proposal_process_step")
    op.drop_table("ai_proposal_item")
    op.drop_table("ai_proposal")
    op.drop_index("ix_ai_interaction_org_created", table_name="ai_interaction")
    op.drop_table("ai_interaction")
