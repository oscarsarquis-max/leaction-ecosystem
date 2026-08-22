"""Resolução de identidade interna e bootstrap explícito. Sem autocadastro."""

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.modules.identity_organization.access_tokens import VerifiedAccessToken
from app.modules.identity_organization.authorization import (
    Association,
    AuthorizationError,
    Principal,
    permissions_for_role,
)
from app.modules.identity_organization.models import (
    AppUser,
    AuditEvent,
    AuthIdentity,
    Organization,
    OrganizationMembership,
    OrganizationMembershipRole,
)


class IdentityResolutionError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _associations_of(
    rows: list[OrganizationMembership],
    roles_by_membership: dict[UUID, tuple[str, ...]],
    organizations: dict[UUID, Organization],
) -> tuple[Association, ...]:
    associations = []
    for row in rows:
        if row.status != "active":
            continue
        roles = roles_by_membership.get(row.id) or ()
        permissions: set[str] = set()
        for role in roles:
            permissions.update(permissions_for_role(role))
        organization = organizations.get(row.organization_id)
        associations.append(
            Association(
                organization_id=row.organization_id,
                status=row.status,
                permissions=frozenset(permissions),
                roles=roles,
                organization_display_name=organization.display_name if organization else "",
                organization_slug=organization.slug if organization else "",
            )
        )
    return tuple(associations)


def _roles_by_membership(
    rows: list[OrganizationMembershipRole],
) -> dict[UUID, tuple[str, ...]]:
    grouped: dict[UUID, list[str]] = {}
    for row in rows:
        grouped.setdefault(row.membership_id, []).append(row.role)
    return {key: tuple(value) for key, value in grouped.items()}


def _principal(
    user: AppUser,
    token: VerifiedAccessToken,
    memberships: list[OrganizationMembership],
    selected_org: UUID | None,
    role_rows: list[OrganizationMembershipRole],
    organizations: dict[UUID, Organization],
) -> Principal:
    if user.status != "active":
        raise IdentityResolutionError("usuario_inativo")
    associations = _associations_of(memberships, _roles_by_membership(role_rows), organizations)
    if not associations:
        raise IdentityResolutionError("sem_associacao")
    selected = None
    if selected_org is not None:
        selected = next(
            (item for item in associations if item.organization_id == selected_org),
            None,
        )
        if selected is None:
            raise IdentityResolutionError("sem_associacao")
    return Principal(
        user_id=user.id,
        display_name=user.display_name,
        status=user.status,
        issuer=token.issuer,
        subject=token.subject,
        associations=associations,
        selected=selected,
    )


def lookup_identity(session: Session, token: VerifiedAccessToken) -> AuthIdentity:
    identity = session.scalar(
        select(AuthIdentity).where(
            AuthIdentity.issuer == token.issuer,
            AuthIdentity.subject == token.subject,
            AuthIdentity.status == "active",
        )
    )
    if identity is None:
        raise IdentityResolutionError("identidade_desconhecida")
    return identity


async def lookup_identity_async(session: AsyncSession, token: VerifiedAccessToken) -> AuthIdentity:
    identity = (
        await session.execute(
            select(AuthIdentity).where(
                AuthIdentity.issuer == token.issuer,
                AuthIdentity.subject == token.subject,
                AuthIdentity.status == "active",
            )
        )
    ).scalar_one_or_none()
    if identity is None:
        raise IdentityResolutionError("identidade_desconhecida")
    return identity


def load_principal(
    session: Session,
    identity: AuthIdentity,
    token: VerifiedAccessToken,
    requested_organization_id: UUID | None,
) -> Principal:
    user = session.get(AppUser, identity.user_id)
    if user is None:
        raise IdentityResolutionError("usuario_inativo")
    memberships = list(
        session.scalars(
            select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
        )
    )
    role_rows = []
    organizations: dict[UUID, Organization] = {}
    if memberships:
        role_rows = list(
            session.scalars(
                select(OrganizationMembershipRole)
                .where(
                    OrganizationMembershipRole.membership_id.in_(
                        [row.id for row in memberships]
                    ),
                    OrganizationMembershipRole.revoked_at.is_(None),
                )
                .order_by(OrganizationMembershipRole.granted_at)
            )
        )
        org_ids = [row.organization_id for row in memberships]
        organizations = {
            item.id: item
            for item in session.scalars(select(Organization).where(Organization.id.in_(org_ids)))
        }
    return _principal(
        user, token, memberships, requested_organization_id, role_rows, organizations
    )


async def load_principal_async(
    session: AsyncSession,
    identity: AuthIdentity,
    token: VerifiedAccessToken,
    requested_organization_id: UUID | None,
) -> Principal:
    user = await session.get(AppUser, identity.user_id)
    if user is None:
        raise IdentityResolutionError("usuario_inativo")
    memberships = list(
        (
            await session.execute(
                select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
            )
        ).scalars()
    )
    role_rows = []
    organizations: dict[UUID, Organization] = {}
    if memberships:
        role_rows = list(
            (
                await session.execute(
                    select(OrganizationMembershipRole)
                    .where(
                        OrganizationMembershipRole.membership_id.in_(
                            [row.id for row in memberships]
                        ),
                        OrganizationMembershipRole.revoked_at.is_(None),
                    )
                    .order_by(OrganizationMembershipRole.granted_at)
                )
            ).scalars()
        )
        org_ids = [row.organization_id for row in memberships]
        organizations = {
            item.id: item
            for item in (
                await session.execute(select(Organization).where(Organization.id.in_(org_ids)))
            ).scalars()
        }
    return _principal(
        user, token, memberships, requested_organization_id, role_rows, organizations
    )


def record_audit(
    session: Session | AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    organization_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    correlation_id: UUID | None = None,
    payload: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        correlation_id=correlation_id,
        payload=payload or {},
    )
    session.add(event)
    return event


def bootstrap_first_owner(
    session: Session,
    *,
    issuer: str,
    subject: str,
    email: str,
    display_name: str,
    organization_slug: str,
    legal_name: str,
    organization_display_name: str | None = None,
    role: str = "owner",
) -> tuple[Organization, AppUser, OrganizationMembership, AuthIdentity]:
    """Cria o primeiro proprietário. Somente sessão administrativa. Sem HTTP."""
    if not issuer.strip() or not subject.strip():
        raise IdentityResolutionError("identidade_invalida")
    existing = session.scalar(
        select(AuthIdentity).where(AuthIdentity.issuer == issuer, AuthIdentity.subject == subject)
    )
    if existing is not None:
        raise IdentityResolutionError("identidade_ja_vinculada")
    organization = Organization(
        slug=organization_slug,
        legal_name=legal_name,
        display_name=organization_display_name or organization_slug,
        status="active",
    )
    user = AppUser(email=email, display_name=display_name, status="active")
    session.add_all([organization, user])
    session.flush()
    membership = OrganizationMembership(
        organization_id=organization.id,
        user_id=user.id,
        legacy_role_label=role,
        status="active",
    )
    identity = AuthIdentity(
        user_id=user.id,
        issuer=issuer,
        subject=subject,
        status="active",
    )
    session.add_all([membership, identity])
    session.flush()
    session.add(
        OrganizationMembershipRole(
            organization_id=organization.id,
            membership_id=membership.id,
            role=role,
            granted_by_user_id=user.id,
            reason="bootstrap",
        )
    )
    session.flush()
    record_audit(
        session,
        event_type="identity.linked",
        aggregate_type="auth_identity",
        aggregate_id=identity.id,
        organization_id=organization.id,
        actor_user_id=user.id,
        payload={"bootstrap": True},
    )
    return organization, user, membership, identity


def parse_organization_header(value: str | None) -> UUID | None:
    if value is None or not value.strip():
        return None
    try:
        return UUID(value.strip())
    except ValueError as exc:
        raise AuthorizationError("organizacao_invalida") from exc


def new_correlation_id(header: str | None) -> UUID:
    if header:
        try:
            return UUID(header.strip())
        except ValueError:
            pass
    return uuid4()
