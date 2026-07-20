"""Rotas /gatekeeper/* e /manutencao — mesmo contrato do mudaedu/PanelDX."""

from __future__ import annotations

import hmac
import os
import re

from flask import Blueprint, jsonify, redirect, request, session

from system_config import is_system_locked, lock_system, unlock_system

gatekeeper_bp = Blueprint("gatekeeper", __name__)

_STATIC_EXT = re.compile(r"\.(png|jpe?g|gif|svg|ico|webp|css|js|map|woff2?|ttf)$", re.I)


def _master_key() -> str:
    return (os.environ.get("PRODUCTION_MASTER_KEY") or "").strip()


def _admin_enabled() -> bool:
    env = (os.environ.get("INOVE4US_ENV") or os.environ.get("FLASK_ENV") or "").lower()
    if env == "production" or (os.environ.get("NODE_ENV") or "").lower() == "production":
        return True
    return (os.environ.get("GATEKEEPER_ALLOW_DEV") or "").lower() == "true"


def _is_production() -> bool:
    env = (os.environ.get("INOVE4US_ENV") or os.environ.get("FLASK_ENV") or "").lower()
    return env == "production"


def _valid_secret(provided: str | None) -> bool:
    expected = _master_key()
    got = (provided or "").strip()
    if not expected or not got:
        return False
    return hmac.compare_digest(expected, got)


def _is_exempt(path: str) -> bool:
    if path in ("/manutencao", "/api/health", "/favicon.ico"):
        return True
    if path.startswith("/gatekeeper"):
        return True
    if path.startswith("/api/webhooks/"):
        return True
    # Action-Sponge sensor (proxy → Hub) mesmo com site em manutenção
    if path.startswith("/api/tracking/"):
        return True
    if path.startswith("/assets/") or path.startswith("/imagens/") or path.startswith("/static/"):
        return True
    if _STATIC_EXT.search(path or ""):
        return True
    return False


_MANUTENCAO_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="robots" content="noindex, nofollow"/>
  <title>inove4us — Em preparação</title>
  <style>
    body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;
      font-family:Segoe UI,system-ui,sans-serif;color:#0f172a;
      background:radial-gradient(circle at 20% 20%,rgba(217,119,6,.12),transparent 40%),
      radial-gradient(circle at 80% 0%,rgba(14,165,233,.10),transparent 35%),
      linear-gradient(160deg,#fff7ed 0%,#f0f9ff 100%)}
    .card{width:min(560px,100%);background:#fff;border:1px solid #e2e8f0;border-left:6px solid #ea580c;
      border-radius:20px;padding:36px 32px;text-align:center;box-shadow:0 20px 50px rgba(15,23,42,.08)}
    h1{margin:0 0 10px;font-size:1.65rem;color:#c2410c}
    p{margin:0;color:#64748b;line-height:1.6}
    .brand{letter-spacing:.12em;font-size:12px;color:#ea580c;margin:0 0 8px}
  </style>
</head>
<body>
  <section class="card">
    <p class="brand">INOVE4US</p>
    <h1>Em preparação</h1>
    <p>Estamos finalizando o lançamento. Em breve a Mesa do Inovador estará disponível para todos os clientes.</p>
  </section>
</body>
</html>
"""


@gatekeeper_bp.get("/manutencao")
def manutencao():
    return _MANUTENCAO_HTML, 200, {"Content-Type": "text/html; charset=utf-8"}


@gatekeeper_bp.get("/gatekeeper/bypass")
def bypass():
    if not _admin_enabled():
        return (
            "Rotas de homologação disponíveis apenas em produção. "
            "Em dev, defina GATEKEEPER_ALLOW_DEV=true.",
            403,
        )
    if not _master_key() or not _valid_secret(request.args.get("secret")):
        return "Acesso negado.", 403
    session.permanent = True
    session["is_admin_tester"] = True
    # Evita redirect absoluto para localhost atrás do ALB/proxy
    public = (os.environ.get("FRONTEND_ORIGIN") or "https://inove4us.com.br").rstrip("/")
    return redirect(f"{public}/")


@gatekeeper_bp.get("/gatekeeper/unlock")
def unlock():
    if not _admin_enabled():
        return (
            "Rotas de homologação disponíveis apenas em produção. "
            "Em dev, defina GATEKEEPER_ALLOW_DEV=true.",
            403,
        )
    if not _master_key() or not _valid_secret(request.args.get("secret")):
        return "Acesso negado.", 403
    try:
        unlock_system()
        return "Sistema liberado para uso geral!", 200
    except Exception as exc:
        print(f"[Gatekeeper] unlock: {exc}")
        return "Falha ao liberar o sistema. Verifique a conexão com o banco.", 500


@gatekeeper_bp.get("/gatekeeper/lock")
def lock():
    if not _admin_enabled():
        return (
            "Rotas de homologação disponíveis apenas em produção. "
            "Em dev, defina GATEKEEPER_ALLOW_DEV=true.",
            403,
        )
    if not _master_key() or not _valid_secret(request.args.get("secret")):
        return "Acesso negado.", 403
    try:
        lock_system()
        return "Sistema BLOQUEADO. Tela de manutenção ativada para o público.", 200
    except Exception as exc:
        print(f"[Gatekeeper] lock: {exc}")
        return "Falha ao bloquear o sistema. Verifique a conexão com o banco.", 500


@gatekeeper_bp.get("/gatekeeper/status")
def status():
    try:
        return jsonify({"locked": is_system_locked(), "app": "inove4us"})
    except Exception:
        return jsonify({"locked": _is_production(), "app": "inove4us"})


def register_gatekeeper(app):
    """Registra blueprint + before_request de bloqueio."""

    app.register_blueprint(gatekeeper_bp)

    @app.before_request
    def _gatekeeper_guard():
        path = request.path or "/"
        if _is_exempt(path):
            return None

        ua = request.headers.get("User-Agent") or ""
        if "ELB-HealthChecker" in ua:
            return None

        try:
            locked = is_system_locked()
        except Exception as exc:
            print(f"[Gatekeeper] status fail: {exc}")
            locked = _is_production()

        if not locked:
            return None

        if session.get("is_admin_tester") is True:
            return None

        wants_json = (
            path.startswith("/api/")
            or "application/json" in (request.headers.get("Accept") or "")
            or bool(request.is_json)
        )
        if wants_json:
            return (
                jsonify(
                    {
                        "error": "Sistema em preparação para lançamento.",
                        "maintenance": True,
                    }
                ),
                503,
            )
        return redirect("/manutencao")
