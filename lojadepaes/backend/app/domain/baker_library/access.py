"""Consulta de plano e autorização no ActionHub. Sem ledger local de assinatura."""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.actionhub_client import HubUnavailableError
from app.domain.baker_library.hub_plans import invoke as hub_plans_invoke
from app.domain.errors import ConfirmationError
from app.models.baker_library import HubAuthorizationCache
from app.models.customers import CustomerAccount

logger = logging.getLogger("lojadepaes.biblioteca")

AUTHORIZED_INITIAL_BRL = 19.0
AUTHORIZED_COMPLEMENTARY_BRL = 10.0
PERIOD_LABEL = "mensal"
PLAN_HINT_SKU = "LOJADEPAES_BIBLIOTECA_MENSAL"
COMPLEMENTARY_HINT_SKU = "LOJADEPAES_BIBLIOTECA_CREDITOS"
PRINCIPAL_CREDITS = 20
COMPLEMENTARY_CREDITS = 10
CREDIT_COST = 1
CACHE_POLICY = (
    "O cache guarda só a última autorização confirmada pelo Hub, pelo prazo "
    "configurado. Não cria acesso novo, não vale como saldo e não interpreta "
    "falha técnica como cancelamento ou esgotamento."
)
CYCLE_RULES = {
    "source": "actionhub",
    "calendar_month": False,
    "accumulate": False,
    "pack_accumulate": True,
    "pack_expires": False,
    "pack_requires_principal": False,
    "consume_monthly_first": True,
    "credit_cost": CREDIT_COST,
    "principal_credits": PRINCIPAL_CREDITS,
    "pack_credits": COMPLEMENTARY_CREDITS,
    "pack_optional": True,
    "auto_buy": False,
    "notes": [
        "Assinatura principal: R$ 19,00 por mês, com renovação automática autorizada no cartão.",
        "A franquia de 20 consultas de IA é mensal e não acumula. Entram só após o pagamento confirmado do ciclo.",
        "Pacote adicional: R$ 10,00 por compra avulsa, 10 consultas de IA. Não é assinatura e não renova sozinho.",
        "O pacote avulso é cumulativo, não expira e não exige assinatura vigente para contratar ou usar.",
        "O pacote avulso não concede desconto de assinante, crédito de pão nem carimbo de fidelidade.",
        "Não compramos o pacote automaticamente quando o saldo termina.",
        "O consumo usa primeiro a franquia mensal vigente e devolve à mesma origem. Uma consulta consome um único crédito.",
        "Cancelar a renovação em Gerenciar assinatura, na Loja de Pães, interrompe as próximas cobranças. O período já pago continua até o vencimento. O saldo avulso permanece.",
    ],
}


def subject_hmac(settings: Settings, email: str) -> str:
    secret = (settings.customer_identity_secret or settings.admin_session_secret or "biblioteca").encode()
    return hmac.new(secret, f"biblioteca:{email.strip().lower()}".encode(), hashlib.sha256).hexdigest()


def public_plan(settings: Settings) -> dict[str, Any]:
    base = {
        "period": PERIOD_LABEL,
        "authorized_initial_brl": AUTHORIZED_INITIAL_BRL,
        "authorized_complementary_brl": AUTHORIZED_COMPLEMENTARY_BRL,
        "authorized_pack_brl": AUTHORIZED_COMPLEMENTARY_BRL,
        "credit_cost": CREDIT_COST,
        "accumulate": False,
        "benefits": _benefits(),
        "cache_policy": CACHE_POLICY,
        "cycle_rules": CYCLE_RULES,
        "suggested_sku": PLAN_HINT_SKU,
        "suggested_complementary_sku": COMPLEMENTARY_HINT_SKU,
        "suggested_pack_sku": COMPLEMENTARY_HINT_SKU,
        "plans_href": _plans_href(settings),
    }
    try:
        catalog = _fetch_catalog(settings)
    except HubUnavailableError:
        return {
            **base,
            "configured": False,
            "checkout_ready": False,
            "source": "unavailable",
            "principal": _expected_principal(),
            "complementary": _expected_pack(),
            "pack": _expected_pack(),
            "message": (
                "Não foi possível consultar os planos agora. "
                "Artigos e calculadora continuam abertos."
            ),
        }
    plans = catalog.get("plans") or []
    principal = _pick_library_plan(plans)
    complementary = _pick_complementary_plan(plans, principal)
    if principal is None:
        return {
            **base,
            "configured": False,
            "checkout_ready": False,
            "source": "hub",
            "principal": _expected_principal(),
            "complementary": complementary and _public_offer(complementary, COMPLEMENTARY_CREDITS) or _expected_pack(),
            "pack": complementary and _public_offer(complementary, COMPLEMENTARY_CREDITS) or _expected_pack(),
            "message": (
                "Os planos da Biblioteca ainda não estão publicados. "
                "A leitura e a calculadora já estão abertas. Contratação fica na página de planos da Loja."
            ),
        }
    offer = _public_offer(principal, PRINCIPAL_CREDITS)
    extra = _public_offer(complementary, COMPLEMENTARY_CREDITS) if complementary else _expected_pack()
    return {
        **base,
        "configured": True,
        "checkout_ready": bool(offer.get("checkout_ready")),
        "source": "hub",
        "id": offer.get("id"),
        "sku": offer.get("sku"),
        "name": offer.get("name"),
        "price": offer.get("price"),
        "currency": offer.get("currency"),
        "features": offer.get("features") or _benefits(),
        "credits": offer.get("credits"),
        "principal": offer,
        "complementary": extra,
        "pack": extra,
        "message": None,
    }


def access_for_account(session: Session, settings: Settings, account: CustomerAccount | None) -> dict[str, Any]:
    plan = public_plan(settings)
    if account is None:
        return {
            "identified": False,
            "authorized": False,
            "reason": "anonymous",
            "subscription_status": "unidentified",
            "message": "Identifique-se com o cadastro verificado da Loja para consultar a assinatura e as consultas de IA.",
            "credits": None,
            "ai_credits": None,
            "monthly_credits": None,
            "pack_credits": None,
            "pack_expires": False,
            "can_use_ai": False,
            "subscriber_discount": False,
            "balance_source": None,
            "exhausted": False,
            "plan": plan,
            "plans_href": plan.get("plans_href"),
            "cache": None,
        }
    digest = subject_hmac(settings, account.email)
    try:
        remote = _fetch_entitlement(settings, account.email)
        _remember(session, settings, digest, remote, source="hub")
        authorized = _entitlement_allows(remote)
        credits = _credits_from_remote(remote)
        monthly_credits = _monthly_credits_from_remote(remote)
        pack_credits = _pack_credits_from_remote(remote)
        complementary_active = _complementary_active(remote)
        subscriptions = _list_subscriptions(settings, account.email)
        status = _subscription_status(authorized, remote, subscriptions)
        return {
            "identified": True,
            "authorized": authorized,
            "subscription_status": status,
            "reason": None if authorized else str(remote.get("reason") or "no_entitlement"),
            "message": _access_message(
                authorized,
                remote,
                credits=credits,
                complementary_active=complementary_active,
                status=status,
            ),
            "valid_until": remote.get("valid_until") if authorized else None,
            "credits": credits,
            "ai_credits": credits,
            "monthly_credits": monthly_credits,
            "pack_credits": pack_credits,
            "pack_expires": False,
            "can_use_ai": credits > 0,
            "subscriber_discount": authorized,
            "balance_source": "hub",
            "credit_cost": CREDIT_COST,
            "complementary_active": complementary_active,
            "complementary_eligible": True,
            "exhausted": credits <= 0,
            "plan": plan,
            "plans_href": plan.get("plans_href"),
            "subscriptions": subscriptions,
            "cancel_policy": (
                "Cancele a renovação em Gerenciar assinatura, na Loja de Pães. "
                "O período já pago continua até o vencimento. Sem pró-rata. "
                "Cancelar a assinatura não apaga créditos de pão."
            ),
            "cache": {"used": False, "policy": CACHE_POLICY},
        }
    except HubUnavailableError:
        cached = _load_cache(session, digest)
        if cached is not None and cached.active and _cache_fresh(settings, cached):
            return {
                "identified": True,
                "authorized": True,
                "reason": "cache",
                "message": (
                    "Não foi possível consultar o saldo agora. A última autorização confirmada "
                    "ainda vale para reconhecer a assinatura. Isso não é saldo esgotado nem cancelamento."
                ),
                "valid_until": cached.valid_until.isoformat() if cached.valid_until else None,
                "credits": None,
                "ai_credits": None,
                "monthly_credits": None,
                "pack_credits": None,
                "pack_expires": False,
                "can_use_ai": False,
                "subscriber_discount": True,
                "subscription_status": "active",
                "balance_source": "unavailable",
                "credit_cost": CREDIT_COST,
                "complementary_active": False,
                "complementary_eligible": False,
                "exhausted": False,
                "plan": plan,
                "plans_href": plan.get("plans_href"),
                "cache": {"used": True, "policy": CACHE_POLICY, "checked_at": cached.checked_at.isoformat()},
            }
        return {
            "identified": True,
            "authorized": False,
            "reason": "hub_unavailable",
            "message": (
                "Não foi possível confirmar a assinatura no ActionHub. "
                "Isso não cancela um plano existente nem esgota créditos. "
                "Artigos, calculadora e pedidos continuam abertos."
            ),
            "credits": None,
            "ai_credits": None,
            "monthly_credits": None,
            "pack_credits": None,
            "pack_expires": False,
            "can_use_ai": False,
            "subscriber_discount": False,
            "subscription_status": "none",
            "balance_source": "unavailable",
            "exhausted": False,
            "plan": plan,
            "plans_href": plan.get("plans_href"),
            "cache": {"used": False, "policy": CACHE_POLICY},
        }


def can_use_ai(access: dict[str, Any] | None) -> bool:
    if not isinstance(access, dict):
        return False
    if access.get("balance_source") == "unavailable":
        return False
    if access.get("exhausted"):
        return False
    if access.get("can_use_ai") is True:
        return True
    try:
        credits = int(access.get("ai_credits") if access.get("ai_credits") is not None else access.get("credits") or 0)
    except (TypeError, ValueError):
        credits = 0
    return credits > 0


def start_subscription_checkout(
    session: Session,
    settings: Settings,
    account: CustomerAccount,
    *,
    return_to: str,
    sku: str = "",
) -> dict[str, Any]:
    plan = public_plan(settings)
    wanted = str(sku or "").strip() or str((plan.get("principal") or {}).get("sku") or plan.get("sku") or "")
    pack = plan.get("pack") if isinstance(plan.get("pack"), dict) else plan.get("complementary")
    pack = pack if isinstance(pack, dict) else {}
    is_pack = wanted and wanted == str(pack.get("sku") or COMPLEMENTARY_HINT_SKU)
    if is_pack:
        if not pack.get("checkout_ready"):
            raise ConfirmationError("o pacote avulso só abre quando estiver ativo no ActionHub")
    elif not plan.get("configured") or not plan.get("checkout_ready"):
        raise ConfirmationError(
            "o checkout da assinatura só abre quando o plano mensal de R$ 19,00 estiver ativo no ActionHub"
        )
    sku = wanted
    path = return_to if return_to.startswith("/biblioteca") else "/#biblioteca"
    payload = hub_plans_invoke(
        settings,
        "START_HUB_CATALOG_CHECKOUT",
        {
            "subject_id": account.email,
            "sku": sku,
            "return_origin": settings.public_origin,
            "return_to": path,
        },
        correlation_id=f"loja-checkout-{account.id}",
        idempotency_key=f"checkout:{settings.actionhub_app_id}:{account.email}:{sku}",
    )
    if payload.get("error"):
        raise ConfirmationError(str(payload.get("error")))
    checkout_url = str(payload.get("checkout_url") or "")
    if not checkout_url:
        raise ConfirmationError("o ActionHub não devolveu o endereço de pagamento")
    mode = str(payload.get("checkout_mode") or "")
    if is_pack:
        if mode == "subscription":
            raise ConfirmationError("o pacote adicional é compra avulsa, não assinatura mensal")
    elif mode != "subscription":
        raise ConfirmationError(
            "o checkout da assinatura só abre como assinatura mensal com renovação automática"
        )
    return {
        "checkout_url": checkout_url,
        "order_id": payload.get("order_id"),
        "sku": payload.get("sku") or sku,
        "amount": payload.get("amount") or plan.get("price"),
        "currency": payload.get("currency") or "BRL",
        "checkout_mode": mode or ("hub_brick" if is_pack else "subscription"),
    }


def cancel_subscription(settings: Settings, account: CustomerAccount, sku: str = "") -> dict[str, Any]:
    payload = hub_plans_invoke(
        settings,
        "CANCEL_HUB_SUBSCRIPTION",
        {"subject_id": account.email, "sku": sku or PLAN_HINT_SKU},
        correlation_id=f"loja-cancel-{account.id}",
        idempotency_key=f"cancel:{settings.actionhub_app_id}:{account.email}:{sku or PLAN_HINT_SKU}",
    )
    if payload.get("error"):
        raise ConfirmationError(str(payload.get("error")))
    return {
        "ok": True,
        "status": payload.get("status") or "cancelled",
        "sku": payload.get("sku") or sku or PLAN_HINT_SKU,
        "message": payload.get("message")
        or "A renovação automática foi cancelada. O período já pago continua até o vencimento.",
    }


def _benefits() -> list[str]:
    return [
        "Aprofundamento personalizado com o Gigio: 1 consulta de IA por crédito usado neste modo.",
        "Assinatura: R$ 19,00 por mês, 20 consultas de IA no ciclo pago e 10% de desconto nos produtos da Loja.",
        "Pacote adicional: R$ 10,00 avulso, 10 consultas de IA cumulativas, sem vencimento e sem exigir assinatura vigente.",
        "Artigos, calculadora, pedido e fidelidade do pão continuam separados da assinatura.",
    ]


def _expected_principal() -> dict[str, Any]:
    return {
        "sku": PLAN_HINT_SKU,
        "name": "Principal da Biblioteca",
        "price": AUTHORIZED_INITIAL_BRL,
        "currency": "BRL",
        "period": PERIOD_LABEL,
        "credits": PRINCIPAL_CREDITS,
        "checkout_ready": False,
        "role": "principal",
    }


def _expected_pack() -> dict[str, Any]:
    return {
        "sku": COMPLEMENTARY_HINT_SKU,
        "name": "Pacote adicional de consultas de IA",
        "price": AUTHORIZED_COMPLEMENTARY_BRL,
        "currency": "BRL",
        "period": "avulso",
        "credits": COMPLEMENTARY_CREDITS,
        "checkout_ready": False,
        "optional": True,
        "role": "pack",
    }


def _expected_complementary() -> dict[str, Any]:
    return _expected_pack()


def _public_offer(plan: dict, fallback_credits: int) -> dict[str, Any]:
    price = float(plan.get("price") or 0)
    credits = plan.get("credits")
    if not credits:
        meta = plan.get("meta_json") if isinstance(plan.get("meta_json"), dict) else {}
        direitos = meta.get("direitos") or meta.get("entitlements") or {}
        credits = meta.get("creditos") or meta.get("credits") or direitos.get("creditos") or direitos.get("credits")
    try:
        credits_n = int(credits) if credits else fallback_credits
    except (TypeError, ValueError):
        credits_n = fallback_credits
    return {
        "id": plan.get("id"),
        "sku": plan.get("sku"),
        "name": plan.get("name"),
        "price": price,
        "currency": plan.get("currency") or "BRL",
        "period": _period_label(plan),
        "credits": credits_n,
        "features": list(plan.get("features") or []),
        "checkout_ready": price > 0
        and (
            (_is_pack_row(plan) and not _offer_is_recurring(plan))
            or (not _is_pack_row(plan) and _offer_is_recurring(plan))
        ),
        "role": "pack" if _is_pack_row(plan) else "principal",
        "optional": _is_pack_row(plan),
    }


def _offer_is_recurring(plan: dict) -> bool:
    meta = plan.get("meta_json") if isinstance(plan.get("meta_json"), dict) else {}
    mode = str(meta.get("checkout_mode") or plan.get("checkout_mode") or "").casefold()
    if mode == "subscription" or meta.get("recurring") or plan.get("recurring"):
        return True
    return False


def _period_label(plan: dict) -> str:
    if _is_pack_row(plan):
        return "avulso"
    meta = plan.get("meta_json") if isinstance(plan.get("meta_json"), dict) else {}
    raw = str(meta.get("periodicidade") or "").strip().casefold()
    if raw in {"mensal", "monthly", "mês", "mes"}:
        return PERIOD_LABEL
    months = meta.get("period_months") or meta.get("meses")
    if months in {1, "1"}:
        return PERIOD_LABEL
    if plan.get("type") == "plan":
        return PERIOD_LABEL
    return PERIOD_LABEL


def _pick_library_plan(plans: list[dict]) -> dict | None:
    active = [row for row in plans if isinstance(row, dict) and not _is_complementary_row(row)]
    if not active:
        return None
    hinted = [row for row in active if str(row.get("sku") or "") == PLAN_HINT_SKU]
    if hinted:
        return hinted[0]
    for row in active:
        meta = row.get("meta_json") if isinstance(row.get("meta_json"), dict) else {}
        direitos = meta.get("direitos") or meta.get("entitlements") or {}
        if isinstance(direitos, dict) and (direitos.get("biblioteca") or direitos.get("assinatura")):
            return row
        sku = str(row.get("sku") or "").casefold()
        name = str(row.get("name") or "").casefold()
        if "biblioteca" in sku or "biblioteca" in name:
            return row
    monthly = [
        row
        for row in active
        if str(row.get("type") or "") == "plan" and not _is_complementary_row(row)
    ]
    if len(monthly) == 1:
        return monthly[0]
    return None


def _pick_complementary_plan(plans: list[dict], principal: dict | None) -> dict | None:
    principal_sku = str((principal or {}).get("sku") or "")
    for row in plans:
        if not isinstance(row, dict):
            continue
        if principal_sku and str(row.get("sku") or "") == principal_sku:
            continue
        if _is_pack_row(row):
            return row
    return None


def _is_pack_row(row: dict) -> bool:
    return _is_complementary_row(row)


def _is_complementary_row(row: dict) -> bool:
    sku = str(row.get("sku") or "").casefold()
    name = str(row.get("name") or "").casefold()
    if sku == COMPLEMENTARY_HINT_SKU.casefold():
        return True
    meta = row.get("meta_json") if isinstance(row.get("meta_json"), dict) else {}
    direitos = meta.get("direitos") or meta.get("entitlements") or {}
    papel = str(direitos.get("papel") or meta.get("papel") or "").casefold()
    if papel in {"complementar", "complementary"}:
        return True
    if "complementar" in sku or "complementar" in name:
        return True
    if "biblioteca_creditos" in sku or "biblioteca-creditos" in sku:
        return True
    return str(row.get("type") or "") == "credit_pack" and "biblioteca" in f"{sku} {name}"


def _credits_from_remote(remote: dict) -> int:
    payload = remote.get("entitlement") if isinstance(remote.get("entitlement"), dict) else {}
    try:
        return max(0, int(payload.get("credits") or 0))
    except (TypeError, ValueError):
        return 0


def _pack_credits_from_remote(remote: dict) -> int:
    payload = remote.get("entitlement") if isinstance(remote.get("entitlement"), dict) else {}
    try:
        return max(0, int(payload.get("pack_credits") or 0))
    except (TypeError, ValueError):
        return 0


def _monthly_credits_from_remote(remote: dict) -> int:
    payload = remote.get("entitlement") if isinstance(remote.get("entitlement"), dict) else {}
    try:
        return max(0, int(payload.get("principal_credits") or 0))
    except (TypeError, ValueError):
        return 0


def _subscription_status(authorized: bool, remote: dict, subscriptions: list) -> str:
    statuses = [
        str(item.get("status") or "").casefold()
        for item in subscriptions
        if isinstance(item, dict)
    ]
    open_sub = any(status in {"authorized", "pending", "paused"} for status in statuses)
    cancelled = any(status in {"cancelled", "canceled"} for status in statuses)
    if authorized and cancelled and not open_sub:
        return "cancelled_with_access"
    if authorized:
        return "active"
    if open_sub:
        return "pending"
    if str(remote.get("reason") or "") == "expired":
        return "none"
    return "none"


def _plans_href(settings: Settings, return_to: str = "/#biblioteca") -> str:
    origin = _hub_site_origin(settings)
    loja = settings.public_origin.rstrip("/")
    path = return_to if str(return_to).startswith("/") else "/#biblioteca"
    from urllib.parse import urlencode

    query = urlencode({"return_origin": loja, "return_to": path})
    return f"{origin}/loja?{query}"


def _hub_site_origin(settings: Settings) -> str:
    raw = str(getattr(settings, "actionhub_site_url", "") or "").strip()
    if raw:
        return raw.rstrip("/")
    base = settings.actionhub_base_url.rstrip("/")
    if ":4001" in base:
        return "http://127.0.0.1:4000"
    if base.endswith("/hub-api"):
        return base[: -len("/hub-api")]
    return "https://actionhub.com.br"


def _complementary_active(remote: dict) -> bool:
    payload = remote.get("entitlement") if isinstance(remote.get("entitlement"), dict) else {}
    extra = payload.get("complementary")
    if not isinstance(extra, dict) or not extra.get("sku"):
        return False
    until = extra.get("cycle_ends_at") or extra.get("valid_until")
    if not until:
        return True
    parsed = _parse_dt(until)
    if parsed is None:
        return True
    return parsed > datetime.now(UTC)


def _entitlement_allows(remote: dict) -> bool:
    if not remote.get("active"):
        return False
    payload = remote.get("entitlement") if isinstance(remote.get("entitlement"), dict) else {}
    direitos = payload.get("direitos") or payload.get("entitlements") or payload
    if isinstance(direitos, dict):
        if direitos.get("biblioteca") is False:
            return False
        if direitos.get("assinatura") is False and direitos.get("biblioteca") is None:
            return False
    return True


def _access_message(
    authorized: bool,
    remote: dict,
    *,
    credits: int | None = None,
    complementary_active: bool = False,
    status: str = "none",
) -> str:
    del complementary_active
    saldo = (
        f" Consultas de IA: {credits}."
        if credits is not None
        else ""
    )
    if authorized and status == "cancelled_with_access":
        return (
            "Renovação cancelada. O acesso da assinatura continua até o fim do período já pago."
            f"{saldo} Artigos e calculadora continuam livres."
        )
    if authorized:
        return (
            "Assinatura confirmada."
            f"{saldo} "
            "Cada consulta de aprofundamento usa 1 consulta de IA. Artigos e contas continuam livres."
        )
    if status == "pending":
        return (
            "A assinatura ainda está pendente. O código de acesso não prova pagamento. "
            "Artigos e calculadora continuam livres."
        )
    reason = str(remote.get("reason") or "")
    if reason == "expired":
        return "O ciclo contratado terminou. A leitura e a calculadora continuam abertas."
    if reason == "pack_only" or (not authorized and (credits or 0) > 0):
        return (
            f"Sem assinatura vigente.{saldo} "
            "Pacote avulso não concede desconto de assinante. Artigos e calculadora continuam livres."
        )
    return "Este aprofundamento usa consultas de IA da Biblioteca. Artigos e contas continuam livres."


def _fetch_catalog(settings: Settings) -> dict[str, Any]:
    payload = hub_plans_invoke(
        settings,
        "LIST_HUB_CATALOG",
        {},
        correlation_id=f"loja-catalog-{settings.actionhub_app_id}",
        idempotency_key=f"catalog:{settings.actionhub_app_id}",
    )
    return payload if isinstance(payload, dict) else {"plans": []}


def _list_subscriptions(settings: Settings, email: str) -> list[dict[str, Any]]:
    payload = hub_plans_invoke(
        settings,
        "LIST_HUB_SUBSCRIPTIONS",
        {"subject_id": email},
        correlation_id=f"loja-subs-{email[:24]}",
        idempotency_key=f"subs:{settings.actionhub_app_id}:{email}",
    )
    items = payload.get("subscriptions") if isinstance(payload, dict) else []
    return items if isinstance(items, list) else []


def _fetch_entitlement(settings: Settings, email: str) -> dict[str, Any]:
    payload = hub_plans_invoke(
        settings,
        "GET_HUB_ENTITLEMENTS",
        {"subject_id": email},
        correlation_id=f"loja-ent-{email[:24]}",
        idempotency_key=f"ent:{settings.actionhub_app_id}:{email}",
    )
    return payload if isinstance(payload, dict) else {"active": False, "reason": "no_entitlement"}


def _remember(session: Session, settings: Settings, digest: str, remote: dict, *, source: str) -> None:
    del settings
    row = session.scalar(select(HubAuthorizationCache).where(HubAuthorizationCache.subject_hmac == digest))
    now = datetime.now(UTC)
    valid_until = _parse_dt(remote.get("valid_until"))
    if row is None:
        row = HubAuthorizationCache(subject_hmac=digest)
        session.add(row)
    row.app_id = str(remote.get("app_id") or "lojadepaes")
    row.active = bool(remote.get("active") and _entitlement_allows(remote))
    row.plan_sku = _plan_sku_from_remote(remote)
    row.valid_until = valid_until
    row.checked_at = now
    row.source = source
    session.flush()


def _load_cache(session: Session, digest: str) -> HubAuthorizationCache | None:
    return session.scalar(select(HubAuthorizationCache).where(HubAuthorizationCache.subject_hmac == digest))


def _cache_fresh(settings: Settings, row: HubAuthorizationCache) -> bool:
    ttl = max(30, int(settings.actionhub_entitlement_cache_seconds))
    if row.checked_at is None:
        return False
    checked = row.checked_at if row.checked_at.tzinfo else row.checked_at.replace(tzinfo=UTC)
    if datetime.now(UTC) - checked > timedelta(seconds=ttl):
        return False
    if row.valid_until is not None:
        until = row.valid_until if row.valid_until.tzinfo else row.valid_until.replace(tzinfo=UTC)
        if until <= datetime.now(UTC):
            return False
    return True


def _plan_sku_from_remote(remote: dict) -> str | None:
    payload = remote.get("entitlement") if isinstance(remote.get("entitlement"), dict) else {}
    for key in ("sku", "plan", "plano"):
        value = payload.get(key)
        if value:
            return str(value)[:80]
    return None


def _parse_dt(value: object) -> datetime | None:
    if not value:
        return None
    raw = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed
