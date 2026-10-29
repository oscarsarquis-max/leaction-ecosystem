import pytest
from app.modules.identity_organization.models import (
    AppUser,
    AuditEvent,
    Establishment,
    Organization,
)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests import helpers


def test_organization_slug_unique(db_session: Session) -> None:
    helpers.org(db_session, "padaria-norte")
    db_session.add(
        Organization(
            slug="padaria-norte",
            legal_name="outra",
            display_name="outra",
            status="active",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_establishment_code_unique_per_organization(db_session: Session) -> None:
    one = helpers.org(db_session, "org-a")
    two = helpers.org(db_session, "org-b")
    db_session.add(
        Establishment(organization_id=one.id, code="MATRIZ", display_name="Matriz", status="active")
    )
    db_session.flush()
    db_session.add(
        Establishment(
            organization_id=two.id, code="MATRIZ", display_name="Matriz B", status="active"
        )
    )
    db_session.flush()
    db_session.add(
        Establishment(organization_id=one.id, code="MATRIZ", display_name="dup", status="active")
    )
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_membership_unique_per_user_and_organization(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-memb")
    person = helpers.user(db_session, "dono@example.com")
    helpers.membership(db_session, organization, person)
    with pytest.raises(IntegrityError):
        helpers.membership(db_session, organization, person, role="viewer")


def test_email_unique_case_insensitive(db_session: Session) -> None:
    helpers.user(db_session, "Ana@Example.com")
    db_session.add(AppUser(email="ana@example.com", display_name="Ana", status="active"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_audit_event_append_only(db_session: Session) -> None:
    organization = helpers.org(db_session, "org-audit")
    event = AuditEvent(
        organization_id=organization.id,
        event_type="organization.created",
        aggregate_type="organization",
        aggregate_id=organization.id,
        payload={"slug": "org-audit"},
    )
    db_session.add(event)
    db_session.flush()
    with pytest.raises(Exception, match="append_only"):
        db_session.execute(
            text("UPDATE audit_event SET event_type = 'x' WHERE id = :id"),
            {"id": event.id},
        )
        db_session.flush()
