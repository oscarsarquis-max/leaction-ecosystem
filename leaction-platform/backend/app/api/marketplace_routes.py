"""Rotas do plugin Marketplace — exposição federada multivendor."""

from __future__ import annotations

import logging

from flask import Blueprint, current_app, has_app_context, jsonify, request

from app.services.amazon_service import AmazonService
from app.services.marketplace_resilience import (
    LIVE_BUDGET_S,
    annotate_cache_meta,
    ml_circuit,
    offers_cache,
    run_with_live_budget,
    vitrine_cache,
)
from app.services.mercadolivre_auth import is_ml_api_configured
from app.services.ml_oauth_service import (
    has_persisted_or_env_tokens,
    is_oauth_app_configured,
    oauth_setup_info,
)
from app.services.mercadolivre_service import DEFAULT_LIMIT, MAX_LIMIT
from app.services.multivendor_orchestrator import MultivendorOrchestrator

logger = logging.getLogger(__name__)

marketplace_bp = Blueprint("marketplace", __name__)


def _bind_app_context(producer):
    """Garante app context Flask em threads SWR / budget (curadoria DB)."""
    if not has_app_context():
        return producer
    app = current_app._get_current_object()

    def _wrapped():
        with app.app_context():
            return producer()

    return _wrapped


def _offers_cache_key(query: str | None, category: str | None, limit: int) -> str:
    return f"offers:{(query or '').strip().lower()}|{(category or '').strip().lower()}|{limit}"


def _vitrine_cache_key(
    id_matu: int | None,
    id_clie: int | None,
    id_projeto: int | None,
    limit: int,
) -> str:
    return f"vitrine:{id_matu or 0}:{id_clie or 0}:{id_projeto or 0}:{limit}"


@marketplace_bp.get("/offers")
def list_marketplace_offers():
    """
    GET /api/marketplace/offers
    Query params: q (termo), category (formacao|equipamentos|software), limit (1–24).

    Resiliência: cache SWR + budget de live + circuit breaker.
    """
    query = (request.args.get("q") or "").strip() or None
    category = (request.args.get("category") or "").strip() or None
    limit_raw = request.args.get("limit", type=int)
    limit = limit_raw if limit_raw is not None else DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = _offers_cache_key(query, category, limit)

    cached, state = offers_cache.get(cache_key)
    if state == "fresh" and isinstance(cached, dict):
        return jsonify(annotate_cache_meta(cached, cache_state="fresh")), 200

    if state == "stale" and isinstance(cached, dict):
        offers_cache.schedule_refresh(
            cache_key,
            _bind_app_context(
                lambda: MultivendorOrchestrator().search_all_vendors(
                    query, category=category, limit=limit
                )
            ),
            on_success=lambda _: ml_circuit.record_success(),
            on_failure=lambda _: ml_circuit.record_failure(),
        )
        return jsonify(annotate_cache_meta(cached, cache_state="stale")), 200

    orchestrator = MultivendorOrchestrator()

    def _live() -> dict:
        return orchestrator.search_all_vendors(query, category=category, limit=limit)

    try:
        if not ml_circuit.allow():
            # Circuito aberto sem cache: ainda tenta orquestrador (ele cai em fallback estático)
            result = _live()
            result = annotate_cache_meta(result, cache_state="miss")
            result["reliability"]["circuit_forced_fallback"] = True
            return jsonify(result), 200

        result = run_with_live_budget(_bind_app_context(_live), budget_s=LIVE_BUDGET_S)
        offers_cache.set(cache_key, result)
        ml_circuit.record_success()
        return jsonify(annotate_cache_meta(result, cache_state="miss")), 200
    except TimeoutError:
        logger.warning("offers live budget esgotado — fallback estático")
        ml_circuit.record_failure()
        result = _live_fallback_offers(orchestrator, query, category, limit)
        offers_cache.set(cache_key, result, ttl_s=60, stale_s=300)
        offers_cache.schedule_refresh(
            cache_key,
            _bind_app_context(
                lambda: MultivendorOrchestrator().search_all_vendors(
                    query, category=category, limit=limit
                )
            ),
        )
        return jsonify(annotate_cache_meta(result, cache_state="miss")), 200
    except Exception:
        logger.exception("Falha inesperada no marketplace federado")
        ml_circuit.record_failure()
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Erro interno ao agregar ofertas multivendor",
                    "offers": [],
                    "count": 0,
                    "reliability": {"cache": "miss", "circuit": ml_circuit.snapshot()},
                }
            ),
            500,
        )


def _live_fallback_offers(
    orchestrator: MultivendorOrchestrator,
    query: str | None,
    category: str | None,
    limit: int,
) -> dict:
    """Força caminho com ML circuit/fallback — reusa orquestrador (já faz fallback se ML vazio)."""
    # Abre circuito temporário via allow=False não; em vez disso busca com service que
    # retorna vazio rápido se circuit aberto. Aqui garantimos payload com fallback.
    from app.services.multivendor_orchestrator import (
        _fallback_offers_for_category,
        resolve_category_key,
        CATEGORY_PROFILES,
    )

    cat_key = resolve_category_key(category)
    profile = CATEGORY_PROFILES.get(cat_key, CATEGORY_PROFILES["geral"])
    offers = _fallback_offers_for_category(
        cat_key, query or profile["default_query"], limit
    )
    return {
        "status": "ok",
        "source": "fallback",
        "sources": ["mercadolivre"] if offers else [],
        "live": False,
        "category": cat_key,
        "category_label": profile["label"],
        "query": query or profile["default_query"],
        "count": len(offers),
        "offers": offers,
        "notice": (
            "Timeout na busca live — exibindo vitrine curada LeAction "
            "(revalidação automática em seguida)."
        ),
        "vendors": {
            "mercadolivre": {"count": len(offers), "active": bool(offers), "fallback": True},
            "amazon": {
                "count": 0,
                "configured": AmazonService.is_configured(),
                "active": False,
            },
        },
    }


@marketplace_bp.get("/vitrine")
def marketplace_vitrine_contextual():
    """
    GET /api/marketplace/vitrine
    Query: id_matu | id_clie | id_projeto (opcionais) → modo contextual vs genérico.
    """
    from app.services.contextual_vitrine import build_contextual_vitrine

    def _positive_int(raw) -> int | None:
        try:
            value = int(str(raw).strip())
        except (TypeError, ValueError, AttributeError):
            return None
        return value if value > 0 else None

    id_matu = _positive_int(request.args.get("id_matu"))
    id_clie = _positive_int(request.args.get("id_clie"))
    id_projeto = _positive_int(request.args.get("id_projeto"))
    limit = request.args.get("limit", type=int) or DEFAULT_LIMIT
    limit = max(1, min(limit, MAX_LIMIT))
    cache_key = _vitrine_cache_key(id_matu, id_clie, id_projeto, limit)

    cached, state = vitrine_cache.get(cache_key)
    if state == "fresh" and isinstance(cached, dict):
        return jsonify(annotate_cache_meta(cached, cache_state="fresh")), 200

    if state == "stale" and isinstance(cached, dict):
        vitrine_cache.schedule_refresh(
            cache_key,
            _bind_app_context(
                lambda: build_contextual_vitrine(
                    id_matu=id_matu,
                    id_clie=id_clie,
                    id_projeto=id_projeto,
                    limit_per_category=limit,
                    recommended_limit=max(limit * 2, 8),
                )
            ),
        )
        return jsonify(annotate_cache_meta(cached, cache_state="stale")), 200

    def _live() -> dict:
        return build_contextual_vitrine(
            id_matu=id_matu,
            id_clie=id_clie,
            id_projeto=id_projeto,
            limit_per_category=limit,
            recommended_limit=max(limit * 2, 8),
        )

    try:
        # Vitrine agrega 3 categorias — budget um pouco maior que offers unitário
        budget = max(LIVE_BUDGET_S * 2, 8.0)
        payload = run_with_live_budget(_bind_app_context(_live), budget_s=budget)
        vitrine_cache.set(cache_key, payload)
        return jsonify(annotate_cache_meta(payload, cache_state="miss")), 200
    except TimeoutError:
        logger.warning("vitrine live budget esgotado — montando shelves via fallback estático")
        ml_circuit.record_failure()
        from app.services.multivendor_orchestrator import (
            CATEGORY_PROFILES,
            _fallback_offers_for_category,
        )

        shelves = []
        for cat in ("formacao", "equipamentos", "software"):
            profile = CATEGORY_PROFILES[cat]
            offers = _fallback_offers_for_category(cat, profile["default_query"], limit)
            shelves.append(
                {
                    "category": cat,
                    "category_label": profile["label"],
                    "offers": offers,
                    "count": len(offers),
                    "source": "fallback",
                }
            )
        payload = {
            "status": "ok",
            "mode": "generic",
            "title": "Explore nossas Soluções",
            "subtitle": "Vitrine curada (modo degradado — live em revalidação).",
            "recommended": [],
            "sprints": [],
            "matched_categories": [],
            "sprint_tags": [],
            "shelves": shelves,
            "notice": "Timeout na montagem live — shelves curadas LeAction.",
        }
        vitrine_cache.set(cache_key, payload, ttl_s=60, stale_s=300)
        # Revalida em background sem bloquear a resposta
        vitrine_cache.schedule_refresh(cache_key, _bind_app_context(_live))
        return jsonify(annotate_cache_meta(payload, cache_state="miss")), 200
    except Exception:
        logger.exception("Falha na vitrine contextual")
        return (
            jsonify(
                {
                    "status": "error",
                    "error": "Erro ao montar vitrine contextual",
                    "mode": "generic",
                    "recommended": [],
                    "shelves": [],
                    "reliability": {"cache": "miss", "circuit": ml_circuit.snapshot()},
                }
            ),
            500,
        )


@marketplace_bp.get("/categories")
def list_marketplace_categories():
    """Catálogo de categorias de Transformação Digital suportadas pelo agregador."""
    return jsonify(
        {
            "status": "ok",
            "categories": MultivendorOrchestrator.list_categories(),
        }
    ), 200


@marketplace_bp.get("/health")
def marketplace_health():
    """Healthcheck isolado do plugin (não interfere no gateway)."""
    ml_oauth = oauth_setup_info()
    return (
        jsonify(
            {
                "status": "ok",
                "plugin": "marketplace",
                "mode": "federated",
                "ml_configured": is_ml_api_configured(),
                "ml_oauth_app": is_oauth_app_configured(),
                "ml_tokens_ready": has_persisted_or_env_tokens(),
                "ml_redirect_uri_https": ml_oauth.get("redirect_uri_https"),
                "ml_redirect_uri": ml_oauth.get("redirect_uri"),
                "amazon_configured": AmazonService.is_configured(),
                "amazon_credentials": AmazonService.credential_status(),
                "reliability": {
                    "circuit": ml_circuit.snapshot(),
                    "live_budget_s": LIVE_BUDGET_S,
                },
            }
        ),
        200,
    )
