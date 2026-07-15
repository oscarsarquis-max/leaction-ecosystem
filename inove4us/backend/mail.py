"""Envio do código de acesso (AWS SES) — identidade inove4us."""

from __future__ import annotations

import os
import sys
import textwrap
import threading
from pathlib import Path


def _dev_mode() -> bool:
    return os.environ.get("EMAIL_DEV_MODE", "").strip() in ("1", "true", "True", "yes")


def _render_access_code_html(*, recipient: str, access_code: str, access_url: str, logo_url: str) -> str:
    template_path = Path(__file__).resolve().parent / "templates" / "email_access_code.html"
    html = template_path.read_text(encoding="utf-8")
    return (
        html.replace("{{ recipient }}", recipient)
        .replace("{{ access_code }}", access_code)
        .replace("{{ access_url }}", access_url)
        .replace("{{ logo_url }}", logo_url)
    )


def _build_access_code_text(*, recipient: str, access_code: str, access_url: str) -> str:
    return textwrap.dedent(
        f"""\
        Olá!

        Seu cadastro freemium na inove4us foi concluído.
        Seu código de acesso à Mesa do Inovador é:

        {access_code}

        Login (e-mail): {recipient}
        Acesse: {access_url}

        Se você não solicitou este código, ignore esta mensagem.

        Equipe inove4us
        contato@inove4us.com.br
        """
    ).strip()


def send_access_code_email(recipient: str, access_code: str) -> dict:
    """Envia o código. Em falha SES ou modo dev, registra no log."""
    recipient = (recipient or "").strip().lower()
    access_code = (access_code or "").strip().upper()
    frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5174").rstrip("/")
    access_url = f"{frontend}/acesso"
    logo_url = f"{frontend}/imagens/logosombra3.png"

    subject = "Seu código de acesso — Mesa do Inovador | inove4us"
    body_text = _build_access_code_text(
        recipient=recipient,
        access_code=access_code,
        access_url=access_url,
    )
    try:
        body_html = _render_access_code_html(
            recipient=recipient,
            access_code=access_code,
            access_url=access_url,
            logo_url=logo_url,
        )
    except Exception as exc:
        print(f"[inove4us] Falha ao montar HTML do e-mail: {exc}", file=sys.stderr)
        body_html = None

    # Em local: EMAIL_DEV_MODE=1. Em ECS Fargate as credenciais vêm da task role
    # (não há AWS_ACCESS_KEY_ID no ambiente — não usar isso como gate).
    if _dev_mode():
        print(
            f"[inove4us][DEV-MAIL] Para {recipient}: {access_code}",
            file=sys.stderr,
        )
        return {"sent": True, "channel": "dev_log"}

    def _worker():
        try:
            import boto3

            region = (
                os.environ.get("AWS_REGION")
                or os.environ.get("AWS_DEFAULT_REGION")
                or "us-east-2"
            )
            sender = os.environ.get("EMAIL_SENDER") or os.environ.get("SES_SENDER")
            if not sender:
                print("[inove4us] EMAIL_SENDER ausente — código só no log.", file=sys.stderr)
                print(f"[inove4us][DEV-MAIL] Para {recipient}: {access_code}", file=sys.stderr)
                return

            message_body = {
                "Text": {
                    "Data": body_text.replace("\n", "\r\n"),
                    "Charset": "UTF-8",
                }
            }
            if body_html:
                message_body["Html"] = {"Data": body_html, "Charset": "UTF-8"}

            client = boto3.client("ses", region_name=region)
            client.send_email(
                Source=sender,
                Destination={"ToAddresses": [recipient]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": message_body,
                },
            )
            print(f"[inove4us] Código enviado via SES para {recipient}", file=sys.stderr)
        except Exception as exc:
            print(f"[inove4us] Falha SES: {exc}", file=sys.stderr)
            print(f"[inove4us][DEV-MAIL] Para {recipient}: {access_code}", file=sys.stderr)

    threading.Thread(target=_worker, daemon=True, name=f"mail-{recipient}").start()
    return {"sent": True, "channel": "ses"}
