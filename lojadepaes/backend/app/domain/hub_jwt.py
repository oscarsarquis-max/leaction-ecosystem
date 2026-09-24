from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


class HubJwtError(ValueError):
    pass


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


def verify_hub_jwt(token: str, secret: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise HubJwtError("token malformado")
    header_b64, payload_b64, signature_b64 = parts
    signed = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).digest()
    try:
        given = _b64url_decode(signature_b64)
    except Exception as exc:
        raise HubJwtError("assinatura inválida") from exc
    if not hmac.compare_digest(expected, given):
        raise HubJwtError("assinatura inválida")
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception as exc:
        raise HubJwtError("payload inválido") from exc
    if not isinstance(payload, dict):
        raise HubJwtError("payload inválido")
    if payload.get("iss") != "leaction-hub":
        raise HubJwtError("emissor inválido")
    exp = payload.get("exp")
    if exp is not None:
        try:
            if time.time() > float(exp):
                raise HubJwtError("token expirado")
        except (TypeError, ValueError) as exc:
            raise HubJwtError("expiração inválida") from exc
    return payload
