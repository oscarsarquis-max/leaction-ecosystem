"""
Envio de roteiro/plano de aula por Amazon SES (região us-east-2 / Ohio).
"""

from __future__ import annotations

import html
import logging
import os
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger("mativas.email_service")

SES_REGION = "us-east-2"
FROM_EMAIL = "roteiro@metodologiasinovativas.com.br"
SITE_URL = os.environ.get("SITE_URL", "https://metodologiasinovativas.com.br").rstrip("/")
CAPA_LIVRO_URL = os.environ.get("EMAIL_CAPA_LIVRO_URL", "").strip()

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_BRAND_DIR = _ASSETS_DIR / "brand"
_LOGO_PNG_PATHS = (
    _BRAND_DIR / "logo.png",
    _ASSETS_DIR / "logo.png",
)

# Cores e estilos alinhados a frontend/src/index.css
_COLOR_PRIMARY = "#4f46e5"
_COLOR_PRIMARY_DARK = "#3b28cc"
_COLOR_PRIMARY_SOFT = "#f3f0ff"
_COLOR_SECONDARY = "#e11d48"
_COLOR_TEXT = "#333333"
_COLOR_MUTED = "#6b7280"
_COLOR_BORDER = "#e9e7f5"

_STEP_ICON_STYLES = (
    {"bg": "#f3f0ff", "color": _COLOR_PRIMARY},
    {"bg": "#fde7ee", "color": _COLOR_SECONDARY},
    {"bg": "#e6effd", "color": "#3b82f6"},
    {"bg": "#e3f5ea", "color": "#16a34a"},
)

_LOGO_CID = "brand-logo"


def _esc(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def _carregar_logo_png() -> bytes | None:
    for path in _LOGO_PNG_PATHS:
        if path.is_file():
            return path.read_bytes()
    return None


def _logo_header_html(logo_src: str | None) -> str:
    if logo_src:
        return (
            f'<img src="{_esc(logo_src)}" alt="Metodologias Inov-ativas" width="280" '
            f'style="display:block;border:0;max-width:280px;width:100%;height:auto;" />'
        )

    logo_url = os.environ.get("EMAIL_LOGO_URL", "").strip()
    if not logo_url:
        logo_url = f"{SITE_URL}/brand/logo.png"
    if logo_url and not logo_url.lower().endswith(".svg"):
        return (
            f'<img src="{_esc(logo_url)}" alt="Metodologias Inov-ativas" width="280" '
            f'style="display:block;border:0;max-width:280px;width:100%;height:auto;" />'
        )

    return (
        f'<div style="line-height:1.2;font-family:\'Segoe UI\',Arial,sans-serif;">'
        f'<div style="font-size:14px;font-weight:600;color:{_COLOR_PRIMARY};">metodologias</div>'
        f'<div style="margin-top:4px;">'
        f'<span style="display:inline-block;background:{_COLOR_SECONDARY};color:#ffffff;'
        f'font-size:16px;font-weight:800;padding:3px 8px;border-radius:5px;">INOV-</span>'
        f'<span style="font-size:18px;font-weight:800;color:{_COLOR_PRIMARY};margin-left:2px;">ativas</span>'
        f"</div>"
        f"</div>"
    )


def _bloco_rationale(titulo: str, conteudo_html: str, extra_style: str = "") -> str:
    return (
        f'<div style="margin:14px 0 4px;padding:12px 14px;border-radius:12px;'
        f"background:{_COLOR_PRIMARY_SOFT};border:1px solid {_COLOR_BORDER};{extra_style}\">"
        f'<div style="font-weight:700;font-size:13px;color:{_COLOR_PRIMARY_DARK};margin-bottom:6px;">'
        f"{titulo}</div>"
        f"{conteudo_html}"
        f"</div>"
    )


def _render_passos(passos: list) -> str:
    blocos = []
    for i, passo in enumerate(passos, start=1):
        if not isinstance(passo, dict):
            continue
        titulo = _esc(passo.get("titulo") or f"Passo {i}")
        desc = _esc(passo.get("descricao") or passo.get("desc") or "")
        tempo = _esc(passo.get("tempo") or "")
        estilo = _STEP_ICON_STYLES[(i - 1) % len(_STEP_ICON_STYLES)]
        tempo_html = (
            f'<div style="font-size:13px;color:{_COLOR_MUTED};margin-top:2px;">&#9201; {tempo}</div>'
            if tempo
            else ""
        )
        blocos.append(
            f'<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">'
            f"<tr>"
            f'<td width="34" valign="top" style="padding-right:12px;">'
            f'<div style="width:34px;height:34px;border-radius:8px;background:{_COLOR_PRIMARY};'
            f'color:#ffffff;text-align:center;line-height:34px;font-weight:700;font-size:14px;">{i}</div>'
            f"</td>"
            f'<td width="42" valign="top" style="padding-right:12px;">'
            f'<div style="width:42px;height:42px;border-radius:50%;background:{estilo["bg"]};'
            f'color:{estilo["color"]};text-align:center;line-height:42px;font-weight:700;font-size:16px;">'
            f"&#9679;</div>"
            f"</td>"
            f'<td valign="top" style="color:{_COLOR_TEXT};">'
            f'<div style="font-weight:700;font-size:15px;line-height:1.35;">{titulo}</div>'
            f"{tempo_html}"
            f'<div style="font-size:14px;color:{_COLOR_MUTED};line-height:1.55;margin-top:3px;">{desc}</div>'
            f"</td>"
            f"</tr></table>"
        )
    return "".join(blocos) or (
        f'<p style="margin:0;color:{_COLOR_MUTED};font-size:14px;">Conteúdo do roteiro indisponível.</p>'
    )


def _montar_html(roteiro_content: dict, project_id: int, *, logo_src: str | None = None) -> str:
    """Monta o corpo HTML do e-mail espelhando a página Roteiro da aplicação."""
    nome = _esc(roteiro_content.get("nome") or "Professor(a)")
    metodologia = _esc(roteiro_content.get("metodologia") or "Metodologia Inov-ativa")
    justificativa = _esc(roteiro_content.get("justificativa") or "")
    passos = roteiro_content.get("passos") or []

    ctx = roteiro_content.get("contexto") or {}
    ctx_linhas = []
    if ctx.get("desafio"):
        ctx_linhas.append(f"<li><strong>Desafio:</strong> {_esc(ctx['desafio'])}</li>")
    if ctx.get("nivel"):
        ctx_linhas.append(f"<li><strong>Nível de ensino:</strong> {_esc(ctx['nivel'])}</li>")
    if ctx.get("formato"):
        ctx_linhas.append(f"<li><strong>Modalidade:</strong> {_esc(ctx['formato'])}</li>")
    if ctx.get("participantes"):
        ctx_linhas.append(
            f"<li><strong>Participantes:</strong> {_esc(ctx['participantes'])}</li>"
        )

    contexto_html = ""
    if ctx_linhas:
        contexto_html = _bloco_rationale(
            "Contexto do seu relato",
            f'<ul style="margin:0;padding-left:18px;color:{_COLOR_TEXT};font-size:14px;line-height:1.55;">'
            f'{"".join(ctx_linhas)}</ul>',
            extra_style="margin-bottom:12px;",
        )

    justificativa_html = ""
    if justificativa:
        justificativa_html = _bloco_rationale(
            "Por que esta metodologia?",
            f'<p style="margin:0;font-size:14px;line-height:1.5;color:{_COLOR_TEXT};">{justificativa}</p>',
        )

    passos_html = _render_passos(passos)
    logo_html = _logo_header_html(logo_src)
    capa_html = ""
    if CAPA_LIVRO_URL:
        capa_html = (
            f'<img src="{_esc(CAPA_LIVRO_URL)}" alt="Capa do livro Metodologias inov-ativas na educação" '
            f'width="220" style="display:block;max-width:220px;width:100%;border-radius:12px;'
            f'box-shadow:0 4px 16px rgba(79,70,229,0.08);" />'
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Seu Roteiro de Aulas — Metodologias Inov-ativas</title>
</head>
<body style="margin:0;padding:0;background:#ffffff;font-family:'Segoe UI',system-ui,Arial,sans-serif;color:{_COLOR_TEXT};">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#ffffff;padding:24px 12px 32px;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0" style="max-width:480px;width:100%;">

        <tr>
          <td style="padding:0 6px 18px;">
            {logo_html}
          </td>
        </tr>

        <tr>
          <td style="padding:0 6px 18px;">
            <h1 style="margin:0 0 14px;font-size:24px;font-weight:800;color:{_COLOR_TEXT};line-height:1.25;">
              Olá, {nome}.
            </h1>
            <p style="margin:0 0 14px;font-size:15px;line-height:1.55;color:{_COLOR_MUTED};">
              Com base no desafio que você compartilhou, elaboramos um Roteiro de Aulas inspirado na metodologia
              <strong style="color:{_COLOR_PRIMARY};">{metodologia}</strong>.
            </p>
            <p style="margin:0 0 16px;font-size:15px;line-height:1.55;color:{_COLOR_MUTED};">
              Esperamos que ele ajude você a promover mais participação, engajamento e protagonismo dos estudantes.
            </p>
            {capa_html}
          </td>
        </tr>

        <tr>
          <td style="padding:0 6px;">
            <table width="100%" cellpadding="0" cellspacing="0"
              style="background:#ffffff;border:1px solid {_COLOR_BORDER};border-radius:16px;padding:18px;box-shadow:0 2px 8px rgba(51,51,51,0.05);">
              <tr>
                <td>
                  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
                    <tr>
                      <td width="48" valign="middle" style="padding-right:12px;">
                        <div style="width:48px;height:48px;border-radius:12px;background:{_COLOR_PRIMARY_SOFT};color:{_COLOR_PRIMARY};text-align:center;line-height:48px;font-size:22px;">&#128203;</div>
                      </td>
                      <td valign="middle">
                        <div style="font-size:19px;font-weight:800;color:{_COLOR_PRIMARY_DARK};line-height:1.2;">
                          Seu Roteiro de Aulas
                        </div>
                        <div style="font-size:14px;font-weight:600;color:{_COLOR_SECONDARY};margin-top:4px;">
                          Metodologia recomendada: {metodologia}
                        </div>
                      </td>
                    </tr>
                  </table>

                  {contexto_html}
                  {justificativa_html}

                  <h3 style="margin:20px 0 10px;font-size:15px;font-weight:700;color:{_COLOR_PRIMARY};">
                    Passo a passo
                  </h3>
                  {passos_html}

                  <p style="margin:20px 0 0;font-size:12px;line-height:1.55;color:{_COLOR_MUTED};">
                    Roteiro baseado nas estratégias do livro
                    <em>Metodologias inov-ativas na educação</em>, de Andrea Filatro.
                  </p>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:20px 6px 0;text-align:center;">
            <a href="{_esc(SITE_URL)}"
              style="display:inline-block;background:{_COLOR_PRIMARY};color:#ffffff;text-decoration:none;padding:12px 20px;border-radius:10px;font-weight:600;font-size:14px;">
              Acessar Metodologias Inov-ativas
            </a>
            <p style="margin:14px 0 0;font-size:11px;color:#94a3b8;">
              Referência do roteiro: #{project_id}
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _enviar_ses(destinatario: str, assunto: str, html_body: str, logo_png: bytes | None) -> dict:
    client = boto3.client("ses", region_name=SES_REGION)

    if logo_png:
        msg = MIMEMultipart("related")
        msg["Subject"] = assunto
        msg["From"] = FROM_EMAIL
        msg["To"] = destinatario

        alternative = MIMEMultipart("alternative")
        alternative.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(alternative)

        image = MIMEImage(logo_png, _subtype="png")
        image.add_header("Content-ID", f"<{_LOGO_CID}>")
        image.add_header("Content-Disposition", "inline", filename="logo.png")
        msg.attach(image)

        response = client.send_raw_email(
            Source=FROM_EMAIL,
            Destinations=[destinatario],
            RawMessage={"Data": msg.as_string()},
        )
    else:
        response = client.send_email(
            Source=FROM_EMAIL,
            Destination={"ToAddresses": [destinatario]},
            Message={
                "Subject": {"Data": assunto, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            },
        )

    return response


def send_roteiro_email(
    to_email: str,
    roteiro_content: dict,
    project_id: int,
    *,
    modo: str = "manual",
) -> dict:
    """
    Envia o roteiro por Amazon SES.

    :param to_email: destinatário
    :param roteiro_content: dict com nome, metodologia, justificativa, passos, contexto
    :param project_id: identificador do projeto/roteiro (roteiros.id)
    :param modo: 'automatico' (uma vez por roteiro) ou 'manual' (reenvio)
    :returns: dict com message_id e metadados do SES
    :raises ValueError: e-mail inválido
    :raises ClientError: falha na API SES
    """
    from email_idempotency import (
        atualizar_message_id_envio_automatico,
        pode_enviar_manual,
        registrar_envio_manual,
        reservar_envio_automatico,
    )

    destinatario = (to_email or "").strip().lower()
    if not destinatario or "@" not in destinatario:
        raise ValueError("E-mail de destino inválido.")

    roteiro_id = int(project_id or 0)
    modo_norm = (modo or "manual").strip().lower()

    if roteiro_id > 0 and modo_norm == "automatico":
        if not reservar_envio_automatico(roteiro_id, destinatario):
            return {
                "skipped": True,
                "motivo": "envio_automatico_ja_registrado",
                "destinatario": destinatario,
                "project_id": roteiro_id,
            }
    elif roteiro_id > 0 and modo_norm == "manual":
        if not pode_enviar_manual(roteiro_id, destinatario):
            return {
                "skipped": True,
                "motivo": "reenvio_manual_recente",
                "destinatario": destinatario,
                "project_id": roteiro_id,
            }

    logo_png = _carregar_logo_png()
    logo_src = f"cid:{_LOGO_CID}" if logo_png else None
    html_body = _montar_html(roteiro_content or {}, roteiro_id, logo_src=logo_src)
    assunto = "Seu Roteiro de Aulas — Metodologias Inov-ativas"

    try:
        response = _enviar_ses(destinatario, assunto, html_body, logo_png)
    except (ClientError, BotoCoreError):
        logger.exception(
            "Falha SES ao enviar roteiro (project_id=%s, to=%s, modo=%s)",
            roteiro_id,
            destinatario,
            modo_norm,
        )
        raise

    message_id = response.get("MessageId")
    logger.info(
        "E-mail enviado via SES (project_id=%s, to=%s, message_id=%s, modo=%s, logo_inline=%s)",
        roteiro_id,
        destinatario,
        message_id,
        modo_norm,
        bool(logo_png),
    )

    if roteiro_id > 0:
        if modo_norm == "automatico":
            atualizar_message_id_envio_automatico(roteiro_id, destinatario, message_id)
        else:
            registrar_envio_manual(roteiro_id, destinatario, message_id)

    return {
        "message_id": message_id,
        "destinatario": destinatario,
        "project_id": roteiro_id,
        "origem": FROM_EMAIL,
        "regiao": SES_REGION,
        "modo": modo_norm,
    }
