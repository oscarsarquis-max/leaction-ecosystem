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


def send_desafio_convite_email(
    *,
    recipient: str,
    convidado_por_nome: str,
    desafio_titulo: str,
    papel_ou_parte: str | None,
    convite_url: str,
) -> dict:
    """Convite pontual para colaborar em um desafio — reusa SES / EMAIL_DEV_MODE."""
    recipient = (recipient or "").strip().lower()
    convidado_por_nome = (convidado_por_nome or "Um professor").strip()
    desafio_titulo = (desafio_titulo or "Desafio").strip()
    papel = (papel_ou_parte or "").strip()
    frontend = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5174").rstrip("/")
    logo_url = f"{frontend}/imagens/logosombra3.png"

    papel_line = f"Parte sugerida: {papel}\n" if papel else ""
    subject = f"Convite para colaborar — {desafio_titulo[:80]} | inove4us"
    body_text = textwrap.dedent(
        f"""\
        Olá!

        {convidado_por_nome} convidou você para colaborar no desafio:

        «{desafio_titulo}»
        {papel_line}
        Este é um convite pontual para este desafio (não cria uma rede permanente).

        Aceite pelo link (faça login com este e-mail se ainda não tiver sessão):
        {convite_url}

        Se você não esperava este convite, ignore esta mensagem.

        Equipe inove4us
        contato@inove4us.com.br
        """
    ).strip()

    body_html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Segoe UI,system-ui,sans-serif;color:#1c1917;line-height:1.5">
  <p><img src="{logo_url}" alt="inove4us" height="48"/></p>
  <p><strong>{convidado_por_nome}</strong> convidou você para colaborar no desafio:</p>
  <p style="font-size:1.15rem"><em>«{desafio_titulo}»</em></p>
  {"<p>Parte sugerida: <strong>" + papel + "</strong></p>" if papel else ""}
  <p>Convite pontual — só para este desafio.</p>
  <p><a href="{convite_url}" style="display:inline-block;background:#9f1239;color:#fff;padding:12px 20px;border-radius:10px;text-decoration:none;font-weight:700">Ver convite e aceitar</a></p>
  <p style="font-size:12px;color:#78716c">Se o botão não funcionar: {convite_url}</p>
</body></html>"""

    if _dev_mode():
        print(
            f"[inove4us][DEV-MAIL] Convite para {recipient}: {convite_url}",
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
                print("[inove4us] EMAIL_SENDER ausente — convite só no log.", file=sys.stderr)
                print(f"[inove4us][DEV-MAIL] Convite para {recipient}: {convite_url}", file=sys.stderr)
                return

            client = boto3.client("ses", region_name=region)
            client.send_email(
                Source=sender,
                Destination={"ToAddresses": [recipient]},
                Message={
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": body_text.replace("\n", "\r\n"), "Charset": "UTF-8"},
                        "Html": {"Data": body_html, "Charset": "UTF-8"},
                    },
                },
            )
            print(f"[inove4us] Convite enviado via SES para {recipient}", file=sys.stderr)
        except Exception as exc:
            print(f"[inove4us] Falha SES convite: {exc}", file=sys.stderr)
            print(f"[inove4us][DEV-MAIL] Convite para {recipient}: {convite_url}", file=sys.stderr)

    threading.Thread(target=_worker, daemon=True, name=f"convite-{recipient}").start()
    return {"sent": True, "channel": "ses"}
