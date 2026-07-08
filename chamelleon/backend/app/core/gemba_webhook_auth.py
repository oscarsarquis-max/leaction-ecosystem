"""Autenticação server-to-server para webhooks Gemba (micro-serviços satélites)."""

from __future__ import annotations

import hashlib
import hmac
import os
from functools import wraps
from typing import Callable, TypeVar

from flask import current_app, jsonify, request

F = TypeVar("F", bound=Callable)


def resolve_gemba_webhook_secret() -> str:
    """Chave compartilhada: GEMBA_WEBHOOK_API_KEY > INTEGRATION_API_KEY > JWT_SECRET_KEY."""
    return (
        os.getenv("GEMBA_WEBHOOK_API_KEY", "").strip()
        or os.getenv("INTEGRATION_API_KEY", "").strip()
        or os.getenv("JWT_SECRET_KEY", "").strip()
    )


def _extract_provided_secret() -> str:
    return (
        request.headers.get("X-Integration-Key", "").strip()
        or request.headers.get("X-Gemba-Webhook-Key", "").strip()
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    )


def _verify_hmac_signature(secret: str) -> bool:
    signature = request.headers.get("X-Gemba-Signature", "").strip()
    if not signature:
        return True
    digest = hmac.new(secret.encode("utf-8"), request.get_data(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def require_gemba_webhook_auth(view: F) -> F:
    """Valida API key e, se presente, assinatura HMAC-SHA256 do corpo."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = current_app.config.get("GEMBA_WEBHOOK_API_KEY") or resolve_gemba_webhook_secret()
        if not expected:
            return jsonify({"error": "Webhook Gemba não configurado no servidor."}), 503

        provided = _extract_provided_secret()
        if not provided or not hmac.compare_digest(provided, expected):
            return jsonify({"error": "Não autorizado."}), 401

        if not _verify_hmac_signature(expected):
            return jsonify({"error": "Assinatura do payload inválida."}), 401

        return view(*args, **kwargs)

    return wrapper  # type: ignore[return-value]
