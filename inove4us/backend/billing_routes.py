"""Billing — proxy S2S para checkout Action Hub (secret nunca vai ao browser)."""

from __future__ import annotations

import os
import sys
from functools import wraps

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


def _branding_back_urls() -> dict:
    """Retorno pós-pagamento na experiência da demandante (white-label)."""
    base = _frontend_origin()
    return {
        "success": f"{base}/pagamento/sucesso",
        "pending": f"{base}/pagamento/pendente",
        "failure": f"{base}/pagamento/erro",
    }


def _statement_descriptor() -> str:
    # Máx. 22 chars no Mercado Pago
    raw = (os.environ.get("MP_STATEMENT_DESCRIPTOR") or "INOVE4US").strip()
    return raw[:22] or "INOVE4US"


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
    payload = {
        "app_id": os.environ.get("ACTION_HUB_APP_ID", APP_ID).strip() or APP_ID,
        "subject_id": subject_id,
        "sku": sku,
        # White-label: retorno na app demandante + extrato com nome curto dela
        "back_urls": body.get("back_urls") or _branding_back_urls(),
        "statement_descriptor": body.get("statement_descriptor")
        or _statement_descriptor(),
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
                "preference_id": data.get("preference_id"),
                "amount": data.get("amount"),
                "currency": data.get("currency"),
                "sku": data.get("sku") or sku,
                "plan_name": data.get("plan_name"),
            }
        ),
        200,
    )
