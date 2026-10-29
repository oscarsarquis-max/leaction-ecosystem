"""Prompt 97 — login isolado. Contas fictícias, sem e-mail real."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.domain.capacity import utc_now
from app.domain.customer_identity import (
    CODE_TTL_MINUTES,
    start_resume,
    start_resume_by_cpf,
    start_signup,
    verify_code,
)
from app.domain.errors import ConfirmationError, RateLimitError
from app.models.customers import CustomerChallenge
from app.models.email_outbox import EmailOutbox
from tests.admin_client import TEST_SESSION_SECRET


def _settings(monkeypatch):
    monkeypatch.setenv("LOJADEPAES_CUSTOMER_IDENTITY_SECRET", TEST_SESSION_SECRET)
    monkeypatch.setenv("LOJADEPAES_ADMIN_SESSION_SECRET", TEST_SESSION_SECRET)
    get_settings.cache_clear()
    return get_settings()


def _force_code(monkeypatch, code: int) -> None:
    monkeypatch.setattr("app.domain.customer_identity.secrets.randbelow", lambda _n: code)


def _outbox_count(db: Session) -> int:
    return int(db.query(EmailOutbox).count())


def _verified_account(db: Session, settings, monkeypatch, email="ana.ficticia@example.com", cpf="390.533.447-05"):
    _force_code(monkeypatch, 101010)
    start_signup(db, settings, "Ana Ficticia", email, cpf)
    return verify_code(db, settings, email, "101010", enroll_fidelity=False)


def test_enter_with_existing_code_does_not_send_again(db: Session, monkeypatch) -> None:
    settings = _settings(monkeypatch)
    _force_code(monkeypatch, 202020)
    start_signup(db, settings, "Ana Ficticia", "ana.ficticia@example.com", "390.533.447-05")
    before = _outbox_count(db)
    account, _token = verify_code(db, settings, "ana.ficticia@example.com", "202020", enroll_fidelity=False)
    assert account.email == "ana.ficticia@example.com"
    assert _outbox_count(db) == before
    get_settings.cache_clear()


def test_enter_by_cpf_uses_registered_email_and_ignores_other_address(db: Session, monkeypatch) -> None:
    settings = _settings(monkeypatch)
    _verified_account(db, settings, monkeypatch)
    _force_code(monkeypatch, 303030)
    start_resume_by_cpf(db, settings, "39053344705")
    before = _outbox_count(db)
    account, _token = verify_code(
        db,
        settings,
        "outro@example.com",
        "303030",
        enroll_fidelity=False,
        cpf="39053344705",
    )
    assert account.email == "ana.ficticia@example.com"
    assert _outbox_count(db) == before
    get_settings.cache_clear()


def test_resume_by_cpf_does_not_accept_arbitrary_destination(db: Session, monkeypatch) -> None:
    settings = _settings(monkeypatch)
    _verified_account(db, settings, monkeypatch)
    _force_code(monkeypatch, 404040)
    result = start_resume_by_cpf(db, settings, "39053344705")
    mail = db.query(EmailOutbox).order_by(EmailOutbox.id.desc()).first()
    assert mail is not None
    assert mail.to_address == "ana.ficticia@example.com"
    assert result["email_masked"] == "a***@example.com"
    get_settings.cache_clear()


def test_invalid_expired_and_consumed_codes_are_rejected(db: Session, monkeypatch) -> None:
    settings = _settings(monkeypatch)
    _verified_account(db, settings, monkeypatch)
    _force_code(monkeypatch, 505050)
    start_resume(db, settings, "ana.ficticia@example.com")
    with pytest.raises(ConfirmationError, match="inválido ou expirado"):
        verify_code(db, settings, "ana.ficticia@example.com", "000000", enroll_fidelity=False)
    verify_code(db, settings, "ana.ficticia@example.com", "505050", enroll_fidelity=False)
    with pytest.raises(ConfirmationError, match="inválido ou expirado"):
        verify_code(db, settings, "ana.ficticia@example.com", "505050", enroll_fidelity=False)
    _force_code(monkeypatch, 606060)
    start_resume(db, settings, "ana.ficticia@example.com")
    cutoff = utc_now() - timedelta(hours=1)
    for row in db.query(CustomerChallenge).filter(CustomerChallenge.email == "ana.ficticia@example.com"):
        row.expires_at = cutoff
    db.flush()
    with pytest.raises(ConfirmationError, match="inválido ou expirado"):
        verify_code(db, settings, "ana.ficticia@example.com", "606060", enroll_fidelity=False)
    assert CODE_TTL_MINUTES == 15
    get_settings.cache_clear()


def test_unknown_cpf_verify_does_not_enumerate(db: Session, monkeypatch) -> None:
    settings = _settings(monkeypatch)
    with pytest.raises(ConfirmationError, match="inválido ou expirado"):
        verify_code(db, settings, "", "123456", enroll_fidelity=False, cpf="11144477735")
    get_settings.cache_clear()


def test_resend_limit_stays_in_place(db: Session, monkeypatch) -> None:
    settings = _settings(monkeypatch)
    _verified_account(db, settings, monkeypatch)
    _force_code(monkeypatch, 707070)
    start_resume(db, settings, "ana.ficticia@example.com")
    with pytest.raises(RateLimitError):
        start_resume(db, settings, "ana.ficticia@example.com")
    get_settings.cache_clear()
