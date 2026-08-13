"""Envio do código de acesso (AWS SES) — identidade inove4us."""

from __future__ import annotations

import os
import sys
import textwrap
import threading
from pathlib import Path


def _dev_mode() -> bool:
    return os.environ.get("EMAIL_DEV_MODE", "").strip() in ("1", "true", "True", "yes")


def _frontend_origin() -> str:
    return (os.environ.get("FRONTEND_ORIGIN") or "http://localhost:5174").rstrip("/")


def _public_web_origin() -> str:
    """Origem pública para assets em e-mail (clientes não abrem localhost)."""
    explicit = (
        os.environ.get("EMAIL_ASSET_ORIGIN")
        or os.environ.get("PUBLIC_WEB_ORIGIN")
        or ""
    ).strip().rstrip("/")
    if explicit:
        return explicit
    frontend = _frontend_origin()
    low = frontend.lower()
    if "localhost" in low or "127.0.0.1" in low or low.startswith("http://192.168."):
        return "https://inove4us.com.br"
    return frontend


def _email_logo_url() -> str:
    explicit = (os.environ.get("EMAIL_LOGO_URL") or "").strip()
    if explicit:
        return explicit
    return f"{_public_web_origin()}/imagens/logosombra3.png"


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
    frontend = _frontend_origin()
    access_url = f"{frontend}/acesso"
    logo_url = _email_logo_url()

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
                os.environ.get("SES_REGION")
                or os.environ.get("AWS_REGION")
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
            print(
                f"[inove4us] Código enviado via SES ({region}) de {sender} para {recipient}",
                file=sys.stderr,
            )
        except Exception as exc:
            print(f"[inove4us] Falha SES: {exc}", file=sys.stderr)
            print(f"[inove4us][DEV-MAIL] Para {recipient}: {access_code}", file=sys.stderr)

    threading.Thread(target=_worker, daemon=True, name=f"mail-{recipient}").start()
    return {"sent": True, "channel": "ses"}


def send_school_gestor_credentials_email(
    *,
    recipient: str,
    password: str,
    acesso_url: str,
    razao_social: str | None = None,
) -> dict:
    """E-mail de credencial do gestor School (self-serve). Reusa SES / EMAIL_DEV_MODE.

    Em produção não registra a senha no log. Em EMAIL_DEV_MODE o texto plano
    vai ao stderr para teste local.
    """
    recipient = (recipient or "").strip().lower()
    password = (password or "").strip()
    acesso_url = (acesso_url or "https://school.inove4us.com.br/acesso").strip()
    escola = (razao_social or "sua escola").strip() or "sua escola"
    logo_url = _email_logo_url()

    if not recipient or "@" not in recipient or not password:
        return {"sent": False, "channel": "none", "error": "destinatário ou senha ausente"}

    subject = "Acesso à Torre de Controle | inove4us School"
    body_text = textwrap.dedent(
        f"""\
        Olá!

        A conta da instituição {escola} foi criada na Torre de Controle inove4us School.

        Login (e-mail): {recipient}
        Senha temporária (uso único): {password}

        Acesse: {acesso_url}

        Recomendamos alterar a senha no primeiro acesso.

        Se você não solicitou este cadastro, ignore esta mensagem.

        Equipe inove4us
        contato@inove4us.com.br
        """
    ).strip()

    def _esc(s: str) -> str:
        return (
            (s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )

    body_html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Segoe UI,system-ui,sans-serif;color:#1c1917;line-height:1.5">
  <p><img src="{logo_url}" alt="inove4us" width="180" height="48" style="display:block;max-width:180px;height:auto;border:0;outline:none;text-decoration:none"/></p>
  <p>A conta da instituição <strong>{_esc(escola)}</strong> foi criada na Torre de Controle inove4us School.</p>
  <p>Login (e-mail): <strong>{_esc(recipient)}</strong></p>
  <p>Senha temporária (uso único): <strong>{_esc(password)}</strong></p>
  <p><a href="{_esc(acesso_url)}" style="display:inline-block;background:#9f1239;color:#fff;padding:12px 20px;border-radius:10px;text-decoration:none;font-weight:700">Acessar a Torre de Controle</a></p>
  <p style="font-size:12px;color:#78716c">Se o botão não funcionar: {_esc(acesso_url)}</p>
  <p>Recomendamos alterar a senha no primeiro acesso.</p>
</body></html>"""

    if _dev_mode():
        print(
            f"[inove4us][DEV-MAIL] School gestor {recipient} senha={password} url={acesso_url}",
            file=sys.stderr,
        )
        return {"sent": True, "channel": "dev_log"}

    try:
        import boto3

        region = (
            os.environ.get("SES_REGION")
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or "us-east-2"
        )
        sender = os.environ.get("EMAIL_SENDER") or os.environ.get("SES_SENDER")
        if not sender:
            print(
                "[inove4us] EMAIL_SENDER ausente — credencial School não enviada.",
                file=sys.stderr,
            )
            return {"sent": False, "channel": "dev_log", "error": "EMAIL_SENDER ausente"}

        client = boto3.client("ses", region_name=region)
        resp = client.send_email(
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
        message_id = resp.get("MessageId")
        print(
            f"[inove4us] Credencial School enviada via SES ({region}) de {sender} para {recipient} id={message_id}",
            file=sys.stderr,
        )
        return {"sent": True, "channel": "ses", "message_id": message_id, "region": region}
    except Exception as exc:
        print(f"[inove4us] Falha SES credencial School: {exc}", file=sys.stderr)
        return {"sent": False, "channel": "ses", "error": str(exc)}


def send_desafio_convite_email(
    *,
    recipient: str,
    convidado_por_nome: str,
    desafio_titulo: str,
    papel_ou_parte: str | None,
    convite_url: str,
    desafio_descricao: str | None = None,
    card_titulo: str | None = None,
    card_descricao: str | None = None,
) -> dict:
    """Convite pontual multidisciplinar — e-mail começa pelo desafio e pelo card."""
    recipient = (recipient or "").strip().lower()
    convidado_por_nome = (convidado_por_nome or "Um professor").strip()
    desafio_titulo = (desafio_titulo or "Desafio").strip()
    desafio_desc = (desafio_descricao or desafio_titulo).strip()
    card_tit = (card_titulo or "").strip()
    card_desc = (card_descricao or card_tit).strip()
    papel = (papel_ou_parte or card_tit).strip()
    logo_url = _email_logo_url()
    subject = f"Convite multidisciplinar — {desafio_titulo[:80]} | inove4us"
    body_text = textwrap.dedent(
        f"""\
        Olá!

        === DESAFIO ===
        {desafio_desc}

        === CARD ASSOCIADO ===
        {card_desc or "(card a combinar)"}

        {convidado_por_nome} convidou você (e-mail: {recipient}) para colaborar neste desafio multidisciplinar.
        Ao aceitar com um clique, o desafio entra no seu mapa de realizações.
        Depois você planeja as suas aulas — o outro professor não vê o seu planejamento.

        Aceite pelo link (faça login com este e-mail se ainda não tiver sessão):
        {convite_url}

        Se você não esperava este convite, ignore esta mensagem.

        Equipe inove4us
        contato@inove4us.com.br
        """
    ).strip()

    def _esc(s: str) -> str:
        return (
            (s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )

    body_html = f"""<!DOCTYPE html>
<html lang="pt-BR"><body style="font-family:Segoe UI,system-ui,sans-serif;color:#1c1917;line-height:1.5">
  <p><img src="{logo_url}" alt="inove4us" width="180" height="48" style="display:block;max-width:180px;height:auto;border:0;outline:none;text-decoration:none"/></p>
  <h2 style="margin:0 0 8px;font-size:14px;letter-spacing:.12em;text-transform:uppercase;color:#9f1239">Desafio</h2>
  <p style="margin:0 0 16px;white-space:pre-wrap">{_esc(desafio_desc)}</p>
  <h2 style="margin:0 0 8px;font-size:14px;letter-spacing:.12em;text-transform:uppercase;color:#9f1239">Card associado</h2>
  <p style="margin:0 0 16px;white-space:pre-wrap">{_esc(card_desc or card_tit or "Card a combinar")}</p>
  <p><strong>{_esc(convidado_por_nome)}</strong> convidou <strong>{_esc(recipient)}</strong> para este desafio multidisciplinar.</p>
  <p>Com um clique o desafio entra no seu mapa. Depois você planeja as suas aulas — o planejamento de cada professor fica isolado.</p>
  {"<p>Parte: <strong>" + _esc(papel) + "</strong></p>" if papel else ""}
  <p><a href="{convite_url}" style="display:inline-block;background:#9f1239;color:#fff;padding:12px 20px;border-radius:10px;text-decoration:none;font-weight:700">Aceitar e adicionar ao meu mapa</a></p>
  <p style="font-size:12px;color:#78716c">Se o botão não funcionar: {convite_url}</p>
</body></html>"""

    if _dev_mode():
        print(
            f"[inove4us][DEV-MAIL] Convite para {recipient}: {convite_url}",
            file=sys.stderr,
        )
        return {"sent": True, "channel": "dev_log"}

    try:
        import boto3

        region = (
            os.environ.get("SES_REGION")
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
            or "us-east-2"
        )
        sender = os.environ.get("EMAIL_SENDER") or os.environ.get("SES_SENDER")
        if not sender:
            print("[inove4us] EMAIL_SENDER ausente — convite só no log.", file=sys.stderr)
            print(f"[inove4us][DEV-MAIL] Convite para {recipient}: {convite_url}", file=sys.stderr)
            return {"sent": False, "channel": "dev_log", "error": "EMAIL_SENDER ausente"}

        client = boto3.client("ses", region_name=region)
        resp = client.send_email(
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
        message_id = resp.get("MessageId")
        print(
            f"[inove4us] Convite enviado via SES ({region}) de {sender} para {recipient} id={message_id}",
            file=sys.stderr,
        )
        return {"sent": True, "channel": "ses", "message_id": message_id, "region": region}
    except Exception as exc:
        print(f"[inove4us] Falha SES convite: {exc}", file=sys.stderr)
        print(f"[inove4us][DEV-MAIL] Convite para {recipient}: {convite_url}", file=sys.stderr)
        return {
            "sent": False,
            "channel": "dev_log",
            "error": str(exc),
            "convite_url_fallback": convite_url,
        }
