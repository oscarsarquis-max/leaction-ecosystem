from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from ipaddress import ip_address

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.activation import resolved_password_hash
from app.domain.capacity import utc_now
from app.domain.errors import AuthDisabledError, AuthError, AuthForbiddenError, RateLimitError
from app.models.admin import AdminLoginAttempt, AdminSession

SESSION_COOKIE = "lojadepaes_admin_session"
CSRF_HEADER = "X-CSRF-Token"
ACTOR_PREFIX = "admin:"
LOCAL_DEV_USERNAME = "desenvolvimento"
_hasher = PasswordHasher()


def is_loopback_client(host: str) -> bool:
    value = (host or "").strip().lower()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    if "%" in value:
        value = value.split("%", 1)[0]
    if value in {"localhost", "ip6-localhost", "ip6-loopback"}:
        return True
    if value.startswith("::ffff:"):
        value = value[7:]
    try:
        return ip_address(value).is_loopback
    except ValueError:
        return False


def local_passwordless_permitted(settings: Settings, client_host: str, server_host: str | None = None) -> bool:
    if not settings.admin_local_passwordless:
        return False
    env_name = settings.env.strip().lower()
    if env_name in {"production", "prod"} or env_name not in {"local", "development", "dev"}:
        return False
    if not is_loopback_client(settings.http_host):
        return False
    bind = (server_host or "").strip().lower()
    if bind in {"0.0.0.0", "::", "*"}:
        return False
    if bind and bind not in {"testserver", "testclient"} and not is_loopback_client(bind):
        return False
    return is_loopback_client(client_host)


def actor_ref_for(username: str) -> str:
    return f"{ACTOR_PREFIX}{username}"


def digest_secret(secret: str, value: str) -> str:
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def client_host_of(request_client: str | None) -> str:
    host = (request_client or "").strip() or "unknown"
    return host[:80]


@dataclass(frozen=True)
class AdminPrincipal:
    username: str
    session_id: object
    csrf_token: str

    @property
    def actor_ref(self) -> str:
        return actor_ref_for(self.username)


def _verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    return PasswordHasher(time_cost=2, memory_cost=65536, parallelism=4).hash(
        "lojadepaes-dummy-not-a-password"
    )


def record_login_attempt(
    session: Session, *, username: str, client_host: str, succeeded: bool
) -> None:
    session.add(
        AdminLoginAttempt(
            username=username[:80],
            client_host=client_host,
            succeeded=succeeded,
        )
    )


def assert_not_rate_limited(session: Session, settings: Settings, username: str, client_host: str) -> None:
    window = utc_now() - timedelta(minutes=settings.login_window_minutes)
    failures = session.scalar(
        select(func.count())
        .select_from(AdminLoginAttempt)
        .where(
            AdminLoginAttempt.username == username[:80],
            AdminLoginAttempt.client_host == client_host,
            AdminLoginAttempt.succeeded.is_(False),
            AdminLoginAttempt.created_at >= window,
        )
    )
    if int(failures or 0) >= settings.login_max_failures:
        raise RateLimitError("muitas tentativas; aguarde alguns minutos")


def _issue_session(
    session: Session,
    settings: Settings,
    *,
    username: str,
    client_host: str,
) -> tuple[str, str, AdminSession]:
    raw_token = secrets.token_urlsafe(32)
    raw_csrf = secrets.token_urlsafe(32)
    now = utc_now()
    row = AdminSession(
        token_hash=digest_secret(settings.admin_session_secret, raw_token),
        csrf_token_hash=digest_secret(settings.admin_session_secret, raw_csrf),
        username=username,
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
        last_seen_at=now,
        client_host=client_host,
    )
    session.add(row)
    record_login_attempt(session, username=username, client_host=client_host, succeeded=True)
    session.flush()
    return raw_token, raw_csrf, row


def login_admin(
    session: Session,
    settings: Settings,
    *,
    username: str,
    password: str,
    client_host: str,
) -> tuple[str, str, AdminSession]:
    if not settings.admin_identity_ready:
        raise AuthDisabledError(
            "gestão administrativa desabilitada: execute a configuração local e reinicie a API"
        )
    stored_hash = resolved_password_hash(session, settings)
    if not stored_hash:
        raise AuthDisabledError("esta conta ainda não tem senha. Use o link de ativação enviado.")
    normalized = username.strip()
    assert_not_rate_limited(session, settings, normalized, client_host)
    username_ok = hmac.compare_digest(normalized, settings.admin_username.strip())
    password_ok = _verify_password(
        stored_hash if username_ok else _dummy_password_hash(),
        password,
    )
    if not username_ok or not password_ok:
        record_login_attempt(session, username=normalized, client_host=client_host, succeeded=False)
        session.flush()
        raise AuthError("credenciais inválidas")
    return _issue_session(
        session,
        settings,
        username=settings.admin_username.strip(),
        client_host=client_host,
    )


def login_admin_local(
    session: Session,
    settings: Settings,
    *,
    client_host: str,
    server_host: str | None = None,
) -> tuple[str, str, AdminSession]:
    if not local_passwordless_permitted(settings, client_host, server_host):
        raise AuthForbiddenError("acesso local indisponível")
    if len(settings.admin_session_secret.strip()) < 32:
        raise AuthDisabledError(
            "gestão administrativa desabilitada: execute a configuração local e reinicie a API"
        )
    assert_not_rate_limited(session, settings, LOCAL_DEV_USERNAME, client_host)
    return _issue_session(
        session,
        settings,
        username=LOCAL_DEV_USERNAME,
        client_host=client_host,
    )


def load_session(
    session: Session,
    settings: Settings,
    raw_token: str | None,
    *,
    rotate_csrf: bool = False,
) -> tuple[AdminPrincipal, AdminSession] | None:
    if not settings.admin_enabled or not raw_token:
        return None
    token_hash = digest_secret(settings.admin_session_secret, raw_token)
    stmt = select(AdminSession).where(AdminSession.token_hash == token_hash)
    if rotate_csrf:
        stmt = stmt.with_for_update()
    row = session.execute(stmt).scalar_one_or_none()
    now = utc_now()
    if row is None or row.revoked_at is not None or row.expires_at <= now:
        return None
    csrf_raw = ""
    if rotate_csrf:
        csrf_raw = secrets.token_urlsafe(32)
        row.csrf_token_hash = digest_secret(settings.admin_session_secret, csrf_raw)
    row.last_seen_at = now
    session.flush()
    return AdminPrincipal(username=row.username, session_id=row.id, csrf_token=csrf_raw), row


def verify_csrf(settings: Settings, row: AdminSession, csrf_token: str | None) -> bool:
    if not csrf_token:
        return False
    expected = row.csrf_token_hash
    given = digest_secret(settings.admin_session_secret, csrf_token)
    return hmac.compare_digest(expected, given)


def revoke_session(session: Session, row: AdminSession) -> None:
    if row.revoked_at is None:
        row.revoked_at = utc_now()
        session.flush()
