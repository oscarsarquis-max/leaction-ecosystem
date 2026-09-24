from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from hashlib import sha256
from zoneinfo import ZoneInfo

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.capacity import utc_now
from app.domain.errors import AuthDisabledError, AuthError, ConfirmationError
from app.domain.ses_mailer import send_outbox_email
from app.models.admin import AdminAccount, AdminActivationDispatch, AdminActivationToken

_hasher = PasswordHasher()
PURPOSE = "set_password"
MIN_PASSWORD = 10
ACTIVATION_TZ = ZoneInfo("America/Sao_Paulo")


def activation_ttl_minutes(settings: Settings) -> int:
    return max(5, int(settings.activation_ttl_minutes))


def format_expiry_sao_paulo(expires_at: datetime) -> str:
    local = expires_at.astimezone(ACTIVATION_TZ)
    return local.strftime("%d/%m/%Y às %H:%M")


def _ttl_phrase(minutes: int) -> str:
    if minutes % (24 * 60) == 0:
        days = minutes // (24 * 60)
        return "24 horas" if days == 1 else f"{days} dias"
    if minutes % 60 == 0:
        hours = minutes // 60
        return "1 hora" if hours == 1 else f"{hours} horas"
    return f"{minutes} minutos"


def hash_activation_token(raw: str) -> str:
    return sha256(raw.encode("utf-8")).hexdigest()


def ensure_admin_account(session: Session, username: str) -> AdminAccount:
    row = session.scalar(select(AdminAccount).where(AdminAccount.username == username))
    if row is not None:
        return row
    row = AdminAccount(username=username, password_hash=None)
    session.add(row)
    session.flush()
    return row


def account_password_set(session: Session, settings: Settings) -> bool:
    if settings.admin_password_hash.strip():
        return True
    username = settings.admin_username.strip()
    if not username:
        return False
    row = session.scalar(select(AdminAccount).where(AdminAccount.username == username))
    return bool(row and row.password_hash)


def resolved_password_hash(session: Session, settings: Settings) -> str | None:
    env_hash = settings.admin_password_hash.strip()
    if env_hash:
        return env_hash
    username = settings.admin_username.strip()
    if not username:
        return None
    row = session.scalar(select(AdminAccount).where(AdminAccount.username == username))
    if row is None or not row.password_hash:
        return None
    return row.password_hash


def _active_token(session: Session, username: str) -> AdminActivationToken | None:
    now = utc_now()
    return session.scalar(
        select(AdminActivationToken)
        .where(
            AdminActivationToken.username == username,
            AdminActivationToken.purpose == PURPOSE,
            AdminActivationToken.consumed_at.is_(None),
            AdminActivationToken.invalidated_at.is_(None),
            AdminActivationToken.expires_at > now,
        )
        .order_by(AdminActivationToken.created_at.desc())
    )


def _latest_dispatch(session: Session, username: str) -> AdminActivationDispatch | None:
    return session.scalar(
        select(AdminActivationDispatch)
        .where(AdminActivationDispatch.username == username)
        .order_by(AdminActivationDispatch.sent_at.desc())
    )


def _invalidate_open_tokens(session: Session, username: str) -> None:
    now = utc_now()
    rows = list(
        session.scalars(
            select(AdminActivationToken).where(
                AdminActivationToken.username == username,
                AdminActivationToken.consumed_at.is_(None),
                AdminActivationToken.invalidated_at.is_(None),
            )
        )
    )
    for row in rows:
        row.invalidated_at = now
    if rows:
        session.flush()


def _validate_new_password(username: str, password: str, confirm: str) -> None:
    if password != confirm:
        raise ConfirmationError("as senhas não coincidem")
    if len(password) < MIN_PASSWORD:
        raise ConfirmationError("a senha precisa ter pelo menos 10 caracteres")
    if password.strip() != password:
        raise ConfirmationError("a senha não pode começar ou terminar com espaço")
    if password.lower() == username.strip().lower():
        raise ConfirmationError("a senha não pode ser igual ao login")


def issue_activation(
    session: Session,
    settings: Settings,
    *,
    force: bool = False,
    send: bool = True,
) -> dict[str, str]:
    username = settings.admin_username.strip()
    if username != "admin@lojadepaes.com.br":
        raise AuthDisabledError("ativação só é emitida para a conta administrativa provisionada")
    if len(settings.admin_session_secret.strip()) < 32:
        raise AuthDisabledError("configure o segredo de sessão antes de emitir a ativação")
    origin = settings.public_origin.strip().rstrip("/")
    if send and not origin.startswith("https://"):
        raise AuthDisabledError("a origem pública precisa ser HTTPS para enviar o link de ativação")
    recipient = settings.activation_recipient.strip().lower()
    if recipient != "oscar@oscarsarquis.com.br":
        raise AuthDisabledError("destinatário de ativação não autorizado")
    ensure_admin_account(session, username)
    if account_password_set(session, settings):
        return {"status": "already_activated", "message": "a conta administrativa já tem senha"}
    existing = _active_token(session, username)
    dispatched = _latest_dispatch(session, username)
    if existing is not None and dispatched is not None and dispatched.status == "sent":
        if not force:
            return {
                "status": "already_sent",
                "message": "ativação já enviada; não reenviada",
            }
    _invalidate_open_tokens(session, username)
    raw = secrets.token_urlsafe(32)
    minutes = activation_ttl_minutes(settings)
    expires_at = utc_now() + timedelta(minutes=minutes)
    expiry_label = format_expiry_sao_paulo(expires_at)
    row = AdminActivationToken(
        username=username,
        token_hash=hash_activation_token(raw),
        purpose=PURPOSE,
        expires_at=expires_at,
    )
    session.add(row)
    session.flush()
    if not send:
        return {
            "status": "issued",
            "message": "token emitido sem envio",
            "expires_at_sp": expiry_label,
        }
    link = f"{origin}/ativar/{raw}"
    body = (
        "Olá.\n\n"
        "Use o link abaixo para definir a senha da conta administrativa "
        f"{username} na Loja de Pães.\n"
        "O link vale uma vez e permanece válido por "
        f"{_ttl_phrase(minutes)}. Expira em {expiry_label} (horário de Brasília).\n"
        "Abrir o link não o consome; só salvar a senha conclui a ativação.\n\n"
        f"{link}\n\n"
        "Se você não pediu isso, ignore esta mensagem.\n"
    )
    result = send_outbox_email(
        settings,
        to_address=recipient,
        subject="Defina a senha da Loja de Pães",
        body=body,
    )
    dispatch = AdminActivationDispatch(
        username=username,
        recipient=recipient,
        provider_message_id=result.message_id,
        status="sent" if result.accepted else "failed",
    )
    session.add(dispatch)
    session.flush()
    if not result.accepted:
        raise AuthDisabledError(result.error or "não foi possível enviar o e-mail de ativação")
    return {
        "status": "sent",
        "message": (
            "ativação enviada ao destinatário autorizado; válido até "
            f"{expiry_label} (horário de Brasília)"
        ),
        "expires_at_sp": expiry_label,
    }


def lookup_activation(
    session: Session, settings: Settings, raw_token: str
) -> dict[str, str | bool]:
    username = settings.admin_username.strip()
    digest = hash_activation_token(raw_token.strip())
    row = session.scalar(
        select(AdminActivationToken).where(AdminActivationToken.token_hash == digest)
    )
    if row is None or row.username != username or row.purpose != PURPOSE:
        raise AuthError("este link de ativação não é válido")
    if row.invalidated_at is not None:
        raise AuthError("este link de ativação foi substituído")
    if row.consumed_at is not None:
        raise AuthError("este link de ativação já foi usado")
    if row.expires_at <= utc_now():
        raise AuthError("este link de ativação expirou")
    if account_password_set(session, settings):
        raise AuthError("esta conta já tem senha definida")
    return {"username": username, "ready": True}


def consume_activation(
    session: Session,
    settings: Settings,
    *,
    raw_token: str,
    password: str,
    confirm: str,
) -> dict[str, str]:
    username = settings.admin_username.strip()
    _validate_new_password(username, password, confirm)
    digest = hash_activation_token(raw_token.strip())
    row = session.scalar(
        select(AdminActivationToken)
        .where(AdminActivationToken.token_hash == digest)
        .with_for_update()
    )
    if row is None or row.username != username or row.purpose != PURPOSE:
        raise AuthError("este link de ativação não é válido")
    if row.invalidated_at is not None:
        raise AuthError("este link de ativação foi substituído")
    if row.consumed_at is not None:
        raise AuthError("este link de ativação já foi usado")
    if row.expires_at <= utc_now():
        raise AuthError("este link de ativação expirou")
    account = session.scalar(
        select(AdminAccount).where(AdminAccount.username == username).with_for_update()
    )
    if account is None:
        account = ensure_admin_account(session, username)
    if account.password_hash:
        raise AuthError("esta conta já tem senha definida")
    now = utc_now()
    account.password_hash = _hasher.hash(password)
    account.password_set_at = now
    account.updated_at = now
    row.consumed_at = now
    session.flush()
    return {"status": "activated", "username": username}
