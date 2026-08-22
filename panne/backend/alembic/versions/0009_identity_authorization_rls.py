"""Identidade externa, autorização interna e RLS.

Revision ID: 0009_identity_authorization_rls
Revises: 0008_compliance_governance
Create Date: 2026-08-22
"""

# ruff: noqa: E501

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from app.modules.identity_organization.authorization import (
    FOUNDATION_PERMISSIONS,
    MEMBERSHIP_ROLES,
    ROLE_PERMISSIONS,
)
from app.modules.identity_organization.rls_inventory import (
    GLOBAL_TABLES,
    HYBRID_TABLES,
    IDENTITY_TABLES,
    INHERITED_TABLES,
    ORGANIZATIONAL_TABLES,
    PRE_PRODUCTION_RLS_TABLES,
)

revision: str = "0009_identity_authorization_rls"
down_revision: Union[str, Sequence[str], None] = "0008_compliance_governance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ROLE_CSV = ",".join(f"'{role}'" for role in MEMBERSHIP_ROLES)
_OLD_ROLES = "role IN ('owner','administrator','technical_responsible','production','commercial','viewer')"

_ORG_EQ = "organization_id IS NOT NULL AND organization_id = panne_current_org_id()"
_ACTOR = "panne_current_user_id() IS NOT NULL"
_SELF_USER = "id = panne_current_user_id()"
_IDENTITY_LOOKUP = (
    "(user_id = panne_current_user_id()) OR ("
    "nullif(current_setting('app.current_issuer', true), '') IS NOT NULL "
    "AND issuer = current_setting('app.current_issuer', true) "
    "AND subject = current_setting('app.current_subject', true)"
    ")"
)
_MEMBERSHIP_READ = (
    "user_id = panne_current_user_id() OR organization_id = panne_current_org_id()"
)
_ORG_READ = (
    "id = panne_current_org_id() OR EXISTS ("
    "SELECT 1 FROM organization_membership m "
    "WHERE m.organization_id = organization.id "
    "AND m.user_id = panne_current_user_id() "
    "AND m.status = 'active'"
    ")"
)
_KNOWLEDGE_READ = (
    f"({_ORG_EQ}) OR ("
    "organization_id IS NULL AND release_state = 'released' "
    f"AND {_ACTOR})"
)
_KNOWLEDGE_CHILD_READ = (
    f"({_ORG_EQ}) OR ("
    "organization_id IS NULL AND EXISTS ("
    "SELECT 1 FROM knowledge_source ks "
    "WHERE ks.id = knowledge_source_id AND ks.release_state = 'released'"
    f" AND {_ACTOR}))"
)
_FRAGMENT_READ = (
    f"({_ORG_EQ}) OR ("
    "organization_id IS NULL AND EXISTS ("
    "SELECT 1 FROM knowledge_source_version ksv "
    "JOIN knowledge_source ks ON ks.id = ksv.knowledge_source_id "
    "WHERE ksv.id = knowledge_source_version_id AND ks.release_state = 'released'"
    f" AND {_ACTOR}))"
)
_HYBRID_CATALOG_READ = f"({_ORG_EQ}) OR (organization_id IS NULL AND {_ACTOR})"
_GROUNDING_READ = (
    f"({_ORG_EQ}) OR (organization_id IS NULL AND created_by_user_id = panne_current_user_id())"
)
_AUDIT_READ = (
    f"({_ORG_EQ}) OR (organization_id IS NULL AND actor_user_id = panne_current_user_id())"
)
_AUDIT_WRITE = (
    "actor_user_id IS NOT DISTINCT FROM panne_current_user_id() "
    "AND organization_id IS NOT DISTINCT FROM panne_current_org_id()"
)


def _enable(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")


def _drop_rls(table: str) -> None:
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")


def _policy_all(table: str, name: str, using: str, check: str | None = None) -> None:
    clause = f" WITH CHECK ({check})" if check is not None else ""
    op.execute(f"CREATE POLICY {name} ON {table} FOR ALL USING ({using}){clause}")


def _policy_select(table: str, name: str, using: str) -> None:
    op.execute(f"CREATE POLICY {name} ON {table} FOR SELECT USING ({using})")


def _policy_write(table: str, name: str, using: str, check: str) -> None:
    for command in ("INSERT", "UPDATE", "DELETE"):
        extra = f" WITH CHECK ({check})" if command in {"INSERT", "UPDATE"} else ""
        using_sql = f" USING ({using})" if command != "INSERT" else ""
        if command == "INSERT":
            op.execute(f"CREATE POLICY {name}_{command.lower()} ON {table} FOR INSERT WITH CHECK ({check})")
        else:
            op.execute(
                f"CREATE POLICY {name}_{command.lower()} ON {table} FOR {command}{using_sql}{extra}"
            )


def upgrade() -> None:
    op.create_table(
        "auth_identity",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active','inactive')", name="ck_auth_identity_status"),
        sa.CheckConstraint("char_length(btrim(issuer)) > 0 AND char_length(btrim(subject)) > 0", name="ck_auth_identity_pair"),
        sa.ForeignKeyConstraint(["user_id"], ["app_user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("issuer", "subject", name="uq_auth_identity_issuer_subject"),
    )

    op.create_table(
        "permission",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("char_length(btrim(code)) > 0", name="ck_permission_code"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_permission_code"),
    )

    op.create_table(
        "role_permission",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"role IN ({_ROLE_CSV})", name="ck_role_permission_role"),
        sa.ForeignKeyConstraint(["permission_id"], ["permission.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role", "permission_id", name="uq_role_permission"),
    )

    op.drop_constraint("ck_membership_role", "organization_membership", type_="check")
    op.create_check_constraint(
        "ck_membership_role",
        "organization_membership",
        f"role IN ({_ROLE_CSV})",
    )

    bind = op.get_bind()
    for code, description in FOUNDATION_PERMISSIONS:
        bind.execute(
            sa.text(
                "INSERT INTO permission (code, description) VALUES (:code, :description)"
            ),
            {"code": code, "description": description},
        )
    for role, codes in ROLE_PERMISSIONS.items():
        for code in codes:
            bind.execute(
                sa.text(
                    "INSERT INTO role_permission (role, permission_id) "
                    "SELECT :role, id FROM permission WHERE code = :code"
                ),
                {"role": role, "code": code},
            )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_current_org_id() RETURNS uuid
        LANGUAGE plpgsql STABLE AS $$
        DECLARE raw text;
        BEGIN
          raw := nullif(btrim(current_setting('app.current_organization_id', true)), '');
          IF raw IS NULL THEN
            RETURN NULL;
          END IF;
          RETURN raw::uuid;
        EXCEPTION WHEN invalid_text_representation THEN
          RETURN NULL;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_current_user_id() RETURNS uuid
        LANGUAGE plpgsql STABLE AS $$
        DECLARE raw text;
        BEGIN
          raw := nullif(btrim(current_setting('app.current_user_id', true)), '');
          IF raw IS NULL THEN
            RETURN NULL;
          END IF;
          RETURN raw::uuid;
        EXCEPTION WHEN invalid_text_representation THEN
          RETURN NULL;
        END;
        $$
        """
    )

    for table in sorted(PRE_PRODUCTION_RLS_TABLES):
        _enable(table)

    for table in sorted(ORGANIZATIONAL_TABLES):
        _policy_all(table, f"rls_{table}_org", _ORG_EQ, _ORG_EQ)

    _policy_select("organization", "rls_organization_select", _ORG_READ)
    _policy_select("app_user", "rls_app_user_select", f"{_SELF_USER} OR EXISTS (SELECT 1 FROM organization_membership m WHERE m.user_id = app_user.id AND m.organization_id = panne_current_org_id() AND m.status = 'active')")
    _policy_select("auth_identity", "rls_auth_identity_select", _IDENTITY_LOOKUP)
    _policy_select("organization_membership", "rls_organization_membership_select", _MEMBERSHIP_READ)
    _policy_all(
        "organization_membership",
        "rls_organization_membership_write",
        _ORG_EQ,
        _ORG_EQ,
    )

    for table in sorted(GLOBAL_TABLES):
        _policy_select(table, f"rls_{table}_select", _ACTOR)

    _policy_select("knowledge_source", "rls_knowledge_source_select", _KNOWLEDGE_READ)
    _policy_write("knowledge_source", "rls_knowledge_source_write", _ORG_EQ, _ORG_EQ)
    _policy_select("knowledge_source_version", "rls_knowledge_source_version_select", _KNOWLEDGE_CHILD_READ)
    _policy_write("knowledge_source_version", "rls_knowledge_source_version_write", _ORG_EQ, _ORG_EQ)
    _policy_select("knowledge_fragment", "rls_knowledge_fragment_select", _FRAGMENT_READ)
    _policy_write("knowledge_fragment", "rls_knowledge_fragment_write", _ORG_EQ, _ORG_EQ)

    for table in (
        "nutrition_expectation_profile",
        "compliance_framework",
        "compliance_framework_version",
        "compliance_requirement",
        "compliance_requirement_source",
    ):
        _policy_select(table, f"rls_{table}_select", _HYBRID_CATALOG_READ)
        _policy_write(table, f"rls_{table}_write", _ORG_EQ, _ORG_EQ)

    _policy_select("grounding_query", "rls_grounding_query_select", _GROUNDING_READ)
    _policy_write("grounding_query", "rls_grounding_query_write", _ORG_EQ, _ORG_EQ)

    _policy_select("audit_event", "rls_audit_event_select", _AUDIT_READ)
    op.execute(
        f"CREATE POLICY rls_audit_event_insert ON audit_event FOR INSERT WITH CHECK ({_AUDIT_WRITE})"
    )

    op.execute(
        """
        CREATE POLICY rls_supplier_item_price_all ON supplier_item_price FOR ALL
        USING (
          EXISTS (
            SELECT 1 FROM supplier_item si
            WHERE si.id = supplier_item_price.supplier_item_id
              AND si.organization_id = panne_current_org_id()
          )
        )
        WITH CHECK (
          EXISTS (
            SELECT 1 FROM supplier_item si
            WHERE si.id = supplier_item_price.supplier_item_id
              AND si.organization_id = panne_current_org_id()
          )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_knowledge_source_tag_select ON knowledge_source_tag FOR SELECT
        USING (
          EXISTS (
            SELECT 1 FROM knowledge_source ks
            WHERE ks.id = knowledge_source_tag.knowledge_source_id
              AND (
                (ks.organization_id IS NOT NULL AND ks.organization_id = panne_current_org_id())
                OR (ks.organization_id IS NULL AND ks.release_state = 'released'
                    AND panne_current_user_id() IS NOT NULL)
              )
          )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_knowledge_source_tag_write ON knowledge_source_tag FOR ALL
        USING (
          EXISTS (
            SELECT 1 FROM knowledge_source ks
            WHERE ks.id = knowledge_source_tag.knowledge_source_id
              AND ks.organization_id = panne_current_org_id()
          )
        )
        WITH CHECK (
          EXISTS (
            SELECT 1 FROM knowledge_source ks
            WHERE ks.id = knowledge_source_tag.knowledge_source_id
              AND ks.organization_id = panne_current_org_id()
          )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_nutrition_expectation_profile_item_select
        ON nutrition_expectation_profile_item FOR SELECT
        USING (
          EXISTS (
            SELECT 1 FROM nutrition_expectation_profile p
            WHERE p.id = nutrition_expectation_profile_item.profile_id
              AND (
                (p.organization_id IS NOT NULL AND p.organization_id = panne_current_org_id())
                OR (p.organization_id IS NULL AND panne_current_user_id() IS NOT NULL)
              )
          )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_nutrition_expectation_profile_item_write
        ON nutrition_expectation_profile_item FOR ALL
        USING (
          EXISTS (
            SELECT 1 FROM nutrition_expectation_profile p
            WHERE p.id = nutrition_expectation_profile_item.profile_id
              AND p.organization_id = panne_current_org_id()
          )
        )
        WITH CHECK (
          EXISTS (
            SELECT 1 FROM nutrition_expectation_profile p
            WHERE p.id = nutrition_expectation_profile_item.profile_id
              AND p.organization_id = panne_current_org_id()
          )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_grounding_result_all ON grounding_result FOR ALL
        USING (
          EXISTS (
            SELECT 1 FROM grounding_query q
            WHERE q.id = grounding_result.grounding_query_id
              AND q.organization_id = panne_current_org_id()
          )
        )
        WITH CHECK (
          EXISTS (
            SELECT 1 FROM grounding_query q
            WHERE q.id = grounding_result.grounding_query_id
              AND q.organization_id = panne_current_org_id()
          )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_grounding_citation_all ON grounding_citation FOR ALL
        USING (
          EXISTS (
            SELECT 1 FROM grounding_result r
            JOIN grounding_query q ON q.id = r.grounding_query_id
            WHERE r.id = grounding_citation.grounding_result_id
              AND q.organization_id = panne_current_org_id()
          )
        )
        WITH CHECK (
          EXISTS (
            SELECT 1 FROM grounding_result r
            JOIN grounding_query q ON q.id = r.grounding_query_id
            WHERE r.id = grounding_citation.grounding_result_id
              AND q.organization_id = panne_current_org_id()
          )
        )
        """
    )

    assert IDENTITY_TABLES <= PRE_PRODUCTION_RLS_TABLES
    assert HYBRID_TABLES <= PRE_PRODUCTION_RLS_TABLES
    assert INHERITED_TABLES <= PRE_PRODUCTION_RLS_TABLES


def downgrade() -> None:
    bind = op.get_bind()
    policies = bind.execute(
        sa.text(
            "SELECT tablename, policyname FROM pg_policies WHERE schemaname = 'public'"
        )
    ).fetchall()
    for table, name in policies:
        op.execute(f'DROP POLICY IF EXISTS {name} ON {table}')
    for table in sorted(PRE_PRODUCTION_RLS_TABLES):
        _drop_rls(table)
    op.execute("DROP FUNCTION IF EXISTS panne_current_org_id()")
    op.execute("DROP FUNCTION IF EXISTS panne_current_user_id()")
    op.execute(
        "DELETE FROM organization_membership WHERE role NOT IN "
        "('owner','administrator','technical_responsible','production','commercial','viewer')"
    )
    op.drop_constraint("ck_membership_role", "organization_membership", type_="check")
    op.create_check_constraint("ck_membership_role", "organization_membership", _OLD_ROLES)
    op.drop_table("role_permission")
    op.drop_table("permission")
    op.drop_table("auth_identity")
