"""Concessão e revogação auditadas de papéis. Grupos do IdP não autorizam."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.authorization import (
    MEMBERSHIP_ROLES,
    PERMISSION_MEMBERSHIP_ROLE_MANAGE,
    AuthorizationError,
    Principal,
    require_permission,
)
from app.modules.identity_organization.models import (
    OrganizationMembership,
    OrganizationMembershipRole,
)
from app.modules.identity_organization.services import record_audit
from app.modules.production_planning.errors import InvalidStateError, ValidationError

OWNER_ROLES = frozenset({"owner", "organization_owner"})
ADMIN_ROLES = OWNER_ROLES | frozenset({"administrator", "organization_admin"})


def _now() -> datetime:
    return datetime.now(UTC)


def _selected_roles(principal: Principal) -> frozenset[str]:
    if principal.selected is None:
        raise AuthorizationError("organizacao_nao_selecionada")
    return frozenset(principal.selected.roles)


def _can_assign(actor_roles: frozenset[str], target_role: str) -> bool:
    if target_role in OWNER_ROLES:
        return bool(actor_roles & OWNER_ROLES)
    if target_role in ADMIN_ROLES:
        return bool(actor_roles & ADMIN_ROLES)
    return bool(actor_roles & ADMIN_ROLES)


def _active_roles(
    session: Session, membership_id: UUID
) -> list[OrganizationMembershipRole]:
    return list(
        session.scalars(
            select(OrganizationMembershipRole)
            .where(
                OrganizationMembershipRole.membership_id == membership_id,
                OrganizationMembershipRole.revoked_at.is_(None),
            )
            .order_by(OrganizationMembershipRole.granted_at)
        )
    )


def _active_owner_count(session: Session, organization_id: UUID) -> int:
    return len(
        list(
            session.scalars(
                select(OrganizationMembershipRole.id)
                .join(
                    OrganizationMembership,
                    OrganizationMembership.id == OrganizationMembershipRole.membership_id,
                )
                .where(
                    OrganizationMembershipRole.organization_id == organization_id,
                    OrganizationMembershipRole.revoked_at.is_(None),
                    OrganizationMembershipRole.role.in_(tuple(OWNER_ROLES)),
                    OrganizationMembership.status == "active",
                )
            )
        )
    )


def grant_role(
    session: Session,
    principal: Principal,
    *,
    membership_id: UUID,
    role: str,
    reason: str,
    correlation_id: UUID | None = None,
) -> OrganizationMembershipRole:
    require_permission(principal, PERMISSION_MEMBERSHIP_ROLE_MANAGE)
    if principal.selected is None:
        raise AuthorizationError("organizacao_nao_selecionada")
    organization_id = principal.selected.organization_id
    if role not in MEMBERSHIP_ROLES:
        raise ValidationError("papel inválido")
    if not reason or not reason.strip():
        raise ValidationError("motivo obrigatório")
    if not _can_assign(_selected_roles(principal), role):
        raise AuthorizationError("escalada_indevida")
    membership = session.get(OrganizationMembership, membership_id)
    if membership is None or membership.organization_id != organization_id:
        raise ValidationError("associação inválida")
    if membership.status != "active":
        raise InvalidStateError("associacao_inativa")
    existing = session.scalar(
        select(OrganizationMembershipRole).where(
            OrganizationMembershipRole.membership_id == membership.id,
            OrganizationMembershipRole.role == role,
            OrganizationMembershipRole.revoked_at.is_(None),
        )
    )
    if existing is not None:
        return existing
    row = OrganizationMembershipRole(
        organization_id=organization_id,
        membership_id=membership.id,
        role=role,
        granted_by_user_id=principal.user_id,
        granted_at=_now(),
        reason=reason.strip(),
    )
    session.add(row)
    session.flush()
    record_audit(
        session,
        event_type="membership.role.granted",
        aggregate_type="organization_membership",
        aggregate_id=membership.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        correlation_id=correlation_id,
        payload={"role": role, "membership_role_id": str(row.id)},
    )
    return row


def revoke_role(
    session: Session,
    principal: Principal,
    *,
    membership_id: UUID,
    role: str,
    reason: str,
    correlation_id: UUID | None = None,
) -> OrganizationMembershipRole:
    require_permission(principal, PERMISSION_MEMBERSHIP_ROLE_MANAGE)
    if principal.selected is None:
        raise AuthorizationError("organizacao_nao_selecionada")
    organization_id = principal.selected.organization_id
    if role not in MEMBERSHIP_ROLES:
        raise ValidationError("papel inválido")
    if not reason or not reason.strip():
        raise ValidationError("motivo obrigatório")
    if not _can_assign(_selected_roles(principal), role):
        raise AuthorizationError("escalada_indevida")
    membership = session.get(OrganizationMembership, membership_id)
    if membership is None or membership.organization_id != organization_id:
        raise ValidationError("associação inválida")
    row = session.scalar(
        select(OrganizationMembershipRole).where(
            OrganizationMembershipRole.membership_id == membership.id,
            OrganizationMembershipRole.role == role,
            OrganizationMembershipRole.revoked_at.is_(None),
        )
    )
    if row is None:
        raise ValidationError("papel ativo inexistente")
    active = _active_roles(session, membership.id)
    if len(active) == 1 and active[0].id == row.id:
        raise InvalidStateError("ultimo_papel_ativo")
    if role in OWNER_ROLES and _active_owner_count(session, organization_id) <= 1:
        raise InvalidStateError("ultimo_proprietario")
    row.revoked_at = _now()
    row.revoked_by_user_id = principal.user_id
    row.reason = reason.strip()
    session.flush()
    record_audit(
        session,
        event_type="membership.role.revoked",
        aggregate_type="organization_membership",
        aggregate_id=membership.id,
        organization_id=organization_id,
        actor_user_id=principal.user_id,
        correlation_id=correlation_id,
        payload={"role": role, "membership_role_id": str(row.id)},
    )
    return row
