"""Autorização de onboarding, titular e convite.

Revision ID: 0027_client_onboarding
Revises: 0026_supply_mode_no_default
Create Date: 2026-09-22

Cadastros anteriores permanecem com formalização não informada e identificador
fiscal não registrado. A migração não inventa CNPJ, CPF nem condição comercial.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0027_client_onboarding"
down_revision: Union[str, Sequence[str], None] = "0026_supply_mode_no_default"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ACTOR_MATCH = """
(
  (
    onboarding_authorization.issuer IS NOT NULL
    AND onboarding_authorization.subject IS NOT NULL
    AND onboarding_authorization.issuer = current_setting('app.current_issuer', true)
    AND onboarding_authorization.subject = current_setting('app.current_subject', true)
  )
  OR (
    onboarding_authorization.issuer IS NULL
    AND panne_actor_email() IS NOT NULL
    AND onboarding_authorization.email_normalized = panne_actor_email()
  )
)
"""

_OPEN_AUTH = f"""
onboarding_authorization.status IN ('issued','bound')
AND onboarding_authorization.expires_at > now()
AND onboarding_authorization.clients_created < onboarding_authorization.max_clients
AND {_ACTOR_MATCH}
"""


def upgrade() -> None:
    op.add_column("organization", sa.Column("holder_kind", sa.Text(), nullable=True))
    op.add_column("organization", sa.Column("holder_name", sa.Text(), nullable=True))
    op.add_column("organization", sa.Column("holder_fiscal_id_type", sa.Text(), nullable=True))
    op.add_column("organization", sa.Column("holder_fiscal_id", sa.Text(), nullable=True))
    op.add_column("organization", sa.Column("fiscal_id_status", sa.Text(), nullable=True))
    op.add_column("organization", sa.Column("formalization_state", sa.Text(), nullable=True))
    op.add_column("organization", sa.Column("commercial_condition", sa.Text(), nullable=True))
    op.alter_column("organization", "legal_name", existing_type=sa.Text(), nullable=True)
    op.execute(
        """
        UPDATE organization
           SET holder_kind = 'legal_entity',
               formalization_state = 'unspecified',
               fiscal_id_status = 'not_recorded',
               commercial_condition = 'unspecified'
         WHERE formalization_state IS NULL
        """
    )
    op.alter_column(
        "organization", "holder_kind", nullable=False, server_default="legal_entity"
    )
    op.alter_column(
        "organization", "fiscal_id_status", nullable=False, server_default="not_recorded"
    )
    op.alter_column(
        "organization", "formalization_state", nullable=False, server_default="unspecified"
    )
    op.alter_column(
        "organization", "commercial_condition", nullable=False, server_default="unspecified"
    )
    op.create_check_constraint(
        "ck_organization_onboarding_shape",
        "organization",
        """
        (
          formalization_state = 'unspecified'
          AND fiscal_id_status = 'not_recorded'
          AND holder_fiscal_id IS NULL
          AND commercial_condition = 'unspecified'
        )
        OR (
          formalization_state = 'formalized'
          AND holder_kind = 'legal_entity'
          AND legal_name IS NOT NULL
          AND btrim(legal_name) <> ''
          AND holder_fiscal_id_type = 'cnpj'
          AND fiscal_id_status = 'recorded'
          AND holder_fiscal_id IS NOT NULL
          AND commercial_condition IN ('complimentary','standard')
        )
        OR (
          formalization_state IN ('not_formalized','self_employed')
          AND holder_kind = 'natural_person'
          AND legal_name IS NULL
          AND holder_fiscal_id_type = 'cpf'
          AND fiscal_id_status = 'recorded'
          AND holder_fiscal_id IS NOT NULL
          AND commercial_condition IN ('complimentary','standard')
        )
        """,
    )

    op.add_column("establishment", sa.Column("nature", sa.Text(), nullable=True))
    op.add_column(
        "establishment",
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_check_constraint(
        "ck_establishment_nature",
        "establishment",
        "nature IS NULL OR nature IN ('integrated','specialized')",
    )

    op.create_table(
        "onboarding_authorization",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email_normalized", sa.Text(), nullable=False),
        sa.Column("issuer", sa.Text(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("commercial_condition", sa.Text(), nullable=False),
        sa.Column("max_clients", sa.Integer(), nullable=False),
        sa.Column("clients_created", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'issued'"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "commercial_condition IN ('complimentary','standard')",
            name="ck_onboarding_auth_condition",
        ),
        sa.CheckConstraint("max_clients >= 1 AND max_clients <= 1", name="ck_onboarding_auth_limit"),
        sa.CheckConstraint("clients_created >= 0", name="ck_onboarding_auth_created"),
        sa.CheckConstraint(
            "status IN ('issued','bound','consumed','revoked','expired')",
            name="ck_onboarding_auth_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_onboarding_auth_open_email",
        "onboarding_authorization",
        ["email_normalized"],
        unique=True,
        postgresql_where=sa.text("status IN ('issued','bound')"),
    )

    op.create_table(
        "organization_invitation",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("email_normalized", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending','accepted','revoked')",
            name="ck_invitation_status",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_invitation_open_email",
        "organization_invitation",
        ["organization_id", "email_normalized"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION panne_actor_email() RETURNS text
        LANGUAGE sql STABLE AS $$
          SELECT nullif(lower(btrim(current_setting('app.current_actor_email', true))), '')
        $$
        """
    )
    for table in ("onboarding_authorization", "organization_invitation"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")

    op.execute(
        f"""
        CREATE POLICY rls_onboarding_authorization_actor
        ON onboarding_authorization FOR SELECT
        USING ({_ACTOR_MATCH})
        """
    )
    op.execute(
        f"""
        CREATE POLICY rls_onboarding_authorization_use
        ON onboarding_authorization FOR UPDATE
        USING ({_OPEN_AUTH})
        WITH CHECK (
          status IN ('issued','bound','consumed')
          AND (
            (
              issuer IS NOT NULL AND subject IS NOT NULL
              AND issuer = current_setting('app.current_issuer', true)
              AND subject = current_setting('app.current_subject', true)
            )
            OR (
              issuer IS NULL AND panne_actor_email() IS NOT NULL
              AND email_normalized = panne_actor_email()
            )
          )
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY rls_organization_onboarding_insert
        ON organization FOR INSERT
        WITH CHECK (EXISTS (SELECT 1 FROM onboarding_authorization WHERE {_OPEN_AUTH}))
        """
    )
    op.execute(
        f"""
        CREATE POLICY rls_app_user_onboarding_insert
        ON app_user FOR INSERT
        WITH CHECK (
          NOT EXISTS (
            SELECT 1 FROM auth_identity ai
            WHERE ai.issuer = current_setting('app.current_issuer', true)
              AND ai.subject = current_setting('app.current_subject', true)
              AND ai.status = 'active'
          )
          AND (
            EXISTS (SELECT 1 FROM onboarding_authorization WHERE {_OPEN_AUTH})
            OR EXISTS (
              SELECT 1 FROM organization_invitation i
              WHERE i.status = 'pending'
                AND i.expires_at > now()
                AND panne_actor_email() IS NOT NULL
                AND i.email_normalized = panne_actor_email()
            )
          )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_auth_identity_onboarding_insert
        ON auth_identity FOR INSERT
        WITH CHECK (
          issuer = current_setting('app.current_issuer', true)
          AND subject = current_setting('app.current_subject', true)
          AND user_id = panne_current_user_id()
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_organization_invitation_select
        ON organization_invitation FOR SELECT
        USING (
          organization_id = panne_current_org_id()
          OR (
            status = 'pending'
            AND expires_at > now()
            AND panne_actor_email() IS NOT NULL
            AND email_normalized = panne_actor_email()
          )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_organization_invitation_insert
        ON organization_invitation FOR INSERT
        WITH CHECK (organization_id = panne_current_org_id())
        """
    )
    op.execute(
        """
        CREATE POLICY rls_organization_owner_update
        ON organization FOR UPDATE
        USING (
          EXISTS (
            SELECT 1 FROM organization_membership m
            JOIN organization_membership_role r ON r.membership_id = m.id
            WHERE m.organization_id = organization.id
              AND m.user_id = panne_current_user_id()
              AND m.status = 'active'
              AND r.role = 'owner'
              AND r.revoked_at IS NULL
          )
        )
        WITH CHECK (
          EXISTS (
            SELECT 1 FROM organization_membership m
            JOIN organization_membership_role r ON r.membership_id = m.id
            WHERE m.organization_id = organization.id
              AND m.user_id = panne_current_user_id()
              AND m.status = 'active'
              AND r.role = 'owner'
              AND r.revoked_at IS NULL
          )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_organization_invitation_update
        ON organization_invitation FOR UPDATE
        USING (
          status = 'pending'
          AND expires_at > now()
          AND panne_actor_email() IS NOT NULL
          AND email_normalized = panne_actor_email()
        )
        WITH CHECK (
          status = 'accepted'
          AND email_normalized = panne_actor_email()
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
            GRANT SELECT, UPDATE ON onboarding_authorization TO panne_runtime;
            GRANT SELECT, INSERT, UPDATE ON organization_invitation TO panne_runtime;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_prod_runtime') THEN
            GRANT SELECT, UPDATE ON onboarding_authorization TO panne_prod_runtime;
            GRANT SELECT, INSERT, UPDATE ON organization_invitation TO panne_prod_runtime;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_demo_runtime') THEN
            GRANT SELECT, UPDATE ON onboarding_authorization TO panne_demo_runtime;
            GRANT SELECT, INSERT, UPDATE ON organization_invitation TO panne_demo_runtime;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    for policy, table in (
        ("rls_organization_invitation_update", "organization_invitation"),
        ("rls_organization_invitation_insert", "organization_invitation"),
        ("rls_organization_invitation_select", "organization_invitation"),
        ("rls_auth_identity_onboarding_insert", "auth_identity"),
        ("rls_app_user_onboarding_insert", "app_user"),
        ("rls_organization_owner_update", "organization"),
        ("rls_organization_onboarding_insert", "organization"),
        ("rls_onboarding_authorization_use", "onboarding_authorization"),
        ("rls_onboarding_authorization_actor", "onboarding_authorization"),
    ):
        op.execute(f"DROP POLICY IF EXISTS {policy} ON {table}")
    op.execute("DROP TABLE IF EXISTS organization_invitation")
    op.execute("DROP TABLE IF EXISTS onboarding_authorization")
    op.execute("DROP FUNCTION IF EXISTS panne_actor_email()")
    op.drop_constraint("ck_establishment_nature", "establishment", type_="check")
    op.drop_column("establishment", "capabilities")
    op.drop_column("establishment", "nature")
    op.drop_constraint("ck_organization_onboarding_shape", "organization", type_="check")
    op.execute("UPDATE organization SET legal_name = display_name WHERE legal_name IS NULL")
    op.alter_column("organization", "legal_name", existing_type=sa.Text(), nullable=False)
    for column in (
        "commercial_condition",
        "formalization_state",
        "fiscal_id_status",
        "holder_fiscal_id",
        "holder_fiscal_id_type",
        "holder_name",
        "holder_kind",
    ):
        op.drop_column("organization", column)
