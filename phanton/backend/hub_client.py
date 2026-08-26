"""Cliente S2S do catálogo de identidade no Action Hub.

Login permanece 100% local. Timeout curto — nunca travar criação de usuário.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)

SISTEMA = "phanton"
HUB_TIMEOUT_S = 3.0
PERFIL_CACHE_TTL_S = 8 * 60
_perfil_cache: dict[str, tuple[float, dict[str, Any]]] = {}
ROLE_TO_NIVEL = {
    "admin": "admin",
    "restricted_tester": "usuario_executor",
}


def _hub_base() -> str:
    return (os.getenv("ACTION_HUB_API_URL") or "").strip().rstrip("/")


def _hub_secret() -> str:
    return (os.getenv("PHANTON_HUB_APP_SECRET") or "").strip()


def _auth_headers() -> dict[str, str]:
    secret = _hub_secret()
    return {
        "Authorization": f"Bearer {secret}",
        "X-App-Secret": secret,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def sync_usuario_hub(
    *,
    email: str,
    nome: str,
    nivel: str,
    funcao: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """POST /api/identidade/usuarios. Retorna (ok, erro)."""
    base = _hub_base()
    secret = _hub_secret()
    if not base or not secret:
        msg = "ACTION_HUB_API_URL ou PHANTON_HUB_APP_SECRET ausente"
        logger.warning("hub_sync skip: %s", msg)
        return False, msg

    payload = {
        "sistema": SISTEMA,
        "email": str(email or "").strip().lower(),
        "nome": str(nome or "").strip() or str(email or "").strip(),
        "nivel": str(nivel or "").strip(),
        "funcao": (str(funcao).strip() if funcao else None),
    }
    try:
        with httpx.Client(timeout=HUB_TIMEOUT_S) as client:
            resp = client.post(
                f"{base}/api/identidade/usuarios",
                headers=_auth_headers(),
                json=payload,
            )
        if resp.status_code >= 400:
            detail = _response_error(resp)
            logger.warning(
                "hub_sync falhou HTTP %s: %s", resp.status_code, detail
            )
            return False, detail
        return True, None
    except Exception as exc:
        logger.warning("hub_sync erro: %s", exc)
        return False, str(exc)


def fetch_usuario_perfil(email: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """GET /api/identidade/usuarios/{email}?sistema=phanton."""
    base = _hub_base()
    secret = _hub_secret()
    if not base or not secret:
        msg = "ACTION_HUB_API_URL ou PHANTON_HUB_APP_SECRET ausente"
        return None, msg

    mail = str(email or "").strip().lower()
    if not mail:
        return None, "email ausente"
    path_email = quote(mail, safe="")
    try:
        with httpx.Client(timeout=HUB_TIMEOUT_S) as client:
            resp = client.get(
                f"{base}/api/identidade/usuarios/{path_email}",
                headers=_auth_headers(),
                params={"sistema": SISTEMA},
            )
        if resp.status_code >= 400:
            return None, _response_error(resp)
        data = resp.json()
        if not isinstance(data, dict):
            return None, "resposta inválida do Hub"
        return data, None
    except Exception as exc:
        return None, str(exc)


def resolve_perfil_cached(email: str) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    """Consulta o Hub com cache de 8 min; em falha usa o último valor conhecido."""
    key = str(email or "").strip().lower()
    if not key:
        return None, "email ausente"

    now = time.monotonic()
    hit = _perfil_cache.get(key)
    if hit and (now - hit[0]) < PERFIL_CACHE_TTL_S:
        return hit[1], None

    perfil, err = fetch_usuario_perfil(key)
    if perfil is not None:
        _perfil_cache[key] = (now, perfil)
        return perfil, None
    if hit:
        logger.warning("hub_perfil falhou; usando cache anterior: %s", err)
        return hit[1], None
    return None, err


def clear_perfil_cache() -> None:
    _perfil_cache.clear()


def nivel_from_legacy_role(role: str) -> str:
    return ROLE_TO_NIVEL.get(str(role or "").strip(), "usuario_executor")


def _response_error(resp: httpx.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict):
            err = body.get("error") or body.get("detail")
            if err:
                return str(err)
        return str(body)
    except Exception:
        return (resp.text or f"HTTP {resp.status_code}")[:300]
