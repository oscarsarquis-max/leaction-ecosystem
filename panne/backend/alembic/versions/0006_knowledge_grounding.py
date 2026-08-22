"""Biblioteca de conhecimento, grounding, perfis e LOQ.

Revision ID: 0006_knowledge_grounding
Revises: 0005_nutrition_calculation
Create Date: 2026-08-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_knowledge_grounding"
down_revision: Union[str, Sequence[str], None] = "0005_nutrition_calculation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_FREEZE_0005 = """
CREATE OR REPLACE FUNCTION panne_nutrition_calculation_freeze() RETURNS trigger AS $$
BEGIN
  IF OLD.status = 'invalidated' THEN
    RAISE EXCEPTION 'append_only';
  END IF;
  IF NEW.status = 'invalidated'
     AND NEW.organization_id IS NOT DISTINCT FROM OLD.organization_id
     AND NEW.formulation_version_id IS NOT DISTINCT FROM OLD.formulation_version_id
     AND NEW.calculation_basis IS NOT DISTINCT FROM OLD.calculation_basis
     AND NEW.formulation_version_status IS NOT DISTINCT FROM OLD.formulation_version_status
     AND NEW.is_simulation IS NOT DISTINCT FROM OLD.is_simulation
     AND NEW.formula_net_mass_g IS NOT DISTINCT FROM OLD.formula_net_mass_g
     AND NEW.expected_final_mass_g IS NOT DISTINCT FROM OLD.expected_final_mass_g
     AND NEW.portion_mass_g IS NOT DISTINCT FROM OLD.portion_mass_g
     AND NEW.algorithm_name IS NOT DISTINCT FROM OLD.algorithm_name
     AND NEW.algorithm_version IS NOT DISTINCT FROM OLD.algorithm_version
     AND NEW.rounding_policy IS NOT DISTINCT FROM OLD.rounding_policy
     AND NEW.calculated_at IS NOT DISTINCT FROM OLD.calculated_at
     AND NEW.calculated_by_user_id IS NOT DISTINCT FROM OLD.calculated_by_user_id
     AND NEW.warnings IS NOT DISTINCT FROM OLD.warnings
     AND NEW.assumptions IS NOT DISTINCT FROM OLD.assumptions
  THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'append_only';
END;
$$ LANGUAGE plpgsql;
"""

_FREEZE_0006 = """
CREATE OR REPLACE FUNCTION panne_nutrition_calculation_freeze() RETURNS trigger AS $$
BEGIN
  IF OLD.status = 'invalidated' THEN
    RAISE EXCEPTION 'append_only';
  END IF;
  IF NEW.status = 'invalidated'
     AND NEW.organization_id IS NOT DISTINCT FROM OLD.organization_id
     AND NEW.formulation_version_id IS NOT DISTINCT FROM OLD.formulation_version_id
     AND NEW.calculation_basis IS NOT DISTINCT FROM OLD.calculation_basis
     AND NEW.formulation_version_status IS NOT DISTINCT FROM OLD.formulation_version_status
     AND NEW.is_simulation IS NOT DISTINCT FROM OLD.is_simulation
     AND NEW.formula_net_mass_g IS NOT DISTINCT FROM OLD.formula_net_mass_g
     AND NEW.expected_final_mass_g IS NOT DISTINCT FROM OLD.expected_final_mass_g
     AND NEW.portion_mass_g IS NOT DISTINCT FROM OLD.portion_mass_g
     AND NEW.algorithm_name IS NOT DISTINCT FROM OLD.algorithm_name
     AND NEW.algorithm_version IS NOT DISTINCT FROM OLD.algorithm_version
     AND NEW.rounding_policy IS NOT DISTINCT FROM OLD.rounding_policy
     AND NEW.calculated_at IS NOT DISTINCT FROM OLD.calculated_at
     AND NEW.calculated_by_user_id IS NOT DISTINCT FROM OLD.calculated_by_user_id
     AND NEW.warnings IS NOT DISTINCT FROM OLD.warnings
     AND NEW.assumptions IS NOT DISTINCT FROM OLD.assumptions
     AND NEW.expectation_profile_id IS NOT DISTINCT FROM OLD.expectation_profile_id
  THEN
    RETURN NEW;
  END IF;
  RAISE EXCEPTION 'append_only';
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_unaccent_immutable(value text)
        RETURNS text
        LANGUAGE sql
        IMMUTABLE
        PARALLEL SAFE
        STRICT
        AS $$
          SELECT public.unaccent(value)
        $$
        """
    )

    op.create_table(
        "knowledge_source",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("authority_level", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("issuer_or_author", sa.Text(), nullable=True),
        sa.Column("jurisdiction", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), server_default=sa.text("'pt-BR'"), nullable=False),
        sa.Column("license_or_usage_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("release_state", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "source_kind IN ("
            "'recipe','normative','technical','nutritional_database','internal_document')",
            name="ck_knowledge_source_kind",
        ),
        sa.CheckConstraint(
            "authority_level IN ('official','curated','user_provided','unverified')",
            name="ck_knowledge_source_authority",
        ),
        sa.CheckConstraint(
            "status IN ('active','retired')",
            name="ck_knowledge_source_status",
        ),
        sa.CheckConstraint(
            "release_state IN ('private','restricted','released')",
            name="ck_knowledge_source_release",
        ),
        sa.CheckConstraint(
            "("
            "organization_id IS NULL AND release_state IN ('restricted','released')"
            ") OR ("
            "organization_id IS NOT NULL AND release_state = 'private'"
            ")",
            name="ck_knowledge_source_privacy",
        ),
        sa.CheckConstraint(
            "source_kind <> 'normative' OR authority_level <> 'official' OR ("
            "issuer_or_author IS NOT NULL AND char_length(btrim(issuer_or_author)) > 0"
            " AND jurisdiction IS NOT NULL AND char_length(btrim(jurisdiction)) > 0"
            ")",
            name="ck_knowledge_source_official_norm",
        ),
        sa.CheckConstraint(
            "NOT (source_kind = 'recipe' AND authority_level = 'official')",
            name="ck_knowledge_source_recipe_not_norm",
        ),
        sa.CheckConstraint(
            "char_length(btrim(title)) > 0 AND char_length(title) <= 500",
            name="ck_knowledge_source_title",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_source_org_kind",
        "knowledge_source",
        ["organization_id", "source_kind"],
    )
    op.create_index(
        "ix_knowledge_source_jurisdiction",
        "knowledge_source",
        ["jurisdiction", "authority_level"],
    )

    op.create_table(
        "knowledge_source_version",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("knowledge_source_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("version_label", sa.Text(), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_until", sa.Date(), nullable=True),
        sa.Column("regulatory_status", sa.Text(), nullable=False),
        sa.Column(
            "retrieved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("clock_timestamp()"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("language", sa.Text(), server_default=sa.text("'pt-BR'"), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column(
            "content_usage_kind",
            sa.Text(),
            server_default=sa.text("'not_applicable'"),
            nullable=False,
        ),
        sa.Column("review_status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "regulatory_status IN ("
            "'not_applicable','draft','public_consultation','in_force',"
            "'superseded','revoked','future')",
            name="ck_knowledge_version_regulatory",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending','reviewed','rejected')",
            name="ck_knowledge_version_review",
        ),
        sa.CheckConstraint(
            "content_usage_kind IN ("
            "'citation','summary','extracted_structure','not_applicable')",
            name="ck_knowledge_version_usage",
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_from IS NULL"
            " OR effective_until >= effective_from",
            name="ck_knowledge_version_window",
        ),
        sa.CheckConstraint(
            "content_hash IS NULL OR char_length(content_hash) = 64",
            name="ck_knowledge_version_hash",
        ),
        sa.CheckConstraint(
            "storage_key IS NULL OR content_hash IS NOT NULL",
            name="ck_knowledge_version_storage_hash",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_source_id"], ["knowledge_source.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "knowledge_source_id",
            "version_label",
            name="uq_knowledge_source_version_label",
        ),
    )
    op.create_index(
        "ix_knowledge_source_version_status",
        "knowledge_source_version",
        ["regulatory_status", "review_status", "effective_from"],
    )

    op.create_table(
        "knowledge_fragment",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("knowledge_source_version_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("locator_type", sa.Text(), nullable=False),
        sa.Column("locator_value", sa.Text(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_knowledge_fragment_sequence"),
        sa.CheckConstraint(
            "locator_type IN ("
            "'page','section','article','clause','annex','paragraph','block','url_fragment')",
            name="ck_knowledge_fragment_locator",
        ),
        sa.CheckConstraint(
            "char_length(btrim(locator_value)) > 0",
            name="ck_knowledge_fragment_locator_value",
        ),
        sa.CheckConstraint("char_length(btrim(content)) > 0", name="ck_knowledge_fragment_content"),
        sa.CheckConstraint(
            "char_length(content_hash) = 64",
            name="ck_knowledge_fragment_hash",
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_source_version_id"],
            ["knowledge_source_version.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "knowledge_source_version_id",
            "sequence",
            name="uq_knowledge_fragment_sequence",
        ),
    )
    op.create_index(
        "ix_knowledge_fragment_fts",
        "knowledge_fragment",
        ["search_vector"],
        postgresql_using="gin",
    )

    op.create_table(
        "knowledge_tag",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.CheckConstraint(
            "category IN ("
            "'product','process','ingredient','nutrient','allergen',"
            "'norm','jurisdiction','technique')",
            name="ck_knowledge_tag_category",
        ),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_knowledge_tag_status"),
        sa.CheckConstraint("char_length(btrim(code)) > 0", name="ck_knowledge_tag_code"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_knowledge_tag_code"),
    )

    op.create_table(
        "knowledge_source_tag",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("knowledge_source_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_tag_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_source_id"], ["knowledge_source.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["knowledge_tag_id"], ["knowledge_tag.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "knowledge_source_id",
            "knowledge_tag_id",
            name="uq_knowledge_source_tag",
        ),
    )

    op.create_table(
        "nutrition_expectation_profile",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("knowledge_source_version_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purpose IN ('technical','regulatory_candidate','custom')",
            name="ck_nutrition_expectation_purpose",
        ),
        sa.CheckConstraint(
            "status IN ('active','inactive')",
            name="ck_nutrition_expectation_status",
        ),
        sa.CheckConstraint(
            "char_length(btrim(code)) > 0",
            name="ck_nutrition_expectation_code",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["knowledge_source_version_id"],
            ["knowledge_source_version.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_nutrition_expectation_profile_org_code",
        "nutrition_expectation_profile",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NOT NULL"),
    )
    op.create_index(
        "uq_nutrition_expectation_profile_global_code",
        "nutrition_expectation_profile",
        ["code"],
        unique=True,
        postgresql_where=sa.text("organization_id IS NULL"),
    )

    op.create_table(
        "nutrition_expectation_profile_item",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_definition_id", sa.Uuid(), nullable=False),
        sa.Column("required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("sequence >= 1", name="ck_nutrition_expectation_item_sequence"),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["nutrition_expectation_profile.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["nutrient_definition_id"], ["nutrient_definition.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id",
            "nutrient_definition_id",
            name="uq_nutrition_expectation_profile_item_nutrient",
        ),
        sa.UniqueConstraint(
            "profile_id",
            "sequence",
            name="uq_nutrition_expectation_profile_item_sequence",
        ),
    )

    op.create_table(
        "grounding_query",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("retrieval_algorithm", sa.Text(), nullable=False),
        sa.Column("retrieval_version", sa.Text(), nullable=False),
        sa.Column("applicability_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("jsonb_typeof(filters) = 'object'", name="ck_grounding_query_filters"),
        sa.CheckConstraint(
            "query_text IS NULL OR char_length(query_text) <= 4000",
            name="ck_grounding_query_text",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "grounding_result",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("grounding_query_id", sa.Uuid(), nullable=False),
        sa.Column("knowledge_fragment_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(14, 6), nullable=False),
        sa.Column("selection_reason", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("rank >= 1", name="ck_grounding_result_rank"),
        sa.CheckConstraint("jsonb_typeof(selection_reason) = 'object'", name="ck_grounding_reason"),
        sa.ForeignKeyConstraint(
            ["grounding_query_id"], ["grounding_query.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["knowledge_fragment_id"], ["knowledge_fragment.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grounding_query_id", "rank", name="uq_grounding_result_rank"),
        sa.UniqueConstraint(
            "grounding_query_id",
            "knowledge_fragment_id",
            name="uq_grounding_result_fragment",
        ),
    )

    op.create_table(
        "grounding_citation",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("grounding_result_id", sa.Uuid(), nullable=False),
        sa.Column("source_title", sa.Text(), nullable=False),
        sa.Column("version_label", sa.Text(), nullable=False),
        sa.Column("issuer_or_author", sa.Text(), nullable=True),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("locator_type", sa.Text(), nullable=False),
        sa.Column("locator_value", sa.Text(), nullable=False),
        sa.Column("version_content_hash", sa.Text(), nullable=True),
        sa.Column("fragment_content_hash", sa.Text(), nullable=False),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "char_length(btrim(source_title)) > 0",
            name="ck_grounding_citation_title",
        ),
        sa.CheckConstraint(
            "char_length(fragment_content_hash) = 64",
            name="ck_grounding_citation_hash",
        ),
        sa.ForeignKeyConstraint(
            ["grounding_result_id"], ["grounding_result.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grounding_result_id", name="uq_grounding_citation_result"),
    )

    op.add_column(
        "nutrition_calculation",
        sa.Column("expectation_profile_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_nutrition_calculation_expectation_profile",
        "nutrition_calculation",
        "nutrition_expectation_profile",
        ["expectation_profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute(_FREEZE_0006)

    op.alter_column(
        "ingredient_nutrient",
        "value",
        existing_type=sa.Numeric(14, 6),
        nullable=True,
    )
    op.drop_constraint("ck_ingredient_nutrient_value", "ingredient_nutrient", type_="check")
    op.add_column(
        "ingredient_nutrient",
        sa.Column(
            "value_status",
            sa.Text(),
            server_default=sa.text("'measured'"),
            nullable=False,
        ),
    )
    op.add_column(
        "ingredient_nutrient",
        sa.Column("limit_of_quantification", sa.Numeric(14, 6), nullable=True),
    )
    op.add_column("ingredient_nutrient", sa.Column("loq_unit_id", sa.Uuid(), nullable=True))
    op.add_column("ingredient_nutrient", sa.Column("method_or_source", sa.Text(), nullable=True))
    op.create_foreign_key(
        "fk_ingredient_nutrient_loq_unit",
        "ingredient_nutrient",
        "measurement_unit",
        ["loq_unit_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_ingredient_nutrient_value",
        "ingredient_nutrient",
        "value IS NULL OR value >= 0",
    )
    op.create_check_constraint(
        "ck_ingredient_nutrient_value_status",
        "ingredient_nutrient",
        "value_status IN ('measured','known_zero','below_loq','not_detected','unknown')",
    )
    op.create_check_constraint(
        "ck_ingredient_nutrient_loq_positive",
        "ingredient_nutrient",
        "limit_of_quantification IS NULL OR limit_of_quantification > 0",
    )
    op.create_check_constraint(
        "ck_ingredient_nutrient_loq_pair",
        "ingredient_nutrient",
        "(limit_of_quantification IS NULL) = (loq_unit_id IS NULL)",
    )
    op.create_check_constraint(
        "ck_ingredient_nutrient_status_shape",
        "ingredient_nutrient",
        "("
        "value_status = 'measured' AND value IS NOT NULL"
        ") OR ("
        "value_status = 'known_zero' AND value = 0"
        ") OR ("
        "value_status = 'below_loq' AND value IS NULL"
        " AND limit_of_quantification IS NOT NULL AND loq_unit_id IS NOT NULL"
        ") OR ("
        "value_status = 'not_detected' AND value IS NULL"
        ") OR ("
        "value_status = 'unknown' AND value IS NULL AND limit_of_quantification IS NULL"
        ")",
    )
    op.create_check_constraint(
        "ck_ingredient_nutrient_loq_applicable",
        "ingredient_nutrient",
        "value_status IN ('below_loq','not_detected') OR limit_of_quantification IS NULL",
    )

    op.drop_constraint("ck_calculation_evidence_type", "calculation_evidence", type_="check")
    op.create_check_constraint(
        "ck_calculation_evidence_type",
        "calculation_evidence",
        "evidence_type IN ("
        "'source_value','calculated_contribution','missing_value',"
        "'yield_assumption','portion_assumption','unit_conversion',"
        "'warning','quantification_limit')",
    )

    op.execute(
        """
        CREATE FUNCTION panne_knowledge_fragment_set_search_vector() RETURNS trigger AS $$
        BEGIN
          NEW.search_vector := to_tsvector(
            'portuguese',
            panne_unaccent_immutable(coalesce(NEW.heading, '') || ' ' || NEW.content)
          );
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER knowledge_fragment_search_vector
        BEFORE INSERT ON knowledge_fragment
        FOR EACH ROW EXECUTE FUNCTION panne_knowledge_fragment_set_search_vector();
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_knowledge_source_version_guard() RETURNS trigger AS $$
        DECLARE
          review_changed boolean;
          status_changed boolean;
        BEGIN
          IF NEW.knowledge_source_id IS DISTINCT FROM OLD.knowledge_source_id
             OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
             OR NEW.version_label IS DISTINCT FROM OLD.version_label
             OR NEW.publication_date IS DISTINCT FROM OLD.publication_date
             OR NEW.effective_from IS DISTINCT FROM OLD.effective_from
             OR NEW.effective_until IS DISTINCT FROM OLD.effective_until
             OR NEW.retrieved_at IS DISTINCT FROM OLD.retrieved_at
             OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
             OR NEW.mime_type IS DISTINCT FROM OLD.mime_type
             OR NEW.language IS DISTINCT FROM OLD.language
             OR NEW.storage_key IS DISTINCT FROM OLD.storage_key
             OR NEW.content_usage_kind IS DISTINCT FROM OLD.content_usage_kind
             OR NEW.created_at IS DISTINCT FROM OLD.created_at
          THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          review_changed :=
            NEW.review_status IS DISTINCT FROM OLD.review_status
            OR NEW.reviewed_at IS DISTINCT FROM OLD.reviewed_at
            OR NEW.reviewed_by_user_id IS DISTINCT FROM OLD.reviewed_by_user_id;
          status_changed := NEW.regulatory_status IS DISTINCT FROM OLD.regulatory_status;
          IF review_changed THEN
            IF OLD.review_status <> 'pending'
               OR NEW.review_status NOT IN ('reviewed', 'rejected') THEN
              RAISE EXCEPTION 'append_only';
            END IF;
          END IF;
          IF status_changed AND NEW.regulatory_status NOT IN ('superseded', 'revoked') THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF NOT review_changed AND NOT status_changed THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER knowledge_source_version_guard
        BEFORE UPDATE ON knowledge_source_version
        FOR EACH ROW EXECUTE FUNCTION panne_knowledge_source_version_guard();
        """
    )

    for table in (
        "knowledge_fragment",
        "knowledge_source_tag",
        "nutrition_expectation_profile_item",
        "grounding_query",
        "grounding_result",
        "grounding_citation",
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_append_only
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_mutation();
            """
        )

    for table in (
        "knowledge_source",
        "knowledge_source_version",
        "knowledge_fragment",
        "knowledge_tag",
        "knowledge_source_tag",
        "nutrition_expectation_profile",
        "nutrition_expectation_profile_item",
        "grounding_query",
        "grounding_result",
        "grounding_citation",
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
        "grounding_citation",
        "grounding_result",
        "grounding_query",
        "nutrition_expectation_profile_item",
        "nutrition_expectation_profile",
        "knowledge_source_tag",
        "knowledge_tag",
        "knowledge_fragment",
        "knowledge_source_version",
        "knowledge_source",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_forbid_delete ON {table}")

    for table in (
        "grounding_citation",
        "grounding_result",
        "grounding_query",
        "nutrition_expectation_profile_item",
        "knowledge_source_tag",
        "knowledge_fragment",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")

    op.execute(
        "DROP TRIGGER IF EXISTS knowledge_source_version_guard ON knowledge_source_version"
    )
    op.execute("DROP FUNCTION IF EXISTS panne_knowledge_source_version_guard()")
    op.execute("DROP TRIGGER IF EXISTS knowledge_fragment_search_vector ON knowledge_fragment")
    op.execute("DROP FUNCTION IF EXISTS panne_knowledge_fragment_set_search_vector()")

    op.drop_constraint("ck_calculation_evidence_type", "calculation_evidence", type_="check")
    op.create_check_constraint(
        "ck_calculation_evidence_type",
        "calculation_evidence",
        "evidence_type IN ("
        "'source_value','calculated_contribution','missing_value',"
        "'yield_assumption','portion_assumption','unit_conversion','warning')",
    )

    op.drop_constraint("ck_ingredient_nutrient_loq_applicable", "ingredient_nutrient", type_="check")
    op.drop_constraint("ck_ingredient_nutrient_status_shape", "ingredient_nutrient", type_="check")
    op.drop_constraint("ck_ingredient_nutrient_loq_pair", "ingredient_nutrient", type_="check")
    op.drop_constraint("ck_ingredient_nutrient_loq_positive", "ingredient_nutrient", type_="check")
    op.drop_constraint("ck_ingredient_nutrient_value_status", "ingredient_nutrient", type_="check")
    op.drop_constraint("ck_ingredient_nutrient_value", "ingredient_nutrient", type_="check")
    op.drop_constraint("fk_ingredient_nutrient_loq_unit", "ingredient_nutrient", type_="foreignkey")
    op.drop_column("ingredient_nutrient", "method_or_source")
    op.drop_column("ingredient_nutrient", "loq_unit_id")
    op.drop_column("ingredient_nutrient", "limit_of_quantification")
    op.drop_column("ingredient_nutrient", "value_status")
    op.execute("UPDATE ingredient_nutrient SET value = 0 WHERE value IS NULL")
    op.alter_column(
        "ingredient_nutrient",
        "value",
        existing_type=sa.Numeric(14, 6),
        nullable=False,
    )
    op.create_check_constraint(
        "ck_ingredient_nutrient_value",
        "ingredient_nutrient",
        "value >= 0",
    )

    op.drop_constraint(
        "fk_nutrition_calculation_expectation_profile",
        "nutrition_calculation",
        type_="foreignkey",
    )
    op.drop_column("nutrition_calculation", "expectation_profile_id")
    op.execute(_FREEZE_0005)

    op.drop_table("grounding_citation")
    op.drop_table("grounding_result")
    op.drop_table("grounding_query")
    op.drop_table("nutrition_expectation_profile_item")
    op.drop_index(
        "uq_nutrition_expectation_profile_global_code",
        table_name="nutrition_expectation_profile",
    )
    op.drop_index(
        "uq_nutrition_expectation_profile_org_code",
        table_name="nutrition_expectation_profile",
    )
    op.drop_table("nutrition_expectation_profile")
    op.drop_table("knowledge_source_tag")
    op.drop_table("knowledge_tag")
    op.drop_index("ix_knowledge_fragment_fts", table_name="knowledge_fragment")
    op.drop_table("knowledge_fragment")
    op.drop_index("ix_knowledge_source_version_status", table_name="knowledge_source_version")
    op.drop_table("knowledge_source_version")
    op.drop_index("ix_knowledge_source_jurisdiction", table_name="knowledge_source")
    op.drop_index("ix_knowledge_source_org_kind", table_name="knowledge_source")
    op.drop_table("knowledge_source")
    op.execute("DROP FUNCTION IF EXISTS panne_unaccent_immutable(text)")
