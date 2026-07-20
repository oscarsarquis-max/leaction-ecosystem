"""Billing — proxy S2S para checkout Action Hub (secret nunca vai ao browser)."""

from __future__ import annotations

import os
import sys
from functools import wraps
from urllib.parse import urlencode

import requests
from flask import Blueprint, jsonify, request, session

billing_bp = Blueprint("billing", __name__)

DEFAULT_SKU_FALLBACK = "golive-50"
APP_ID = "inove4us"


def require_session(view):
    """Decorator: exige sessão autenticada com e-mail (subject_id)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = session.get("user")
        if not user or not user.get("id_clie"):
            return jsonify({"error": "Não autenticado"}), 401
        email = str(user.get("mail_clie") or "").strip().lower()
        if not email or "@" not in email:
            return jsonify({"error": "Sessão sem e-mail válido"}), 401
        return view(*args, **kwargs)

    return wrapped


def _hub_secret() -> str:
    return (
        os.environ.get("ACTIONHUB_WEBHOOK_SECRET")
        or os.environ.get("ACTION_HUB_APP_SECRET")
        or ""
    ).strip()


def _hub_api_base() -> str:
    return (
        os.environ.get("ACTION_HUB_API_URL") or "http://localhost:4001"
    ).rstrip("/")


def _frontend_origin() -> str:
    return (
        os.environ.get("FRONTEND_ORIGIN")
        or os.environ.get("CORS_ORIGINS", "").split(",")[0].strip()
        or "http://localhost:5174"
    ).rstrip("/")


def _resolve_sku(raw: str | None) -> str:
    """Body sku → fallback golive-50 → ACTION_HUB_DEFAULT_SKU (SKU real do catálogo)."""
    sku = str(raw or "").strip() or DEFAULT_SKU_FALLBACK
    default_real = (os.environ.get("ACTION_HUB_DEFAULT_SKU") or "").strip()
    if sku == DEFAULT_SKU_FALLBACK and default_real:
        return default_real
    return sku


def _hub_public_base() -> str:
    explicit = (os.environ.get("ACTION_HUB_PUBLIC_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")
    env = (os.environ.get("INOVE4US_ENV") or os.environ.get("FLASK_ENV") or "").lower()
    if env == "production":
        return "https://actionhub.com.br"
    return "http://localhost:4000"


@billing_bp.get("/api/billing/plans-url")
@require_session
def plans_checkout_url():
    """
    URL da vitrine intermediária no Action Hub (/checkout/inove4us),
    no mesmo padrão PanelDX — escolha de plano antes do Brick.
    """
    user = session["user"]
    email = str(user.get("mail_clie") or "").strip().lower()
    frontend = _frontend_origin()
    qs = urlencode(
        {
            "email": email,
            "return_origin": frontend,
            "return_to": "/mesa-do-inovador?paid=1",
        }
    )
    return jsonify(
        {
            "url": f"{_hub_public_base()}/checkout/inove4us?{qs}",
            "app_id": APP_ID,
        }
    )


@billing_bp.post("/api/billing/checkout")
@require_session
def create_checkout():
    user = session["user"]
    subject_id = str(user.get("mail_clie") or "").strip().lower()
    body = request.get_json(silent=True) or {}
    sku = _resolve_sku(body.get("sku"))

    secret = _hub_secret()
    if not secret:
        print(
            "[billing] ACTIONHUB_WEBHOOK_SECRET / ACTION_HUB_APP_SECRET ausente",
            file=sys.stderr,
        )
        return jsonify({"error": "Billing não configurado no servidor"}), 503

    hub_url = f"{_hub_api_base()}/v1/checkout/sessions"
    frontend = _frontend_origin()
    payload = {
        "app_id": os.environ.get("ACTION_HUB_APP_ID", APP_ID).strip() or APP_ID,
        "subject_id": subject_id,
        "sku": sku,
        # Brick white-label no Hub + retorno à home logada do inove4us
        "return_origin": frontend,
        "return_to": "/mesa-do-inovador?paid=1",
        "hub_public_url": os.environ.get("ACTION_HUB_PUBLIC_URL") or "http://localhost:4000",
    }

    try:
        resp = requests.post(
            hub_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {secret}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"[billing] falha S2S Action Hub: {exc}", file=sys.stderr)
        return jsonify({"error": "Falha ao contactar Action Hub"}), 502

    try:
        data = resp.json() if resp.content else {}
    except ValueError:
        data = {}

    if resp.status_code != 200:
        err = data.get("error") or f"Action Hub retornou {resp.status_code}"
        print(f"[billing] Hub status={resp.status_code} error={err}", file=sys.stderr)
        return jsonify({"error": err, "detail": data}), resp.status_code

    checkout_url = data.get("checkout_url")
    if not checkout_url:
        return jsonify({"error": "Hub não retornou checkout_url", "detail": data}), 502

    return (
        jsonify(
            {
                "checkout_url": checkout_url,
                "order_id": data.get("order_id"),
                "amount": data.get("amount"),
                "currency": data.get("currency"),
                "sku": data.get("sku") or sku,
                "plan_name": data.get("plan_name"),
                "checkout_mode": data.get("checkout_mode") or "hub_brick",
            }
        ),
        200,
    )
