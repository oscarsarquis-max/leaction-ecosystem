"""Fundação multiempresa, identidade externa e autorização interna."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Index, Text, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid_pk():
    return mapped_column(Uuid, primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


def _updated_at():
    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Organization(Base):
    __tablename__ = "organization"
    __table_args__ = (Index("uq_organization_slug", "slug", unique=True),)

    id: Mapped[UUID] = _uuid_pk()
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    holder_kind: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'legal_entity'"))
    holder_name: Mapped[str | None] = mapped_column(Text)
    holder_fiscal_id_type: Mapped[str | None] = mapped_column(Text)
    holder_fiscal_id: Mapped[str | None] = mapped_column(Text)
    fiscal_id_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'not_recorded'")
    )
    formalization_state: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'unspecified'")
    )
    commercial_condition: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'unspecified'")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class Establishment(Base):
    __tablename__ = "establishment"
    __table_args__ = (
        Index("uq_establishment_org_code", "organization_id", "code", unique=True),
        Index("uq_establishment_id_org", "id", "organization_id", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    nature: Mapped[str | None] = mapped_column(Text)
    capabilities: Mapped[list | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class AppUser(Base):
    """Identidade global. Nome `app_user` para não usar a palavra reservada `user`."""

    __tablename__ = "app_user"
    __table_args__ = (Index("uq_app_user_email_lower", text("lower(email)"), unique=True),)

    id: Mapped[UUID] = _uuid_pk()
    email: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class OrganizationMembership(Base):
    __tablename__ = "organization_membership"
    __table_args__ = (
        Index("uq_membership_org_user", "organization_id", "user_id", unique=True),
        Index("uq_membership_id_org", "id", "organization_id", unique=True),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    legacy_role_label: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class OrganizationMembershipRole(Base):
    __tablename__ = "organization_membership_role"
    __table_args__ = (
        Index("uq_membership_role_id_org", "id", "organization_id", unique=True),
        Index(
            "uq_membership_role_active",
            "membership_id",
            "role",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
        ForeignKeyConstraint(
            ["membership_id", "organization_id"],
            ["organization_membership.id", "organization_membership.organization_id"],
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    membership_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    granted_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(Text)


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT")
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT")
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    aggregate_type: Mapped[str] = mapped_column(Text, nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    correlation_id: Mapped[UUID | None] = mapped_column(Uuid)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))


class AuthIdentity(Base):
    """Vínculo único issuer + subject (opaco) → app_user. Sem senha local."""

    __tablename__ = "auth_identity"
    __table_args__ = (Index("uq_auth_identity_issuer_subject", "issuer", "subject", unique=True),)

    id: Mapped[UUID] = _uuid_pk()
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("app_user.id", ondelete="RESTRICT"), nullable=False
    )
    issuer: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _updated_at()


class OnboardingAuthorization(Base):
    """Autorização individual da Panne para abrir um cliente. Não é autocadastro."""

    __tablename__ = "onboarding_authorization"
    __table_args__ = (
        Index(
            "uq_onboarding_auth_open_email",
            "email_normalized",
            unique=True,
            postgresql_where=text("status IN ('issued','bound')"),
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    email_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    issuer: Mapped[str | None] = mapped_column(Text)
    subject: Mapped[str | None] = mapped_column(Text)
    commercial_condition: Mapped[str] = mapped_column(Text, nullable=False)
    max_clients: Mapped[int] = mapped_column(nullable=False)
    clients_created: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'issued'"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    organization_id: Mapped[UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = _created_at()


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitation"
    __table_args__ = (
        Index(
            "uq_invitation_open_email",
            "organization_id",
            "email_normalized",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[UUID] = _uuid_pk()
    organization_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("organization.id", ondelete="RESTRICT"), nullable=False
    )
    email_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'pending'"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _created_at()


class Permission(Base):
    __tablename__ = "permission"
    __table_args__ = (Index("uq_permission_code", "code", unique=True),)

    id: Mapped[UUID] = _uuid_pk()
    code: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = _created_at()


class RolePermission(Base):
    __tablename__ = "role_permission"
    __table_args__ = (Index("uq_role_permission", "role", "permission_id", unique=True),)

    id: Mapped[UUID] = _uuid_pk()
    role: Mapped[str] = mapped_column(Text, nullable=False)
    permission_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("permission.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = _created_at()
