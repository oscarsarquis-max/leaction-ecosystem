"""Sessão do parceiro. Cookie e tabela próprios, separados do admin."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.marketplace.models import Partner, PartnerSession, PartnerUser

PARTNER_COOKIE = "lojadepaes_partner_session"
_hasher = PasswordHasher()


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def start_session(db: Session, user: PartnerUser) -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    db.add(
        PartnerSession(
            partner_user_id=user.id,
            token_hash=hash_token(raw),
            csrf_token=csrf,
            expires_at=datetime.now(UTC) + timedelta(hours=12),
        )
    )
    db.flush()
    return raw, csrf


def open_session(db: Session, raw: str | None) -> tuple[PartnerUser, Partner, PartnerSession] | None:
    if not raw:
        return None
    row = db.scalar(select(PartnerSession).where(PartnerSession.token_hash == hash_token(raw)))
    if row is None:
        return None
    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        return None
    user = db.get(PartnerUser, row.partner_user_id)
    if user is None:
        return None
    partner = db.get(Partner, user.partner_id)
    if partner is None:
        return None
    return user, partner, row


def csrf_matches(row: PartnerSession, header: str | None) -> bool:
    if not header or not row.csrf_token:
        return False
    return hmac.compare_digest(row.csrf_token, header)
