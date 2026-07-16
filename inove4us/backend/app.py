"""API Flask — inove4us (Mesa do Inovador autônoma)."""

from __future__ import annotations

import os
import re
import sys

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(ROOT, ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

sys.path.insert(0, os.path.dirname(__file__))

from db import (  # noqa: E402
    create_lead_solicitacao,
    find_cliente_by_email,
    upsert_access_code,
    verify_access_code,
)
from mail import send_access_code_email  # noqa: E402
from paneldx_port.inovador_routes import inovador_bp  # noqa: E402
from wizard_routes import wizard_bp  # noqa: E402
from agenda_routes import agenda_bp  # noqa: E402

EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def _valid_email(value: str) -> bool:
    email = (value or "").strip()
    return bool(email) and len(email) <= 254 and bool(EMAIL_RE.match(email))


def _is_solicitacao_ativa(cliente: dict) -> bool:
    """Solicitação ativa = registro com e-mail em ctdi_clie."""
    return bool(cliente and cliente.get("id_clie") and cliente.get("mail_clie"))


def _session_user(cliente: dict) -> dict:
    return {
        "id_clie": cliente["id_clie"],
        "nome_clie": cliente.get("nome_clie") or "",
        "mail_clie": cliente.get("mail_clie") or "",
        "empresa_clie": cliente.get("empresa_clie") or "",
    }


def _grant(cliente: dict, message: str, *, status_code: int = 200, extra: dict | None = None):
    session.permanent = True
    session["user"] = _session_user(cliente)
    payload = {
        "status": "granted",
        "user": session["user"],
        "message": message,
    }
    if extra:
        payload.update(extra)
    return jsonify(payload), status_code


def create_app() -> Flask:
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    # Não usar static_url_path="" — ele sombreia /assets do Vite e devolve 404.
    app = Flask(__name__, static_folder=None)
    is_prod = os.environ.get("FLASK_ENV", "").lower() == "production" or os.environ.get(
        "INOVE4US_ENV", ""
    ).lower() == "production"
    app.secret_key = os.environ.get("SECRET_KEY", "inove4us-dev-secret")
    app.config.update(
        SESSION_COOKIE_NAME="inove4us_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=is_prod,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 14,
    )

    default_origin = (
        "https://inove4us.com.br"
        if is_prod
        else "http://localhost:5174"
    )
    origins = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", default_origin).split(",")
        if o.strip()
    ]
    CORS(app, supports_credentials=True, origins=origins)

    # Oficina do Inovador — cópia fiel do PanelDX (inovador_dashboard + APIs)
    app.register_blueprint(inovador_bp, url_prefix="/inovador")
    # Fluxo guiado Mesa do Inovador (wizard 4 etapas)
    app.register_blueprint(wizard_bp)
    # Agenda executiva (calendário + compromissos)
    app.register_blueprint(agenda_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True, "app": "inove4us", "db": os.environ.get("DB_NAME")})

    @app.get("/api/auth/me")
    def auth_me():
        user = session.get("user")
        if not user:
            return jsonify({"authenticated": False, "user": None})
        return jsonify({"authenticated": True, "user": user})

    @app.post("/api/tracking/enviar")
    def tracking_enviar():
        """Stub local — aceita eventos do sensor sem falhar no console."""
        _ = request.get_json(silent=True) or {}
        return jsonify({"ok": True}), 202

    @app.post("/api/auth/check-email")
    def check_email():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email") or "").strip().lower()
        if not _valid_email(email):
            return jsonify({"error": "Informe um e-mail válido."}), 400

        try:
            cliente = find_cliente_by_email(email)
        except Exception as exc:
            print(f"[inove4us] DB error check-email: {exc}", file=sys.stderr)
            return jsonify({"error": "Falha ao consultar o banco de dados."}), 500

        if cliente and _is_solicitacao_ativa(cliente):
            return _grant(cliente, "Acesso liberado.")

        return jsonify(
            {
                "status": "lead_required",
                "email": email,
                "message": "Complete o cadastro rápido para receber o código de acesso.",
            }
        )

    @app.post("/api/auth/register-lead")
    def register_lead():
        data = request.get_json(silent=True) or {}
        nome = str(data.get("nome") or data.get("nome_clie") or "").strip()
        email = str(data.get("email") or data.get("mail_clie") or "").strip().lower()
        empresa = str(data.get("empresa") or data.get("empresa_clie") or "").strip()

        if not nome:
            return jsonify({"error": "Informe o nome."}), 400
        if not _valid_email(email):
            return jsonify({"error": "Informe um e-mail válido."}), 400
        # empresa é opcional no cadastro freemium

        try:
            existente = find_cliente_by_email(email)
            if existente and _is_solicitacao_ativa(existente):
                return _grant(existente, "Solicitação ativa encontrada. Acesso liberado.", extra={"existing": True})

            cliente = create_lead_solicitacao(nome=nome, email=email, empresa=empresa)
            access_code = upsert_access_code(int(cliente["id_clie"]))
            mail_info = send_access_code_email(email, access_code)
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        except Exception as exc:
            print(f"[inove4us] DB error register-lead: {exc}", file=sys.stderr)
            return jsonify({"error": "Falha ao gravar a solicitação."}), 500

        # Nunca devolver o código na resposta — valida via e-mail
        return jsonify(
            {
                "status": "code_sent",
                "email": email,
                "message": "Código gerado e enviado. Informe-o para entrar.",
                "channel": mail_info.get("channel"),
            }
        ), 201

    @app.post("/api/auth/verify-code")
    def verify_code():
        data = request.get_json(silent=True) or {}
        email = str(data.get("email") or "").strip().lower()
        code = str(data.get("code") or data.get("access_code") or "").strip()

        if not _valid_email(email):
            return jsonify({"error": "Informe um e-mail válido."}), 400
        if not code:
            return jsonify({"error": "Informe o código recebido."}), 400

        try:
            cliente = verify_access_code(email, code)
        except Exception as exc:
            print(f"[inove4us] DB error verify-code: {exc}", file=sys.stderr)
            return jsonify({"error": "Falha ao validar o código."}), 500

        if not cliente:
            return jsonify({"error": "Código inválido para este e-mail."}), 401

        return _grant(cliente, "Código validado. Acesso liberado.")

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify({"ok": True})

    @app.get("/imagens/<path:filename>")
    def serve_imagens(filename: str):
        return send_from_directory(os.path.join(static_dir, "imagens"), filename)

    # SPA React (Vite build) — em produção o Dockerfile gera frontend/dist
    spa_dir = os.environ.get("SPA_DIR") or os.path.join(ROOT, "frontend", "dist")
    if os.path.isdir(spa_dir):

        @app.get("/", defaults={"path": ""})
        @app.get("/<path:path>")
        def spa_fallback(path: str):
            # /api e /inovador já têm rotas próprias; /imagens tem rota dedicada
            if path.startswith("api/") or path.startswith("inovador"):
                return jsonify({"error": "Not found"}), 404
            candidate = os.path.join(spa_dir, path)
            if path and os.path.isfile(candidate):
                return send_from_directory(spa_dir, path)
            return send_from_directory(spa_dir, "index.html")

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", os.environ.get("PORT", "5010")))
    app.run(host="0.0.0.0", port=port, debug=not os.environ.get("INOVE4US_ENV") == "production")
