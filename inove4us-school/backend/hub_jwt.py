"""Validação JWT HS256 do Action Hub (outbox S2S).

Padrão alinhado ao inove4us B2C: token em Authorization Bearer,
X-Hub-Signature ou body.token; iss obrigatório = leaction-hub.
"""
from __future__ import annotations

import os
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import jwt
from dotenv import load_dotenv
from flask import g, jsonify, request

HUB_ISSUER = "leaction-hub"

# Garante .env do School mesmo sob reloader/cwd diferente
_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ENV_FILE)


def _secret_from_dotenv_file() -> str:
    if not _ENV_FILE.is_file():
        return ""
    for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.strip() in ("ACTIONHUB_WEBHOOK_SECRET", "ACTION_HUB_APP_SECRET"):
            secret = val.strip().strip('"').strip("'")
            if secret:
                return secret
    return ""


def webhook_secret() -> str:
    secret = (
        os.environ.get("ACTIONHUB_WEBHOOK_SECRET")
        or os.environ.get("ACTION_HUB_APP_SECRET")
        or ""
    ).strip()
    if secret:
        return secret
    # Fallback: lê o arquivo (dotenv não sobrescreve var de ambiente vazia)
    secret = _secret_from_dotenv_file()
    if secret:
        return secret
    try:
        from flask import current_app

        return (current_app.config.get("ACTIONHUB_WEBHOOK_SECRET") or "").strip()
    except RuntimeError:
        return ""


def extract_hub_token() -> str:
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    sig = (request.headers.get("X-Hub-Signature") or "").strip()
    if sig:
        return sig
    body = request.get_json(silent=True) or {}
    token = body.get("token")
    return str(token).strip() if token else ""


def decode_hub_jwt(token: str) -> dict[str, Any]:
    secret = webhook_secret()
    if not secret:
        raise RuntimeError("ACTIONHUB_WEBHOOK_SECRET não configurado")
    decoded = jwt.decode(token, secret, algorithms=["HS256"])
    iss = str(decoded.get("iss") or "").strip()
    if iss != HUB_ISSUER:
        raise jwt.InvalidTokenError(f"iss inválido: {iss or '(vazio)'}")
    return decoded


def require_hub_jwt(view: Callable):
    """Decorator: exige JWT Hub válido; 401 se falhar; anexa em g.hub_jwt."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        token = extract_hub_token()
        if not token:
            return jsonify({"error": "Token ausente"}), 401
        try:
            decoded = decode_hub_jwt(token)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError as exc:
            return jsonify({"error": "Token inválido", "detail": str(exc)}), 401
        g.hub_jwt = decoded
        g.hub_token = token
        return view(*args, **kwargs)

    return wrapped
