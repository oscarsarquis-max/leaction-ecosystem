"""Código pessoal reutilizável. O valor só existe na hora de emitir e no provedor."""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.identity_organization.models import (
    AccessCredential,
    AppUser,
    OnboardingAuthorization,
    OrganizationMembership,
)
from app.modules.identity_organization.services import record_audit

_LOWER = "abcdefghijkmnopqrstuvwxyz"
_UPPER = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_DIGIT = "23456789"
_SYMBOL = "!@#$%*-_"
_ATTEMPT_LIMIT = 5
_CONFIRMATION_MINUTES = 30

NOTICE = "Se este endereço puder entrar na Panne, o pedido foi registrado."


class IdentityDirectory(Protocol):
    def ensure_user(self, email: str) -> None: ...

    def set_permanent_code(self, email: str, code: str) -> None: ...

    def disable_user(self, email: str) -> None: ...

    def sign_out(self, email: str) -> None: ...


class AccessMailer(Protocol):
    def send_access_code(self, email: str, code: str, *, replacement: bool) -> None: ...

    def send_change_confirmation(self, email: str, confirmation: str) -> None: ...


class AccessCodeError(Exception):
    """Falha sem o código e sem o endereço."""


@dataclass
class MemoryDirectory:
    """Substituto de teste. Guarda o código só na memória do teste."""

    codes: dict[str, str]
    disabled: set[str]
    sessions_revoked: set[str]

    def ensure_user(self, email: str) -> None:
        return None

    def set_permanent_code(self, email: str, code: str) -> None:
        self.codes[email] = code

    def disable_user(self, email: str) -> None:
        self.disabled.add(email)

    def sign_out(self, email: str) -> None:
        self.sessions_revoked.add(email)

    def accepts(self, email: str, code: str) -> bool:
        return email not in self.disabled and self.codes.get(email) == code


@dataclass
class MemoryMailer:
    sent_codes: list[tuple[str, str, bool]]
    sent_confirmations: list[tuple[str, str]]

    def send_access_code(self, email: str, code: str, *, replacement: bool) -> None:
        self.sent_codes.append((email, code, replacement))

    def send_change_confirmation(self, email: str, confirmation: str) -> None:
        self.sent_confirmations.append((email, confirmation))


def generate_access_code() -> str:
    required = [
        secrets.choice(_LOWER),
        secrets.choice(_UPPER),
        secrets.choice(_DIGIT),
        secrets.choice(_SYMBOL),
    ]
    pool = _LOWER + _UPPER + _DIGIT + _SYMBOL
    chars = required + [secrets.choice(pool) for _ in range(16)]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def _email(value: str) -> str:
    return value.strip().lower()


def _pepper() -> str:
    pepper = os.environ.get("PANNE_ACCESS_CODE_PEPPER", "")
    if len(pepper) < 16:
        raise AccessCodeError("pepper_ausente")
    return pepper


def _hash(secret: str) -> str:
    return hashlib.sha256(f"{_pepper()}:{secret}".encode()).hexdigest()


def _eligible(session: Session, email: str) -> bool:
    authorization = session.scalar(
        select(OnboardingAuthorization.id).where(
            OnboardingAuthorization.email_normalized == email,
            OnboardingAuthorization.status.in_(("issued", "bound")),
            OnboardingAuthorization.expires_at > datetime.now(UTC),
            OnboardingAuthorization.clients_created < OnboardingAuthorization.max_clients,
        )
    )
    if authorization is not None:
        return True
    user = session.scalar(
        select(AppUser).where(func.lower(AppUser.email) == email, AppUser.status == "active")
    )
    if user is None:
        return False
    membership = session.scalar(
        select(OrganizationMembership.id).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.status == "active",
        )
    )
    return membership is not None


def _row(session: Session, email: str) -> AccessCredential | None:
    return session.scalar(select(AccessCredential).where(AccessCredential.email_normalized == email))


def issue_first_code(
    session: Session,
    email: str,
    directory: IdentityDirectory,
    mailer: AccessMailer,
) -> str:
    """Emite uma vez. Uma credencial já ativa não gera outra."""
    email_key = _email(email)
    if not _eligible(session, email_key):
        return "ineligible"
    current = _row(session, email_key)
    if current is not None and current.status == "revoked":
        return "ineligible"
    if current is not None and current.status == "active":
        return "unchanged"
    code = generate_access_code()
    directory.ensure_user(email_key)
    directory.set_permanent_code(email_key, code)
    mailer.send_access_code(email_key, code, replacement=False)
    row = AccessCredential(email_normalized=email_key, status="active", issued_at=datetime.now(UTC))
    session.add(row)
    session.flush()
    record_audit(
        session,
        event_type="access_code.issued",
        aggregate_type="access_credential",
        aggregate_id=row.id,
        payload={"purpose": "first"},
    )
    return "issued"


def request_code_change(
    session: Session,
    email: str,
    mailer: AccessMailer,
) -> None:
    email_key = _email(email)
    current = _row(session, email_key)
    if current is None or current.status != "active" or not _eligible(session, email_key):
        return
    if (
        current.confirmation_hash
        and current.confirmation_expires_at is not None
        and current.confirmation_expires_at > datetime.now(UTC)
    ):
        return
    confirmation = secrets.token_urlsafe(32)
    current.confirmation_hash = _hash(confirmation)
    current.confirmation_expires_at = datetime.now(UTC) + timedelta(minutes=_CONFIRMATION_MINUTES)
    current.confirmation_attempts = 0
    session.flush()
    mailer.send_change_confirmation(email_key, confirmation)
    record_audit(
        session,
        event_type="access_code.change_requested",
        aggregate_type="access_credential",
        aggregate_id=current.id,
        payload={"minutes": _CONFIRMATION_MINUTES},
    )


def confirm_code_change(
    session: Session,
    email: str,
    confirmation: str,
    directory: IdentityDirectory,
    mailer: AccessMailer,
) -> bool:
    email_key = _email(email)
    current = _row(session, email_key)
    if current is None or current.status != "active" or not current.confirmation_hash:
        return False
    if current.confirmation_attempts >= _ATTEMPT_LIMIT:
        return False
    expired = (
        current.confirmation_expires_at is None or current.confirmation_expires_at <= datetime.now(UTC)
    )
    if expired or not secrets.compare_digest(current.confirmation_hash, _hash(confirmation)):
        current.confirmation_attempts += 1
        session.flush()
        return False
    code = generate_access_code()
    directory.set_permanent_code(email_key, code)
    mailer.send_access_code(email_key, code, replacement=True)
    current.confirmation_hash = None
    current.confirmation_expires_at = None
    current.confirmation_attempts = 0
    current.changed_at = datetime.now(UTC)
    session.flush()
    record_audit(
        session,
        event_type="access_code.changed",
        aggregate_type="access_credential",
        aggregate_id=current.id,
        payload={"purpose": "replacement"},
    )
    return True


def revoke_access_code(
    session: Session,
    email: str,
    directory: IdentityDirectory,
) -> str:
    email_key = _email(email)
    current = _row(session, email_key)
    if current is None or current.status == "revoked":
        return "absent"
    directory.disable_user(email_key)
    directory.sign_out(email_key)
    current.status = "revoked"
    current.confirmation_hash = None
    current.confirmation_expires_at = None
    session.flush()
    record_audit(
        session,
        event_type="access_code.revoked",
        aggregate_type="access_credential",
        aggregate_id=current.id,
        payload={"purpose": "revoked"},
    )
    return "revoked"


def credential_id(session: Session, email: str) -> UUID | None:
    row = _row(session, _email(email))
    return None if row is None else row.id
