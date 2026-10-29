from uuid import uuid4

from app.modules.identity_organization.access_tokens import VerifiedAccessToken
from app.modules.identity_organization.authorization import (
    PERMISSION_MEMBERSHIP_ROLE_MANAGE,
    PERMISSION_PRODUCTION_PLAN_MANAGE,
)
from app.modules.identity_organization.models import OrganizationMembershipRole
from app.modules.identity_organization.services import load_principal
from sqlalchemy import delete
from sqlalchemy.orm import Session
from tests import helpers
from tests.jwt_support import ISSUER


def _token(subject: str) -> VerifiedAccessToken:
    return VerifiedAccessToken(
        issuer=ISSUER,
        subject=subject,
        client_id="test-client",
        scopes=frozenset(),
        raw_claims={},
    )


def test_legacy_label_does_not_grant_permission(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    organization = helpers.org(db_session, f"lbl-{suffix}")
    actor = helpers.user(db_session, f"lbl-{suffix}@example.com")
    membership = helpers.membership(db_session, organization, actor, "viewer")
    subject = f"sub-lbl-{suffix}"
    identity = helpers.auth_identity(db_session, actor, ISSUER, subject)
    membership.legacy_role_label = "owner"
    db_session.flush()

    principal = load_principal(db_session, identity, _token(subject), organization.id)
    assert principal.selected is not None
    assert principal.selected.roles == ("viewer",)
    assert PERMISSION_MEMBERSHIP_ROLE_MANAGE not in principal.permissions
    assert PERMISSION_PRODUCTION_PLAN_MANAGE not in principal.permissions
    assert membership.legacy_role_label == "owner"


def test_membership_without_active_roles_has_no_permissions(db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    organization = helpers.org(db_session, f"empty-{suffix}")
    actor = helpers.user(db_session, f"empty-{suffix}@example.com")
    membership = helpers.membership(db_session, organization, actor, "owner")
    subject = f"sub-empty-{suffix}"
    identity = helpers.auth_identity(db_session, actor, ISSUER, subject)
    db_session.execute(
        delete(OrganizationMembershipRole).where(
            OrganizationMembershipRole.membership_id == membership.id
        )
    )
    db_session.flush()

    principal = load_principal(db_session, identity, _token(subject), None)
    assert principal.selected is None
    assert principal.associations[0].roles == ()
    assert principal.permissions == frozenset()
