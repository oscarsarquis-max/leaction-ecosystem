from uuid import uuid4

import pytest
from app.modules.identity_organization.authorization import (
    PERMISSION_MEMBERSHIP_ROLE_MANAGE,
    PERMISSION_PRODUCTION_ORDER_MANAGE,
    PERMISSION_PRODUCTION_WEIGHING_RECORD,
    AuthorizationError,
    permissions_for_role,
)
from app.modules.identity_organization.models import OrganizationMembershipRole
from app.modules.identity_organization.roles import grant_role, revoke_role
from app.modules.production_planning.errors import InvalidStateError
from sqlalchemy import select
from sqlalchemy.orm import Session
from tests import helpers


def test_membership_migrates_to_role_row(db_session: Session) -> None:
    organization = helpers.org(db_session, f"role-mig-{uuid4().hex[:8]}")
    actor = helpers.user(db_session, f"role-mig-{uuid4().hex[:8]}@example.com")
    membership = helpers.membership(db_session, organization, actor, "owner")
    rows = list(
        db_session.scalars(
            select(OrganizationMembershipRole).where(
                OrganizationMembershipRole.membership_id == membership.id,
                OrganizationMembershipRole.revoked_at.is_(None),
            )
        )
    )
    assert [row.role for row in rows] == ["owner"]


def test_grant_unions_permissions_and_keeps_history(db_session: Session) -> None:
    organization = helpers.org(db_session, f"role-un-{uuid4().hex[:8]}")
    actor = helpers.user(db_session, f"role-un-{uuid4().hex[:8]}@example.com")
    target = helpers.user(db_session, f"role-tg-{uuid4().hex[:8]}@example.com")
    helpers.membership(db_session, organization, actor, "owner")
    membership = helpers.membership(db_session, organization, target, "baker_operator")
    principal = helpers.principal_for(actor, organization, "owner")
    granted = grant_role(
        db_session,
        principal,
        membership_id=membership.id,
        role="viewer",
        reason="cobertura de leitura",
    )
    assert granted.role == "viewer"
    assert granted.revoked_at is None
    union = permissions_for_role("baker_operator") | permissions_for_role("viewer")
    assert PERMISSION_PRODUCTION_WEIGHING_RECORD in union
    assert PERMISSION_PRODUCTION_ORDER_MANAGE not in union
    revoke_role(
        db_session,
        principal,
        membership_id=membership.id,
        role="viewer",
        reason="fim da cobertura",
    )
    db_session.refresh(granted)
    assert granted.revoked_at is not None


def test_last_owner_and_escalation_are_blocked(db_session: Session) -> None:
    organization = helpers.org(db_session, f"role-own-{uuid4().hex[:8]}")
    owner = helpers.user(db_session, f"role-ow-{uuid4().hex[:8]}@example.com")
    baker = helpers.user(db_session, f"role-bk-{uuid4().hex[:8]}@example.com")
    owner_membership = helpers.membership(db_session, organization, owner, "owner")
    baker_membership = helpers.membership(db_session, organization, baker, "baker_operator")
    owner_principal = helpers.principal_for(owner, organization, "owner")
    baker_principal = helpers.principal_for(baker, organization, "baker_operator")
    grant_role(
        db_session,
        owner_principal,
        membership_id=owner_membership.id,
        role="viewer",
        reason="papel extra",
    )
    with pytest.raises(InvalidStateError, match="ultimo_proprietario"):
        revoke_role(
            db_session,
            owner_principal,
            membership_id=owner_membership.id,
            role="owner",
            reason="tentativa",
        )
    with pytest.raises(AuthorizationError):
        grant_role(
            db_session,
            baker_principal,
            membership_id=baker_membership.id,
            role="owner",
            reason="escalada",
        )
    admin = helpers.user(db_session, f"role-ad-{uuid4().hex[:8]}@example.com")
    helpers.membership(db_session, organization, admin, "administrator")
    admin_principal = helpers.principal_for(admin, organization, "administrator")
    assert PERMISSION_MEMBERSHIP_ROLE_MANAGE in admin_principal.permissions
    with pytest.raises(AuthorizationError, match="escalada_indevida"):
        grant_role(
            db_session,
            admin_principal,
            membership_id=baker_membership.id,
            role="owner",
            reason="escalada admin",
        )
