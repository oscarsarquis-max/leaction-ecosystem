"""Trava pública do School — mesmo contrato do Inove/Hub (bypass + lock/unlock).

Público vê /manutencao. Oscar verifica com /gatekeeper/bypass?secret=MASTER.
Estado: arquivo data/system_locked (sobrevive ao tar de deploy) ou env SCHOOL_SYSTEM_LOCKED.
"""
from __future__ import annotations

import hmac
import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, redirect, request, session

gatekeeper_bp = Blueprint("gatekeeper", __name__)

_STATIC_EXT = re.compile(r"\.(png|jpe?g|gif|svg|ico|webp|css|js|map|woff2?|ttf)$", re.I)
_LOCK_FILE = Path(__file__).resolve().parents[1] / "data" / "system_locked"

_MANUTENCAO_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="robots" content="noindex, nofollow"/>
  <title>inove4us School — Em breve</title>
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
    <p class="brand">INOVE4US · SCHOOL</p>
    <h1>Lançamento do Ecossistema inove4us — em breve</h1>
    <p>Estamos finalizando a Torre de Controle. Em breve a escola governa o método; os professores executam no inove4us.</p>
  </section>
</body>
</html>
"""


def _master_key() -> str:
    return (os.environ.get("PRODUCTION_MASTER_KEY") or "").strip()


def _is_production() -> bool:
    env = (os.environ.get("INOVE4US_SCHOOL_ENV") or os.environ.get("FLASK_ENV") or "").lower()
    return env == "production"


def _admin_enabled() -> bool:
    if _is_production():
        return True
    return (os.environ.get("GATEKEEPER_ALLOW_DEV") or "").lower() == "true"


def _valid_secret(provided: str | None) -> bool:
    expected = _master_key()
    got = (provided or "").strip()
    if not expected or not got:
        return False
    return hmac.compare_digest(expected, got)


def is_system_locked() -> bool:
    if _LOCK_FILE.is_file():
        val = _LOCK_FILE.read_text(encoding="utf-8").strip().lower()
        return val in ("1", "true", "yes", "on")
    env = (os.environ.get("SCHOOL_SYSTEM_LOCKED") or "").strip().lower()
    if env:
        return env in ("1", "true", "yes", "on")
    return _is_production()


def _write_lock(locked: bool) -> None:
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    _LOCK_FILE.write_text("true" if locked else "false", encoding="utf-8")


def _is_exempt(path: str) -> bool:
    if path in ("/manutencao", "/api/health", "/favicon.ico"):
        return True
    if path.startswith("/gatekeeper"):
        return True
    if path.startswith("/api/webhooks/"):
        return True
    if path.startswith("/api/tracking/"):
        return True
    if path in ("/api/cms/site",):
        return True
    if path.startswith("/assets/") or path.startswith("/static/"):
        return True
    if _STATIC_EXT.search(path or ""):
        return True
    return False


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
    public = (os.environ.get("FRONTEND_ORIGIN") or "https://school.inove4us.com.br").rstrip("/")
    return redirect(f"{public}/acesso")


@gatekeeper_bp.get("/gatekeeper/unlock")
def unlock():
    if not _admin_enabled():
        return "Rotas de homologação disponíveis apenas em produção.", 403
    if not _master_key() or not _valid_secret(request.args.get("secret")):
        return "Acesso negado.", 403
    _write_lock(False)
    return "Sistema liberado para uso geral!", 200


@gatekeeper_bp.get("/gatekeeper/lock")
def lock():
    if not _admin_enabled():
        return "Rotas de homologação disponíveis apenas em produção.", 403
    if not _master_key() or not _valid_secret(request.args.get("secret")):
        return "Acesso negado.", 403
    _write_lock(True)
    return "Sistema BLOQUEADO. Tela de lançamento ativada para o público.", 200


@gatekeeper_bp.get("/gatekeeper/status")
def status():
    return jsonify({"locked": is_system_locked(), "app": "inove4us-school"})


def register_gatekeeper(app):
    app.register_blueprint(gatekeeper_bp)

    @app.before_request
    def _gatekeeper_guard():
        path = request.path or "/"
        if _is_exempt(path):
            return None
        if not is_system_locked():
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
                        "error": "Lançamento do Ecossistema inove4us — em breve",
                        "maintenance": True,
                    }
                ),
                503,
            )
        return redirect("/manutencao")
