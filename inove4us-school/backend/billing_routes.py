"""Billing BFF — proxy S2S Action Hub (catálogo + checkout de licenças School).

Secret do Hub nunca vai ao browser.
"""
from __future__ import annotations

import os
import sys
from functools import wraps
from typing import Any

import requests
from flask import Blueprint, jsonify, request, session

billing_bp = Blueprint("billing", __name__)

APP_ID = "inove4us-school"
SESSION_KEY = "school_gestor"


def require_gestor_session(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = session.get(SESSION_KEY)
        if not user or not user.get("instituicao_id"):
            return jsonify({"error": "Não autenticado"}), 401
        email = str(user.get("email") or "").strip().lower()
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
    return (os.environ.get("ACTION_HUB_API_URL") or "http://127.0.0.1:4001").rstrip("/")


def _hub_public_base() -> str:
    explicit = (os.environ.get("ACTION_HUB_PUBLIC_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")
    return "http://localhost:4000"


def _frontend_origin() -> str:
    return (
        os.environ.get("FRONTEND_ORIGIN")
        or (os.environ.get("CORS_ORIGINS") or "").split(",")[0].strip()
        or "http://localhost:5175"
    ).rstrip("/")


def _licenses_from_plan(plan: dict[str, Any]) -> int | None:
    meta = plan.get("meta_json") if isinstance(plan.get("meta_json"), dict) else {}
    direitos = meta.get("direitos") or meta.get("entitlements") or {}
    if not isinstance(direitos, dict):
        direitos = {}
    raw = (
        plan.get("licenses_granted")
        or meta.get("licenses_granted")
        or meta.get("seats")
        or direitos.get("licenses_granted")
        or direitos.get("seats")
    )
    try:
        n = int(raw)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _serialize_plan(plan: dict[str, Any]) -> dict[str, Any]:
    licenses = _licenses_from_plan(plan)
    return {
        "id": plan.get("id"),
        "sku": plan.get("sku"),
        "sku_id": plan.get("sku"),
        "name": plan.get("name"),
        "type": plan.get("type"),
        "price": plan.get("price"),
        "currency": plan.get("currency") or "BRL",
        "features": plan.get("features") if isinstance(plan.get("features"), list) else [],
        "licenses_granted": licenses,
        "recommended": bool(
            (plan.get("meta_json") or {}).get("recommended")
            if isinstance(plan.get("meta_json"), dict)
            else False
        ),
        "meta_json": plan.get("meta_json") if isinstance(plan.get("meta_json"), dict) else {},
    }


@billing_bp.get("/api/billing/plans")
@require_gestor_session
def list_plans():
    """GET Hub /v1/catalog/inove4us-school → planos B2B ativos."""
    url = f"{_hub_api_base()}/v1/catalog/{APP_ID}"
    headers = {"Accept": "application/json"}
    secret = _hub_secret()
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
        headers["X-App-Secret"] = secret

    try:
        resp = requests.get(url, headers=headers, timeout=15)
    except requests.RequestException as exc:
        print(f"[billing] falha catalog Hub: {exc}", file=sys.stderr, flush=True)
        return jsonify({"error": "Falha ao contactar Action Hub", "plans": []}), 502

    try:
        data = resp.json() if resp.content else {}
    except ValueError:
        data = {}

    if resp.status_code != 200:
        err = data.get("error") or f"Action Hub retornou {resp.status_code}"
        return jsonify({"error": err, "plans": [], "detail": data}), resp.status_code

    plans = [_serialize_plan(p) for p in (data.get("plans") or []) if isinstance(p, dict)]
    return jsonify(
        {
            "app_id": APP_ID,
            "app_name": data.get("app_name") or "Inove4us School",
            "plans": plans,
        }
    )


@billing_bp.post("/api/billing/checkout")
@require_gestor_session
def create_checkout():
    """
    Body: { sku | sku_id }
    subject_id = instituicao_id da sessão (contraparte B2B no Hub).
    """
    user = session[SESSION_KEY]
    instituicao_id = str(user["instituicao_id"]).strip()
    email = str(user.get("email") or "").strip().lower()
    body = request.get_json(silent=True) or {}
    sku = str(body.get("sku") or body.get("sku_id") or "").strip()
    if not sku:
        return jsonify({"error": "sku_id obrigatório"}), 400

    secret = _hub_secret()
    if not secret:
        print(
            "[billing] ACTIONHUB_WEBHOOK_SECRET / ACTION_HUB_APP_SECRET ausente",
            file=sys.stderr,
            flush=True,
        )
        return jsonify({"error": "Billing não configurado no servidor"}), 503

    frontend = _frontend_origin()
    payload = {
        "app_id": APP_ID,
        "subject_id": instituicao_id,
        "subject_type": "instituicao",
        "instituicao_id": instituicao_id,
        "sku": sku,
        "payer_email": email,
        "email": email,
        "return_origin": frontend,
        "return_to": "/equipe?paid=1",
        "hub_public_url": _hub_public_base(),
    }

    hub_url = f"{_hub_api_base()}/v1/checkout/sessions"
    try:
        resp = requests.post(
            hub_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {secret}",
                "X-App-Secret": secret,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"[billing] falha checkout Hub: {exc}", file=sys.stderr, flush=True)
        return jsonify({"error": "Falha ao contactar Action Hub"}), 502

    try:
        data = resp.json() if resp.content else {}
    except ValueError:
        data = {}

    if resp.status_code != 200:
        err = data.get("error") or f"Action Hub retornou {resp.status_code}"
        print(f"[billing] Hub status={resp.status_code} error={err}", file=sys.stderr, flush=True)
        return jsonify({"error": err, "detail": data}), resp.status_code

    checkout_url = data.get("checkout_url")
    if not checkout_url:
        return jsonify({"error": "Hub não retornou checkout_url", "detail": data}), 502

    return (
        jsonify(
            {
                "checkout_url": checkout_url,
                "url": checkout_url,
                "order_id": data.get("order_id"),
                "amount": data.get("amount"),
                "currency": data.get("currency"),
                "sku": data.get("sku") or sku,
                "plan_name": data.get("plan_name"),
                "checkout_mode": data.get("checkout_mode") or "hub_brick",
                "instituicao_id": instituicao_id,
            }
        ),
        200,
    )
