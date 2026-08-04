"""JWT compartilhado School ↔ B2C (ponte interna S2S).

Secret: SCHOOL_B2C_SHARED_SECRET.
Issuers: inove4us-school (top-down) | inove4us (bottom-up).
"""
from __future__ import annotations

import os
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import jwt
from dotenv import load_dotenv
from flask import g, jsonify, request

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

ISSUER_SCHOOL = "inove4us-school"
ISSUER_B2C = "inove4us"


def shared_secret() -> str:
    secret = (os.environ.get("SCHOOL_B2C_SHARED_SECRET") or "").strip()
    if secret:
        return secret
    env_file = Path(__file__).resolve().parents[1] / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("SCHOOL_B2C_SHARED_SECRET="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def sign_bridge_jwt(
    *,
    issuer: str,
    event_type: str,
    payload: dict[str, Any],
    expires_sec: int = 3600,
) -> str:
    import time

    secret = shared_secret()
    if not secret:
        raise RuntimeError("SCHOOL_B2C_SHARED_SECRET não configurado")
    now = int(time.time())
    return jwt.encode(
        {
            "iss": issuer,
            "event_type": event_type,
            "payload": payload or {},
            "iat": now,
            "exp": now + max(60, int(expires_sec)),
        },
        secret,
        algorithm="HS256",
    )


def extract_bridge_token() -> str:
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    sig = (request.headers.get("X-School-B2C-Signature") or "").strip()
    if sig:
        return sig
    body = request.get_json(silent=True) or {}
    token = body.get("token")
    return str(token).strip() if token else ""


def decode_bridge_jwt(token: str, *, expected_iss: str) -> dict[str, Any]:
    secret = shared_secret()
    if not secret:
        raise RuntimeError("SCHOOL_B2C_SHARED_SECRET não configurado")
    decoded = jwt.decode(token, secret, algorithms=["HS256"])
    iss = str(decoded.get("iss") or "").strip()
    if iss != expected_iss:
        raise jwt.InvalidTokenError(f"iss inválido: {iss or '(vazio)'}")
    return decoded


def require_b2c_bridge_jwt(view: Callable):
    """Valida JWT vindo do B2C (iss=inove4us)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        token = extract_bridge_token()
        if not token:
            return jsonify({"error": "Token ausente"}), 401
        try:
            decoded = decode_bridge_jwt(token, expected_iss=ISSUER_B2C)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 503
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expirado"}), 401
        except jwt.InvalidTokenError as exc:
            return jsonify({"error": "Token inválido", "detail": str(exc)}), 401
        g.bridge_jwt = decoded
        return view(*args, **kwargs)

    return wrapped
