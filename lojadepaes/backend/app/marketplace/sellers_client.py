"""Cliente HTTP do módulo marketplace → /v1/sellers do Pay.

Usa as mesmas credenciais de app da Loja (ACTIONHUB_*), sem importar actionhub_client.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import Settings

RETURN_TO = "https://lojadepaes.com.br/parceiro/recebimento"


class SellersPayError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _base(settings: Settings) -> str:
    return str(settings.actionhub_base_url or "").rstrip("/")


def _headers(settings: Settings) -> dict[str, str]:
    secret = str(settings.actionhub_app_secret or "").strip()
    app_id = str(settings.actionhub_app_id or "").strip() or "lojadepaes"
    if not secret:
        raise SellersPayError(503, "Pay não configurado para recebimento")
    return {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-App-Id": app_id,
    }


def _timeout(settings: Settings) -> float:
    return float(settings.actionhub_timeout_seconds or 15)


def get_seller(settings: Settings, seller_ref: str) -> dict[str, Any]:
    url = f"{_base(settings)}/v1/sellers/{seller_ref}"
    try:
        response = httpx.get(
            url,
            headers=_headers(settings),
            params={"app_id": settings.actionhub_app_id or "lojadepaes"},
            timeout=_timeout(settings),
        )
    except httpx.HTTPError as exc:
        raise SellersPayError(502, "Pay indisponível") from exc
    if response.status_code == 404:
        raise SellersPayError(404, "recebimento indisponível no Pay")
    if response.status_code >= 400:
        detail = "falha ao consultar o Pay"
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("error"):
                detail = str(body["error"])
        except Exception:
            pass
        raise SellersPayError(response.status_code, detail)
    data = response.json()
    if not isinstance(data, dict):
        raise SellersPayError(502, "resposta inválida do Pay")
    return data


def connect_link(settings: Settings, seller_ref: str, return_to: str = RETURN_TO) -> str:
    url = f"{_base(settings)}/v1/sellers/connect-link"
    payload = {
        "app_id": settings.actionhub_app_id or "lojadepaes",
        "seller_ref": str(seller_ref),
        "return_to": return_to,
    }
    try:
        response = httpx.post(
            url,
            headers=_headers(settings),
            json=payload,
            timeout=_timeout(settings),
        )
    except httpx.HTTPError as exc:
        raise SellersPayError(502, "Pay indisponível") from exc
    if response.status_code >= 400:
        detail = "não foi possível abrir a conexão com o Mercado Pago"
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("error"):
                detail = str(body["error"])
        except Exception:
            pass
        raise SellersPayError(response.status_code, detail)
    data = response.json()
    link = data.get("url") if isinstance(data, dict) else None
    if not link:
        raise SellersPayError(502, "Pay não devolveu a URL de conexão")
    return str(link)


def disconnect_seller(settings: Settings, seller_ref: str) -> None:
    url = f"{_base(settings)}/v1/sellers/{seller_ref}"
    try:
        response = httpx.request(
            "DELETE",
            url,
            headers=_headers(settings),
            params={"app_id": settings.actionhub_app_id or "lojadepaes"},
            timeout=_timeout(settings),
        )
    except httpx.HTTPError as exc:
        raise SellersPayError(502, "Pay indisponível") from exc
    if response.status_code == 404:
        return
    if response.status_code >= 400:
        detail = "não foi possível desconectar"
        try:
            body = response.json()
            if isinstance(body, dict) and body.get("error"):
                detail = str(body["error"])
        except Exception:
            pass
        raise SellersPayError(response.status_code, detail)
