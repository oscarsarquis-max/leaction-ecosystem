"""Jornada do cliente — máquina de estados estilo PanelDX (status_ia)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.journey_constants import (
    JOURNEY_AGUARDANDO_CONTEXTO,
    JOURNEY_AVALIACAO_OK,
    JOURNEY_CONCLUIDO,
    JOURNEY_CONTEXTO_OK,
    JOURNEY_DEFAULT,
    JOURNEY_ERRO_IA,
    JOURNEY_PENDENTE,
    JOURNEY_PRESURVEY_OK,
    JOURNEY_PROCESSANDO,
    JOURNEY_PROJETO_OK,
    KANBAN_COLUMNS,
)
from app.database.models import AssessmentSubmission, Tenant, db


def _normalize_status(raw: str | None) -> str:
    return (raw or JOURNEY_DEFAULT).strip().upper()


def _has_completed_assessment(tenant_id) -> bool:
    return (
        AssessmentSubmission.query.filter_by(
            tenant_id=tenant_id,
            status="completed",
        ).first()
        is not None
    )


def _derive_status_from_data(tenant: Tenant) -> str:
    """Backfill para tenants antigos sem journey_status explícito."""
    if getattr(tenant, "journey_status", None):
        return _normalize_status(tenant.journey_status)
    if _has_completed_assessment(tenant.id):
        return JOURNEY_AVALIACAO_OK
    return JOURNEY_DEFAULT


def set_journey_status(tenant: Tenant, status: str) -> None:
    tenant.journey_status = _normalize_status(status)


def advance_after_assessment(tenant_id) -> None:
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        return
    set_journey_status(tenant, JOURNEY_AVALIACAO_OK)


def _context_is_complete(context_data: dict[str, Any]) -> bool:
    mercado = (context_data.get("dados_mercado") or context_data.get("mercado_resumo") or "").strip()
    clientes = (
        context_data.get("dados_clientes")
        or context_data.get("dados_etnograficos")
        or ""
    ).strip()
    clima = (
        context_data.get("clima_organizacional")
        or context_data.get("clima_resumo")
        or ""
    ).strip()
    return len(mercado) >= 40 and len(clientes) >= 40 and len(clima) >= 40


def _normalize_context_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Aceita chaves Chamelleon e legado PanelDX; grava ambas quando aplicável."""
    clientes = (payload.get("dados_clientes") or payload.get("dados_etnograficos") or "").strip()
    mercado = (payload.get("dados_mercado") or payload.get("mercado_resumo") or "").strip()
    clima = (payload.get("clima_organizacional") or payload.get("clima_resumo") or "").strip()

    normalized: dict[str, Any] = {}
    if clientes:
        normalized["dados_clientes"] = clientes
        normalized["dados_etnograficos"] = clientes
    if mercado:
        normalized["dados_mercado"] = mercado
        normalized["mercado_resumo"] = mercado
    if clima:
        normalized["clima_organizacional"] = clima
        normalized["clima_resumo"] = clima

    for key, val in payload.items():
        if key.startswith("moderacao_") and val:
            normalized[key] = val

    return normalized


def save_client_context(tenant_id, payload: dict[str, Any]) -> dict[str, Any]:
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Tenant não encontrado.")
    current = dict(tenant.context_data or {})
    normalized = _normalize_context_payload(payload)
    current.update(normalized)
    if normalized:
        current["completed_at"] = datetime.now(timezone.utc).isoformat()
    tenant.context_data = current
    status = _derive_status_from_data(tenant)
    if status in (JOURNEY_AGUARDANDO_CONTEXTO, JOURNEY_PROJETO_OK, JOURNEY_PRESURVEY_OK):
        set_journey_status(tenant, JOURNEY_CONTEXTO_OK)
    elif status == JOURNEY_AVALIACAO_OK:
        pass
    else:
        set_journey_status(tenant, JOURNEY_CONTEXTO_OK)
    db.session.commit()
    return build_journey_payload(tenant)


def activate_project(tenant_id) -> dict[str, Any]:
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Tenant não encontrado.")
    tenant.has_active_project = True
    status = _derive_status_from_data(tenant)
    if status in (JOURNEY_AGUARDANDO_CONTEXTO, JOURNEY_PRESURVEY_OK):
        set_journey_status(tenant, JOURNEY_PROJETO_OK)
    db.session.commit()
    return build_journey_payload(tenant)


def build_journey_payload(tenant: Tenant) -> dict[str, Any]:
    status_ia = _derive_status_from_data(tenant)
    has_active = bool(getattr(tenant, "has_active_project", False))
    context_data = tenant.context_data or {}
    has_context = _context_is_complete(context_data)

    is_aguardando_contexto = status_ia == JOURNEY_AGUARDANDO_CONTEXTO
    is_presurvey_ok = status_ia == JOURNEY_PRESURVEY_OK
    is_projeto_ok = status_ia == JOURNEY_PROJETO_OK or has_active
    is_contexto_ok = has_context
    is_avaliacao_ok = status_ia == JOURNEY_AVALIACAO_OK or _has_completed_assessment(tenant.id)
    is_em_processamento = status_ia in (JOURNEY_PENDENTE, JOURNEY_PROCESSANDO)
    is_plano_concluido = status_ia == JOURNEY_CONCLUIDO
    is_erro_ia = status_ia == JOURNEY_ERRO_IA

    plano_ativado = (
        has_active
        or is_projeto_ok
        or is_contexto_ok
        or is_avaliacao_ok
        or is_em_processamento
        or is_plano_concluido
    )

    pode_gerar_plano = (
        is_avaliacao_ok
        and is_contexto_ok
        and is_projeto_ok
        and not is_em_processamento
        and not is_plano_concluido
    )
    # Regenerar / atualizar após Gênese ou em falha de IA
    pode_atualizar_plano = (
        is_avaliacao_ok
        and not is_em_processamento
        and (is_plano_concluido or is_erro_ia)
    )

    mostrar_plano_kanban = is_plano_concluido
    mostrar_botao_genese = (
        is_avaliacao_ok
        and not is_em_processamento
        and (not is_plano_concluido or is_erro_ia)
    )

    latest_submission = (
        AssessmentSubmission.query.filter_by(
            tenant_id=tenant.id,
            status="completed",
        )
        .order_by(
            AssessmentSubmission.evaluated_at.desc().nulls_last(),
            AssessmentSubmission.created_at.desc(),
        )
        .first()
    )

    return {
        "status_ia": status_ia,
        "has_active_project": has_active,
        "context_data": context_data,
        "context_filled": has_context,
        "latest_submission_id": str(latest_submission.id) if latest_submission else None,
        "has_diagnostic_report": bool(latest_submission and latest_submission.report_data),
        "flags": {
            "is_aguardando_contexto": is_aguardando_contexto,
            "is_presurvey_ok": is_presurvey_ok,
            "is_projeto_ok": is_projeto_ok,
            "is_contexto_ok": is_contexto_ok,
            "is_avaliacao_ok": is_avaliacao_ok,
            "is_em_processamento": is_em_processamento,
            "is_plano_concluido": is_plano_concluido,
            "is_erro_ia": is_erro_ia,
            "plano_ativado": plano_ativado,
            "pode_gerar_plano": pode_gerar_plano,
            "pode_atualizar_plano": pode_atualizar_plano,
            "mostrar_plano_kanban": mostrar_plano_kanban,
            "mostrar_botao_genese": mostrar_botao_genese,
        },
        "kanban_columns": KANBAN_COLUMNS,
        "steps": [
            {
                "id": "questionario",
                "label": "Questionário completo",
                "done": is_avaliacao_ok,
                "status_target": JOURNEY_AVALIACAO_OK,
            },
            {
                "id": "contexto",
                "label": "Contexto institucional",
                "done": is_contexto_ok,
                "status_target": JOURNEY_CONTEXTO_OK,
            },
            {
                "id": "contrato",
                "label": "Contratação da ferramenta",
                "done": is_projeto_ok,
                "status_target": JOURNEY_PROJETO_OK,
            },
            {
                "id": "plano_ia",
                "label": "Plano gerado por IA",
                "done": is_plano_concluido,
                "status_target": JOURNEY_CONCLUIDO,
            },
        ],
    }


def get_journey_for_tenant(tenant_id) -> dict[str, Any]:
    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Tenant não encontrado.")
    return build_journey_payload(tenant)


def build_td_readiness_status(tenant_id) -> dict[str, Any]:
    """Portão de prontidão para Gênese TD — contexto + avaliação completa."""
    from app.services.assessment_service import AssessmentService

    tenant = db.session.get(Tenant, tenant_id)
    if not tenant:
        raise ValueError("Tenant não encontrado.")

    context_data = tenant.context_data or {}
    context_filled = _context_is_complete(context_data)
    survey_completed = _has_completed_assessment(tenant.id)
    survey_progress_pct = (
        100.0 if survey_completed else AssessmentService().get_tenant_survey_progress_pct(tenant.id)
    )

    is_ready = context_filled and survey_completed

    return {
        "is_ready": is_ready,
        "context_filled": context_filled,
        "survey_completed": survey_completed,
        "survey_progress_pct": round(survey_progress_pct, 1),
    }
