from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import timedelta

from fastapi import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.admin_auth import digest_secret
from app.domain.capacity import utc_now
from app.domain.cpf import cpf_hmac, identity_secret, mask_cpf, require_cpf
from app.domain.errors import ConfirmationError, RateLimitError
from app.domain.house_fidelity import GENERIC_VERIFY_MESSAGE, campaign_is_publicly_active
from app.models.customers import CustomerAccount, CustomerChallenge, CustomerSession
from app.models.email_outbox import EmailOutbox
from app.models.house_fidelity import HouseFidelityEnrollment

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CUSTOMER_COOKIE = "lojadepaes_customer_session"
CODE_TTL_MINUTES = 15
RESEND_SECONDS = 60
MAX_SENDS_HOUR = 5
SESSION_DAYS = 30
GENERIC_SENT = (
    "Se este cadastro puder ser confirmado, enviamos um código para o e-mail informado. "
    "O CPF não abre saldo sozinho."
)


def _email(value: str) -> str:
    cleaned = value.strip().lower()
    if not EMAIL_RE.fullmatch(cleaned) or len(cleaned) > 254:
        raise ConfirmationError("informe um e-mail válido")
    return cleaned


def _name(value: str) -> str:
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > 160:
        raise ConfirmationError("informe um nome")
    return cleaned


def digest_code(settings: Settings, code: str) -> str:
    return hmac.new(
        identity_secret(settings).encode("utf-8"),
        f"code:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def set_customer_cookie(response: Response, settings: Settings, raw_token: str) -> None:
    response.set_cookie(
        key=CUSTOMER_COOKIE,
        value=raw_token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=SESSION_DAYS * 24 * 3600,
        path="/",
    )


def clear_customer_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=CUSTOMER_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def load_customer(
    session: Session, settings: Settings, token: str | None
) -> CustomerAccount | None:
    if not token:
        return None
    secret = settings.admin_session_secret or identity_secret(settings)
    row = session.scalar(
        select(CustomerSession).where(CustomerSession.token_hash == digest_secret(secret, token))
    )
    now = utc_now()
    if row is None or row.revoked_at is not None or row.expires_at <= now:
        return None
    account = session.get(CustomerAccount, row.account_id)
    if account is None or account.email_verified_at is None:
        return None
    return account


def _create_session(session: Session, settings: Settings, account: CustomerAccount) -> str:
    raw = secrets.token_urlsafe(32)
    secret = settings.admin_session_secret or identity_secret(settings)
    session.add(
        CustomerSession(
            account_id=account.id,
            token_hash=digest_secret(secret, raw),
            expires_at=utc_now() + timedelta(days=SESSION_DAYS),
        )
    )
    session.flush()
    return raw


def _sends_last_hour(session: Session, email: str) -> int:
    cutoff = utc_now() - timedelta(hours=1)
    return int(
        session.scalar(
            select(func.count()).where(
                CustomerChallenge.email == email,
                CustomerChallenge.created_at >= cutoff,
            )
        )
        or 0
    )


def _latest_open_challenge(session: Session, email: str) -> CustomerChallenge | None:
    return session.scalar(
        select(CustomerChallenge)
        .where(
            CustomerChallenge.email == email,
            CustomerChallenge.consumed_at.is_(None),
            CustomerChallenge.expires_at > utc_now(),
        )
        .order_by(CustomerChallenge.created_at.desc())
    )


def _enqueue_code(
    session: Session,
    settings: Settings,
    *,
    account: CustomerAccount | None,
    email: str,
    purpose: str,
) -> None:
    if _sends_last_hour(session, email) >= MAX_SENDS_HOUR:
        raise RateLimitError("aguarde para pedir um novo código")
    latest = _latest_open_challenge(session, email)
    if latest is not None and (utc_now() - latest.created_at).total_seconds() < RESEND_SECONDS:
        raise RateLimitError("aguarde um momento para reenviar o código")
    code = f"{secrets.randbelow(1_000_000):06d}"
    raw_link = secrets.token_urlsafe(24)
    secret = settings.admin_session_secret or identity_secret(settings)
    challenge = CustomerChallenge(
        account_id=account.id if account is not None else None,
        email=email,
        purpose=purpose,
        code_hash=digest_code(settings, code),
        token_hash=digest_secret(secret, raw_link),
        expires_at=utc_now() + timedelta(minutes=CODE_TTL_MINUTES),
    )
    session.add(challenge)
    session.flush()
    ready = settings.mail_transport_ready
    origin = settings.public_origin.rstrip("/")
    link = f"{origin}/#fidelidade-verificar={raw_link}"
    body = (
        f"Seu código da Loja de Pães é {code}. Ele vale por {CODE_TTL_MINUTES} minutos "
        f"e só pode ser usado uma vez.\n\nConfirmar por este endereço:\n{link}\n\n"
        "Se você não pediu este código, ignore esta mensagem."
    )
    session.add(
        EmailOutbox(
            kind="customer_verify" if purpose == "signup" else "customer_resume",
            to_address=email,
            subject="Código para a Loja de Pães",
            body=body,
            status="pending" if ready else "skipped",
            last_error=None if ready else "serviço de e-mail não configurado; mensagem capturada",
            dedupe_key=f"customer:{challenge.id}:{purpose}",
        )
    )
    session.flush()


def start_signup(session: Session, settings: Settings, name: str, email: str, cpf: str) -> dict:
    person = _name(name)
    address = _email(email)
    digits = require_cpf(cpf)
    digest = cpf_hmac(settings, digits)
    by_email = session.scalar(select(CustomerAccount).where(CustomerAccount.email == address))
    by_cpf = session.scalar(select(CustomerAccount).where(CustomerAccount.cpf_hmac == digest))
    if by_cpf is not None and by_email is not None and by_cpf.id != by_email.id:
        return {"ok": True, "needs_verification": True, "message": GENERIC_SENT}
    if by_cpf is not None and by_cpf.email != address:
        return {"ok": True, "needs_verification": True, "message": GENERIC_SENT}
    if by_email is not None and by_email.cpf_hmac != digest:
        return {"ok": True, "needs_verification": True, "message": GENERIC_SENT}
    account = by_email or by_cpf
    if account is None:
        account = CustomerAccount(
            name=person,
            email=address,
            cpf_hmac=digest,
            cpf_last2=digits[-2:],
            marketing_opt_in=False,
        )
        session.add(account)
        session.flush()
    elif account.email_verified_at is None:
        account.name = person
    _enqueue_code(session, settings, account=account, email=address, purpose="signup")
    return {"ok": True, "needs_verification": True, "message": GENERIC_SENT}


def start_resume(session: Session, settings: Settings, email: str) -> dict:
    address = _email(email)
    account = session.scalar(select(CustomerAccount).where(CustomerAccount.email == address))
    if account is not None and account.email_verified_at is not None:
        _enqueue_code(session, settings, account=account, email=address, purpose="resume")
    elif account is not None:
        _enqueue_code(session, settings, account=account, email=address, purpose="signup")
    return {"ok": True, "needs_verification": True, "message": GENERIC_SENT}


def verify_code(
    session: Session, settings: Settings, email: str, code: str
) -> tuple[CustomerAccount, str]:
    address = _email(email)
    challenge = _latest_open_challenge(session, address)
    if challenge is None:
        raise ConfirmationError("código inválido ou expirado")
    if challenge.attempts >= challenge.max_attempts:
        raise RateLimitError("muitas tentativas; peça um código novo")
    challenge.attempts += 1
    session.flush()
    if challenge.code_hash != digest_code(settings, code.strip()):
        raise ConfirmationError("código inválido ou expirado")
    account = session.get(CustomerAccount, challenge.account_id) if challenge.account_id else None
    if account is None:
        raise ConfirmationError("código inválido ou expirado")
    challenge.consumed_at = utc_now()
    if account.email_verified_at is None:
        account.email_verified_at = utc_now()
    _ensure_enrollment(session, settings, account)
    raw = _create_session(session, settings, account)
    session.flush()
    return account, raw


def verify_link(session: Session, settings: Settings, token: str) -> tuple[CustomerAccount, str]:
    secret = settings.admin_session_secret or identity_secret(settings)
    digest = digest_secret(secret, token)
    challenge = session.scalar(
        select(CustomerChallenge).where(CustomerChallenge.token_hash == digest)
    )
    if (
        challenge is None
        or challenge.consumed_at is not None
        or challenge.expires_at <= utc_now()
        or challenge.account_id is None
    ):
        raise ConfirmationError("este link não é mais válido")
    account = session.get(CustomerAccount, challenge.account_id)
    if account is None:
        raise ConfirmationError("este link não é mais válido")
    challenge.consumed_at = utc_now()
    if account.email_verified_at is None:
        account.email_verified_at = utc_now()
    _ensure_enrollment(session, settings, account)
    raw = _create_session(session, settings, account)
    session.flush()
    return account, raw


def logout_customer(session: Session, settings: Settings, token: str | None) -> None:
    if not token:
        return
    secret = settings.admin_session_secret or identity_secret(settings)
    row = session.scalar(
        select(CustomerSession).where(CustomerSession.token_hash == digest_secret(secret, token))
    )
    if row is not None and row.revoked_at is None:
        row.revoked_at = utc_now()
        session.flush()


def _ensure_enrollment(session: Session, settings: Settings, account: CustomerAccount) -> None:
    from app.domain.house_fidelity import current_campaign

    campaign = current_campaign(session)
    if campaign is None:
        return
    existing = session.scalar(
        select(HouseFidelityEnrollment).where(
            HouseFidelityEnrollment.account_id == account.id,
            HouseFidelityEnrollment.campaign_id == campaign.id,
        )
    )
    if existing is not None:
        return
    session.add(
        HouseFidelityEnrollment(
            account_id=account.id,
            campaign_id=campaign.id,
            rules_version=campaign.rules_version,
            enrolled_at=utc_now(),
        )
    )


def public_account_view(
    account: CustomerAccount,
    settings: Settings,
    extra: dict | None = None,
    campaign=None,
) -> dict:
    active = campaign_is_publicly_active(settings, campaign)
    payload = {
        "verified": account.email_verified_at is not None,
        "name": account.name,
        "email": account.email,
        "cpf_masked": mask_cpf(account.cpf_last2),
        "campaign_active": active,
        "confirmed": True,
        "message": "Cadastro confirmado." if active else GENERIC_VERIFY_MESSAGE,
    }
    if extra:
        payload.update(extra)
    return payload
