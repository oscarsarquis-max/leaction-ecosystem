"""Código reutilizável. O teste conserva o valor só para conferir o provedor falso."""

import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity_organization.access_code import (
    MemoryDirectory,
    MemoryMailer,
    confirm_code_change,
    generate_access_code,
    issue_first_code,
    request_code_change,
    revoke_access_code,
)
from app.modules.identity_organization.models import AuditEvent
from app.modules.identity_organization.onboarding import issue_onboarding_authorization


@pytest.fixture(scope="module", autouse=True)
def _schema(engine) -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def _pepper(monkeypatch) -> None:
    monkeypatch.setenv("PANNE_ACCESS_CODE_PEPPER", "teste-de-confirmacao-16")


def _grant(db_session: Session, email: str) -> None:
    issue_onboarding_authorization(db_session, email=email, commercial_condition="complimentary", valid_hours=2)


def _ports() -> tuple[MemoryDirectory, MemoryMailer]:
    return MemoryDirectory(codes={}, disabled=set(), sessions_revoked=set()), MemoryMailer([], [])


def test_code_strength() -> None:
    code = generate_access_code()
    assert len(code) == 20
    assert any(character.islower() for character in code)
    assert any(character.isupper() for character in code)
    assert any(character.isdigit() for character in code)
    assert any(not character.isalnum() for character in code)


def test_first_code_is_sent_once_and_reused(db_session: Session) -> None:
    email = f"um-{uuid4().hex[:8]}@example.invalid"
    _grant(db_session, email)
    directory, mailer = _ports()
    assert issue_first_code(db_session, email, directory, mailer) == "issued"
    assert issue_first_code(db_session, email, directory, mailer) == "unchanged"
    assert len(mailer.sent_codes) == 1
    code = mailer.sent_codes[0][1]
    assert directory.accepts(email, code)
    payload = db_session.scalars(select(AuditEvent).where(AuditEvent.event_type == "access_code.issued")).all()
    assert payload
    assert code not in str(payload[-1].payload)


def test_two_people_receive_different_codes(db_session: Session) -> None:
    first = f"a-{uuid4().hex[:8]}@example.invalid"
    second = f"b-{uuid4().hex[:8]}@example.invalid"
    _grant(db_session, first)
    _grant(db_session, second)
    directory, mailer = _ports()
    issue_first_code(db_session, first, directory, mailer)
    issue_first_code(db_session, second, directory, mailer)
    assert directory.codes[first] != directory.codes[second]
    assert directory.accepts(first, directory.codes[first])
    assert not directory.accepts(first, directory.codes[second])


def test_unknown_email_does_not_send(db_session: Session) -> None:
    directory, mailer = _ports()
    assert issue_first_code(db_session, f"ninguem-{uuid4().hex[:8]}@example.invalid", directory, mailer) == "ineligible"
    assert mailer.sent_codes == []


def test_change_replaces_the_code_and_locks_attempts(db_session: Session) -> None:
    email = f"troca-{uuid4().hex[:8]}@example.invalid"
    _grant(db_session, email)
    directory, mailer = _ports()
    issue_first_code(db_session, email, directory, mailer)
    previous = directory.codes[email]
    request_code_change(db_session, email, mailer)
    request_code_change(db_session, email, mailer)
    assert len(mailer.sent_confirmations) == 1
    confirmation = mailer.sent_confirmations[0][1]
    assert confirmation != previous
    assert confirm_code_change(db_session, email, "errado-demais", directory, mailer) is False
    for _ in range(4):
        assert confirm_code_change(db_session, email, "errado-demais", directory, mailer) is False
    assert confirm_code_change(db_session, email, confirmation, directory, mailer) is False
    assert directory.accepts(email, previous)
    assert len(mailer.sent_codes) == 1


def test_confirmed_change_invalidates_the_previous_code(db_session: Session) -> None:
    email = f"nova-{uuid4().hex[:8]}@example.invalid"
    _grant(db_session, email)
    directory, mailer = _ports()
    issue_first_code(db_session, email, directory, mailer)
    previous = directory.codes[email]
    request_code_change(db_session, email, mailer)
    confirmation = mailer.sent_confirmations[0][1]
    assert confirm_code_change(db_session, email, confirmation, directory, mailer) is True
    assert not directory.accepts(email, previous)
    replacement = mailer.sent_codes[-1][1]
    assert replacement != previous
    assert mailer.sent_codes[-1][2] is True
    assert directory.accepts(email, replacement)
    changed = db_session.scalars(select(AuditEvent).where(AuditEvent.event_type == "access_code.changed")).all()
    assert replacement not in str(changed[-1].payload)
    assert previous not in str(changed[-1].payload)


def test_revocation_blocks_the_code(db_session: Session) -> None:
    email = f"fim-{uuid4().hex[:8]}@example.invalid"
    _grant(db_session, email)
    directory, mailer = _ports()
    issue_first_code(db_session, email, directory, mailer)
    code = directory.codes[email]
    assert revoke_access_code(db_session, email, directory) == "revoked"
    assert not directory.accepts(email, code)
    assert email in directory.sessions_revoked
    assert issue_first_code(db_session, email, directory, mailer) == "ineligible"
