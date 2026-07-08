"""Envio de código de acesso por e-mail — mesma infra SES do PanelDX."""

from __future__ import annotations

import logging
import os
import textwrap
import threading
from pathlib import Path

from botocore.config import Config

logger = logging.getLogger(__name__)

SES_BOTO_CONFIG = Config(connect_timeout=8, read_timeout=12, retries={"max_attempts": 2})
SES_PLACEHOLDER_DOMAINS = ("seudominio.com.br", "example.com", "seudominio.com")
DEFAULT_EMAIL_SENDER = "consultant@paneldx.com.br"
DEFAULT_SES_REGION = "us-east-2"
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "email_access_code.html"


def dispatch_access_code_email(recipient: str, access_code: str) -> None:
    """Dispara e-mail em background para não bloquear cadastro/login."""
    resolved_base = _resolve_public_url()

    def _worker() -> None:
        ok = send_access_code_email_ses(
            recipient=recipient,
            access_code=access_code,
            access_url_base=resolved_base,
        )
        if not ok:
            logger.warning(
                "[SES] Falha ao enviar código para %s. Verifique EMAIL_SENDER (%s) e identidades no SES.",
                recipient,
                _resolve_email_sender(),
            )
            print(
                f"\n📧 [DEV] Código de acesso para {recipient}: {access_code}\n"
                f"    Acesse: {resolved_base}/acesso\n",
                flush=True,
            )

    logger.info(
        "[SES] Agendando e-mail para %s (código %s, base %s)...",
        recipient,
        access_code,
        resolved_base,
    )
    threading.Thread(target=_worker, daemon=True, name=f"ses-{recipient}").start()


def send_access_code_email_ses(
    recipient: str,
    access_code: str,
    *,
    aws_region: str | None = None,
    access_url_base: str | None = None,
) -> bool:
    """Envia o e-mail de código de acesso via AWS SES (Boto3), com corpo HTML."""
    aws_region = aws_region or _resolve_ses_region()
    sender_email = _resolve_email_sender()

    try:
        import boto3

        ses_client = boto3.client("ses", region_name=aws_region, config=SES_BOTO_CONFIG)
    except Exception as exc:
        logger.error("Falha ao inicializar cliente Boto3/SES: %s", exc)
        return False

    base = (access_url_base or _resolve_public_url()).rstrip("/")
    access_url = f"{base}/acesso/{access_code}"

    subject = "Seu Código de Acesso — Chamelleon Diagnóstico"
    body_html = _render_access_code_html(recipient, access_code, access_url)
    body_text = textwrap.dedent(
        f"""\
        Olá!

        Sua inscrição foi concluída com sucesso.

        Seu código de acesso único é:
        {access_code}

        Seu login é o e-mail cadastrado:
        ({recipient}).

        Acesse {access_url}
        para iniciar sua avaliação.

        Equipe LeAction / Chamelleon
        Dúvidas: conhecer@leaction.com.br
        """
    ).strip().replace("\n", "\r\n")

    message_body: dict[str, dict[str, str]] = {
        "Text": {"Data": body_text, "Charset": "UTF-8"},
    }
    if body_html:
        message_body["Html"] = {"Data": body_html, "Charset": "UTF-8"}

    try:
        response = ses_client.send_email(
            Source=sender_email,
            Destination={"ToAddresses": [recipient]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": message_body,
            },
        )
        logger.info("[SES] E-mail enviado para %s (MessageId: %s)", recipient, response["MessageId"])
        return True
    except Exception as exc:
        logger.error("[SES] Falha ao enviar para %s: %s", recipient, exc)
        return False


def _resolve_email_sender() -> str:
    """Remetente SES verificado — mesmo padrão do PanelDX."""
    candidates = [
        os.getenv("EMAIL_SENDER"),
        os.getenv("MAIL_USERNAME"),
        DEFAULT_EMAIL_SENDER,
    ]
    for sender in candidates:
        if not sender:
            continue
        normalized = sender.strip().lower()
        if any(domain in normalized for domain in SES_PLACEHOLDER_DOMAINS):
            continue
        return sender.strip()
    return DEFAULT_EMAIL_SENDER


def _resolve_ses_region() -> str:
    return (
        os.getenv("AWS_SES_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or os.getenv("AWS_REGION")
        or DEFAULT_SES_REGION
    )


def _resolve_public_url() -> str:
    candidates = [
        os.getenv("CHAMELLEON_PUBLIC_URL"),
        os.getenv("FRONTEND_URL"),
        "http://localhost:5173",
    ]
    for url in candidates:
        if url and str(url).strip():
            return str(url).strip().rstrip("/")
    return "http://localhost:5173"


def _render_access_code_html(recipient: str, access_code: str, access_url: str) -> str | None:
    try:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
        return (
            template.replace("{{ access_code }}", access_code)
            .replace("{{ recipient }}", recipient)
            .replace("{{ access_url }}", access_url)
        )
    except Exception as exc:
        logger.warning("Falha ao renderizar template HTML de e-mail: %s", exc)
        return None
