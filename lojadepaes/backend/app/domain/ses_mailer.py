from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class MailSendResult:
    accepted: bool
    message_id: str | None
    error: str | None


def sanitize_mail_error(exc: BaseException) -> str:
    code = ""
    response = getattr(exc, "response", None)
    if isinstance(response, dict):
        error = response.get("Error")
        if isinstance(error, dict):
            code = str(error.get("Code") or "").strip()
    if not code:
        code = type(exc).__name__
    allowed = {
        "MessageRejected",
        "MailFromDomainNotVerified",
        "ConfigurationSetDoesNotExist",
        "AccountSendingPausedException",
        "LimitExceededException",
        "InvalidParameterValue",
        "AccessDeniedException",
        "UnrecognizedClientException",
        "IncompleteSignature",
        "ImportError",
    }
    label = code if code in allowed else "ses_error"
    return f"SES recusou o envio ({label})"


def formatted_mail_from(settings: Settings) -> str:
    address = settings.mail_from.strip()
    name = settings.mail_from_name.strip()
    if name and address:
        escaped = name.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}" <{address}>'
    return address


def send_outbox_email(
    settings: Settings, *, to_address: str, subject: str, body: str
) -> MailSendResult:
    if settings.mail_backend.strip().lower() != "ses":
        return MailSendResult(False, None, "transporte de e-mail não é SES")
    if not settings.mail_identity_ready:
        return MailSendResult(False, None, "identidade SES ainda não verificada")
    source = formatted_mail_from(settings)
    dest = to_address.strip()
    if not settings.mail_from.strip() or "@" not in settings.mail_from:
        return MailSendResult(False, None, "remetente SES não configurado")
    if not dest or "@" not in dest:
        return MailSendResult(False, None, "destinatário inválido")
    import os

    if os.environ.get("PYTEST_CURRENT_TEST"):
        return MailSendResult(False, None, "transporte de teste; SES real bloqueado")
    try:
        import boto3
    except ImportError:
        return MailSendResult(False, None, "biblioteca SES ausente no ambiente")
    kwargs: dict[str, str] = {"region_name": settings.ses_region.strip() or "us-east-2"}
    if settings.aws_access_key_id.strip() and settings.aws_secret_access_key.strip():
        kwargs["aws_access_key_id"] = settings.aws_access_key_id.strip()
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key.strip()
    client = boto3.client("ses", **kwargs)
    try:
        response = client.send_email(
            Source=source,
            Destination={"ToAddresses": [dest]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Text": {"Data": body, "Charset": "UTF-8"}},
            },
        )
    except Exception as exc:
        return MailSendResult(False, None, sanitize_mail_error(exc))
    message_id = response.get("MessageId") if isinstance(response, dict) else None
    return MailSendResult(True, str(message_id) if message_id else None, None)
