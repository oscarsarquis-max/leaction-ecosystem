"""
Envio de e-mail com o roteiro gerado (HTML com identidade visual).
Ativo quando SMTP_HOST estiver configurado no ambiente.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SITE_URL = os.environ.get("SITE_URL", "https://metodologiasinovativas.com.br")
LOGO_URL = os.environ.get(
    "EMAIL_LOGO_URL",
    f"{SITE_URL.rstrip('/')}/assets/capa-livro-2aJT9QNo.png",
)
FROM_EMAIL = os.environ.get("SMTP_FROM", "noreply@metodologiasinovativas.com.br")
FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Metodologias Inov-ativas")


def _smtp_configurado():
    return bool(os.environ.get("SMTP_HOST"))


def _montar_html(nome, metodologia, justificativa, passos, contexto):
    passos_html = ""
    for i, passo in enumerate(passos or [], start=1):
        titulo = passo.get("titulo") or f"Passo {i}"
        desc = passo.get("descricao") or passo.get("desc") or ""
        tempo = passo.get("tempo") or ""
        tempo_html = f' <span style="color:#6b7280;">({tempo})</span>' if tempo else ""
        passos_html += (
            f'<li style="margin-bottom:12px;">'
            f'<strong>{i}. {titulo}</strong>{tempo_html}<br/>'
            f'<span style="color:#374151;">{desc}</span></li>'
        )

    ctx = contexto or {}
    ctx_linhas = []
    if ctx.get("desafio"):
        ctx_linhas.append(f"<li><strong>Desafio:</strong> {ctx['desafio']}</li>")
    if ctx.get("nivel"):
        ctx_linhas.append(f"<li><strong>Nível de ensino:</strong> {ctx['nivel']}</li>")
    if ctx.get("formato"):
        ctx_linhas.append(f"<li><strong>Modalidade:</strong> {ctx['formato']}</li>")
    if ctx.get("participantes"):
        ctx_linhas.append(
            f"<li><strong>Participantes:</strong> {ctx['participantes']}</li>"
        )
    contexto_html = (
        f'<ul style="padding-left:18px;color:#374151;">{"".join(ctx_linhas)}</ul>'
        if ctx_linhas
        else ""
    )

    justificativa_html = (
        f'<h2 style="color:#4f46e5;font-size:15px;margin:24px 0 8px;">Por que esta metodologia?</h2>'
        f'<p style="color:#374151;line-height:1.6;">{justificativa}</p>'
        if justificativa
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Seu Roteiro de Aulas</title></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:Segoe UI,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:24px 12px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(15,23,42,.08);">
        <tr>
          <td style="background:linear-gradient(135deg,#4f46e5,#3b28cc);padding:24px;text-align:center;">
            <img src="{LOGO_URL}" alt="Metodologias Inov-ativas" width="88" style="border-radius:8px;margin-bottom:12px;" />
            <h1 style="margin:0;color:#ffffff;font-size:22px;">Seu Roteiro de Aulas</h1>
            <p style="margin:8px 0 0;color:#e0e7ff;font-size:14px;">Metodologias Inov-ativas na Educação</p>
          </td>
        </tr>
        <tr>
          <td style="padding:28px 24px;">
            <p style="margin:0 0 16px;color:#111827;font-size:16px;">Olá, <strong>{nome or 'Professor(a)'}</strong>!</p>
            <p style="margin:0 0 20px;color:#374151;line-height:1.6;">
              Segue o roteiro personalizado com base no desafio que você compartilhou.
            </p>
            {f'<h2 style="color:#4f46e5;font-size:15px;margin:24px 0 8px;">Contexto do seu relato</h2>{contexto_html}' if contexto_html else ''}
            <h2 style="color:#e11d48;font-size:15px;margin:24px 0 8px;">Metodologia recomendada</h2>
            <p style="margin:0 0 8px;font-size:18px;font-weight:700;color:#111827;">{metodologia}</p>
            {justificativa_html}
            <h2 style="color:#4f46e5;font-size:15px;margin:24px 0 12px;">Passo a passo</h2>
            <ol style="padding-left:20px;margin:0;">{passos_html}</ol>
            <p style="margin:28px 0 0;color:#6b7280;font-size:12px;line-height:1.5;">
              Roteiro baseado nas estratégias do livro <em>Metodologias inov-ativas na educação</em>, de Andrea Filatro.
            </p>
            <p style="margin:16px 0 0;text-align:center;">
              <a href="{SITE_URL}" style="display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;padding:12px 20px;border-radius:8px;font-weight:600;">Acessar a plataforma</a>
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def enviar_roteiro_por_email(destinatario, nome, metodologia, justificativa, passos, contexto=None):
    """Envia o roteiro por e-mail via Amazon SES (ou SMTP legado se configurado)."""
    if not destinatario:
        return False

    if _smtp_configurado():
        host = os.environ["SMTP_HOST"]
        port = int(os.environ.get("SMTP_PORT", "587"))
        user = os.environ.get("SMTP_USER", "")
        password = os.environ.get("SMTP_PASSWORD", "")
        use_tls = os.environ.get("SMTP_USE_TLS", "1") == "1"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Seu Roteiro de Aulas — Metodologias Inov-ativas"
        msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg["To"] = destinatario

        html = _montar_html(nome, metodologia, justificativa, passos, contexto)
        msg.attach(MIMEText(html, "html", "utf-8"))

        with smtplib.SMTP(host, port, timeout=30) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(FROM_EMAIL, [destinatario], msg.as_string())
        return True

    from email_service import send_roteiro_email

    send_roteiro_email(
        destinatario,
        {
            "nome": nome,
            "metodologia": metodologia,
            "justificativa": justificativa,
            "passos": passos,
            "contexto": contexto or {},
        },
        int(project_id or 0),
        modo="automatico",
    )
    return True
