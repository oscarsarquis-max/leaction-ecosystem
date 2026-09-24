"""Credencial de acesso reutilizável. Não armazena o código.

Revision ID: 0028_access_credential
Revises: 0027_client_onboarding
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028_access_credential"
down_revision: str | Sequence[str] | None = "0027_client_onboarding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "access_credential",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email_normalized", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_hash", sa.Text(), nullable=True),
        sa.Column("confirmation_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmation_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active','revoked')", name="ck_access_credential_status"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_access_credential_email", "access_credential", ["email_normalized"], unique=True)
    op.execute("ALTER TABLE access_credential ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE access_credential FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY rls_access_credential_self ON access_credential
        FOR SELECT USING (
          panne_actor_email() IS NOT NULL
          AND email_normalized = panne_actor_email()
        )
        """
    )
    op.execute(
        """
        CREATE POLICY rls_access_credential_self_update ON access_credential
        FOR UPDATE USING (
          panne_actor_email() IS NOT NULL
          AND email_normalized = panne_actor_email()
        )
        WITH CHECK (
          panne_actor_email() IS NOT NULL
          AND email_normalized = panne_actor_email()
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_runtime') THEN
            GRANT SELECT, UPDATE ON access_credential TO panne_runtime;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_prod_runtime') THEN
            GRANT SELECT, UPDATE ON access_credential TO panne_prod_runtime;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'panne_demo_runtime') THEN
            GRANT SELECT, UPDATE ON access_credential TO panne_demo_runtime;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS rls_access_credential_self_update ON access_credential")
    op.execute("DROP POLICY IF EXISTS rls_access_credential_self ON access_credential")
    op.execute("DROP TABLE IF EXISTS access_credential")
