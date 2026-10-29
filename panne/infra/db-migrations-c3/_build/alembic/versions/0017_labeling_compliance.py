"""Conformidade e rotulagem: dossiê versionado e candidatos.

Revision ID: 0017_labeling_compliance
Revises: 0016_recipe_ai_assistant
Create Date: 2026-08-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from app.modules.identity_organization.authorization import (
    LABELING_PERMISSION_DEFINITIONS,
    ROLE_PERMISSIONS,
)

revision: str = "0017_labeling_compliance"
down_revision: Union[str, Sequence[str], None] = "0016_recipe_ai_assistant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CODES = {code for code, _ in LABELING_PERMISSION_DEFINITIONS}
_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"
_TABLES = (
    "labeling_dossier",
    "labeling_applicability_profile",
    "labeling_dossier_version",
    "labeling_assessment",
    "labeling_finding",
    "labeling_evidence",
    "labeling_review",
    "labeling_nutrition_candidate",
    "labeling_nutrition_line",
    "labeling_front_of_pack",
    "labeling_ingredient_candidate",
    "labeling_warning_candidate",
    "labeling_mandatory_item",
    "labeling_label_candidate",
    "labeling_invalidation",
    "labeling_command",
)
_APPEND = (
    "labeling_applicability_profile",
    "labeling_assessment",
    "labeling_finding",
    "labeling_evidence",
    "labeling_review",
    "labeling_nutrition_candidate",
    "labeling_nutrition_line",
    "labeling_front_of_pack",
    "labeling_ingredient_candidate",
    "labeling_warning_candidate",
    "labeling_label_candidate",
    "labeling_invalidation",
    "labeling_command",
)
_RESULTS = (
    "pass",
    "fail",
    "insufficient_evidence",
    "insufficient_context",
    "manual_review_required",
    "not_applicable",
    "high",
    "below",
)


def _uuid() -> sa.Column:
    return sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _now() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
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
        "labeling_dossier",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("establishment_id", sa.Uuid(), nullable=True),
        sa.Column("technical_product_id", sa.Uuid(), nullable=True),
        sa.Column("formulation_id", sa.Uuid(), nullable=False),
        sa.Column("formulation_version_id", sa.Uuid(), nullable=False),
        sa.Column("nutrition_calculation_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        sa.Column("row_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint(
            "status IN ('draft','evaluated','reviewed','invalidated')",
            name="ck_labeling_dossier_status",
        ),
        sa.ForeignKeyConstraint(
            ["formulation_version_id", "organization_id"],
            ["formulation_version.id", "formulation_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_labeling_dossier_id_org", "labeling_dossier", ["id", "organization_id"], unique=True)

    op.create_table(
        "labeling_applicability_profile",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_id", sa.Uuid(), nullable=False),
        sa.Column("jurisdiction", sa.Text(), nullable=True),
        sa.Column("evaluation_date", sa.Date(), nullable=True),
        sa.Column("packed_food", sa.Boolean(), nullable=True),
        sa.Column("packed_away_from_consumer", sa.Boolean(), nullable=True),
        sa.Column("packed_at_point_of_sale", sa.Boolean(), nullable=True),
        sa.Column("packed_on_request", sa.Boolean(), nullable=True),
        sa.Column("same_establishment", sa.Boolean(), nullable=True),
        sa.Column("sales_channel", sa.Text(), nullable=True),
        sa.Column("food_service", sa.Boolean(), nullable=True),
        sa.Column("physical_state", sa.Text(), nullable=True),
        sa.Column("ready_to_eat", sa.Boolean(), nullable=True),
        sa.Column("regulatory_category_code", sa.Text(), nullable=True),
        sa.Column("category_confirmed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("package_area_cm2", sa.Numeric(12, 2), nullable=True),
        sa.Column("net_content_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("servings_per_package", sa.Integer(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("destination_market", sa.Text(), nullable=True),
        sa.Column("completeness", sa.Text(), server_default="incomplete", nullable=False),
        _now(),
        sa.CheckConstraint(
            "completeness IN ('incomplete','complete')",
            name="ck_labeling_profile_completeness",
        ),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_id", "organization_id"],
            ["labeling_dossier.id", "labeling_dossier.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_profile_id_org",
        "labeling_applicability_profile",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "labeling_dossier_version",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), server_default="evaluated", nullable=False),
        sa.Column("algorithm_name", sa.Text(), nullable=False),
        sa.Column("algorithm_version", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column(
            "snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.CheckConstraint(
            "status IN ('evaluated','reviewed','invalidated')",
            name="ck_labeling_version_status",
        ),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_id", "organization_id"],
            ["labeling_dossier.id", "labeling_dossier.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_dossier_version_number",
        "labeling_dossier_version",
        ["labeling_dossier_id", "version_number"],
        unique=True,
    )
    op.create_index(
        "uq_labeling_dossier_version_id_org",
        "labeling_dossier_version",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "labeling_assessment",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.Text(), server_default="evaluated", nullable=False),
        sa.Column("proposal_summary", sa.Text(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_assessment_id_org",
        "labeling_assessment",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "labeling_finding",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_assessment_id", sa.Uuid(), nullable=False),
        sa.Column("rule_code", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column("expected_value", sa.Text(), nullable=True),
        sa.Column("found_value", sa.Text(), nullable=True),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("source_version", sa.Text(), nullable=False),
        sa.Column("accessed_at", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("action_needed", sa.Boolean(), server_default="false", nullable=False),
        _now(),
        sa.CheckConstraint(
            "result IN (" + ",".join(f"'{item}'" for item in _RESULTS) + ")",
            name="ck_labeling_finding_result",
        ),
        sa.ForeignKeyConstraint(
            ["labeling_assessment_id", "organization_id"],
            ["labeling_assessment.id", "labeling_assessment.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_labeling_finding_id_org", "labeling_finding", ["id", "organization_id"], unique=True)

    op.create_table(
        "labeling_evidence",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_finding_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_key", sa.Text(), nullable=False),
        sa.Column(
            "detail",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        _now(),
        sa.ForeignKeyConstraint(
            ["labeling_finding_id", "organization_id"],
            ["labeling_finding.id", "labeling_finding.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_labeling_evidence_id_org", "labeling_evidence", ["id", "organization_id"], unique=True)

    op.create_table(
        "labeling_review",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        _now(),
        sa.CheckConstraint(
            "decision IN ('accepted','rejected','needs_changes')",
            name="ck_labeling_review_decision",
        ),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_labeling_review_id_org", "labeling_review", ["id", "organization_id"], unique=True)

    op.create_table(
        "labeling_nutrition_candidate",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("portion_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("household_measure", sa.Text(), nullable=True),
        sa.Column("servings_per_package", sa.Integer(), nullable=True),
        sa.Column("table_format", sa.Text(), server_default="vertical", nullable=False),
        sa.Column(
            "footnotes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        _now(),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_nutrition_id_org",
        "labeling_nutrition_candidate",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "labeling_nutrition_line",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_nutrition_candidate_id", sa.Uuid(), nullable=False),
        sa.Column("nutrient_code", sa.Text(), nullable=False),
        sa.Column("technical_per_100g", sa.Numeric(14, 6), nullable=True),
        sa.Column("regulatory_per_100g", sa.Numeric(14, 6), nullable=True),
        sa.Column("declared_per_100g", sa.Numeric(14, 6), nullable=True),
        sa.Column("declared_per_serving", sa.Numeric(14, 6), nullable=True),
        sa.Column("daily_value_percent", sa.Numeric(8, 2), nullable=True),
        sa.Column("completeness", sa.Text(), nullable=False),
        sa.Column("presented", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["labeling_nutrition_candidate_id", "organization_id"],
            ["labeling_nutrition_candidate.id", "labeling_nutrition_candidate.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_nutrition_line_code",
        "labeling_nutrition_line",
        ["labeling_nutrition_candidate_id", "nutrient_code"],
        unique=True,
    )

    op.create_table(
        "labeling_front_of_pack",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("added_sugars_result", sa.Text(), nullable=False),
        sa.Column("saturated_fat_result", sa.Text(), nullable=False),
        sa.Column("sodium_result", sa.Text(), nullable=False),
        sa.Column("magnifier_required", sa.Boolean(), nullable=True),
        sa.Column(
            "nutrients_high",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "compared",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_fop_version",
        "labeling_front_of_pack",
        ["labeling_dossier_version_id"],
        unique=True,
    )

    op.create_table(
        "labeling_ingredient_candidate",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("ingredient_version_id", sa.Uuid(), nullable=True),
        sa.Column("net_quantity_g", sa.Numeric(14, 6), nullable=True),
        sa.Column("compound", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "components",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("gap", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_ingredient_seq",
        "labeling_ingredient_candidate",
        ["labeling_dossier_version_id", "sequence"],
        unique=True,
    )

    op.create_table(
        "labeling_warning_candidate",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_warning_code",
        "labeling_warning_candidate",
        ["labeling_dossier_version_id", "code"],
        unique=True,
    )

    op.create_table(
        "labeling_mandatory_item",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("claim", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_mandatory_code",
        "labeling_mandatory_item",
        ["labeling_dossier_version_id", "code"],
        unique=True,
    )

    op.create_table(
        "labeling_label_candidate",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("watermark", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("payload_sha256", sa.Text(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_label_version",
        "labeling_label_candidate",
        ["labeling_dossier_version_id"],
        unique=True,
    )

    op.create_table(
        "labeling_invalidation",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("labeling_dossier_version_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        _now(),
        sa.ForeignKeyConstraint(
            ["labeling_dossier_version_id", "organization_id"],
            ["labeling_dossier_version.id", "labeling_dossier_version.organization_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_invalidation_id_org",
        "labeling_invalidation",
        ["id", "organization_id"],
        unique=True,
    )

    op.create_table(
        "labeling_command",
        _uuid(),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("payload_digest", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        _now(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_labeling_command_idempotency",
        "labeling_command",
        ["organization_id", "idempotency_key"],
        unique=True,
    )

    for table in _TABLES:
        _enable_rls(table)

    op.execute(
        """
        CREATE FUNCTION panne_labeling_append_only() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'append_only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table in _APPEND:
        op.execute(
            f"""
            CREATE TRIGGER {table}_append_only
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_labeling_append_only();
            """
        )
    op.execute(
        """
        CREATE FUNCTION panne_labeling_version_guard() RETURNS trigger AS $$
        BEGIN
          IF NEW.version_number IS DISTINCT FROM OLD.version_number
             OR NEW.algorithm_name IS DISTINCT FROM OLD.algorithm_name
             OR NEW.algorithm_version IS DISTINCT FROM OLD.algorithm_version
             OR NEW.content_hash IS DISTINCT FROM OLD.content_hash
             OR NEW.snapshot IS DISTINCT FROM OLD.snapshot
             OR NEW.labeling_dossier_id IS DISTINCT FROM OLD.labeling_dossier_id THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          IF OLD.status = 'invalidated'
             AND NEW.status IS DISTINCT FROM OLD.status THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER labeling_dossier_version_guard
        BEFORE UPDATE ON labeling_dossier_version
        FOR EACH ROW EXECUTE FUNCTION panne_labeling_version_guard();
        """
    )
    op.execute(
        """
        CREATE FUNCTION panne_labeling_mandatory_guard() RETURNS trigger AS $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM labeling_dossier_version v
            WHERE v.id = NEW.labeling_dossier_version_id
              AND v.status IN ('reviewed','invalidated')
          ) THEN
            RAISE EXCEPTION 'append_only';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER labeling_mandatory_item_guard
        BEFORE UPDATE ON labeling_mandatory_item
        FOR EACH ROW EXECUTE FUNCTION panne_labeling_mandatory_guard();
        """
    )
    for table in _TABLES:
        op.execute(
            f"""
            CREATE TRIGGER {table}_forbid_delete
            BEFORE DELETE ON {table}
            FOR EACH ROW EXECUTE FUNCTION panne_forbid_physical_delete();
            """
        )

    bind = op.get_bind()
    for code, description in LABELING_PERMISSION_DEFINITIONS:
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
            if code not in _CODES:
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
              ON labeling_dossier, labeling_applicability_profile, labeling_dossier_version,
                 labeling_assessment, labeling_finding, labeling_evidence, labeling_review,
                 labeling_nutrition_candidate, labeling_nutrition_line, labeling_front_of_pack,
                 labeling_ingredient_candidate, labeling_warning_candidate,
                 labeling_mandatory_item, labeling_label_candidate, labeling_invalidation,
                 labeling_command
              TO panne_runtime;
          END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    for code in _CODES:
        bind.execute(
            sa.text(
                "DELETE FROM role_permission WHERE permission_id IN "
                "(SELECT id FROM permission WHERE code = :code)"
            ),
            {"code": code},
        )
        bind.execute(sa.text("DELETE FROM permission WHERE code = :code"), {"code": code})
    for table in reversed(_TABLES):
        op.execute(f"DROP TRIGGER IF EXISTS {table}_forbid_delete ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}")
        op.execute(f"DROP POLICY IF EXISTS rls_{table}_org ON {table}")
    op.execute("DROP TRIGGER IF EXISTS labeling_dossier_version_guard ON labeling_dossier_version")
    op.execute("DROP TRIGGER IF EXISTS labeling_mandatory_item_guard ON labeling_mandatory_item")
    op.execute("DROP FUNCTION IF EXISTS panne_labeling_version_guard()")
    op.execute("DROP FUNCTION IF EXISTS panne_labeling_mandatory_guard()")
    op.execute("DROP FUNCTION IF EXISTS panne_labeling_append_only()")
    for table in reversed(_TABLES):
        op.drop_table(table)
