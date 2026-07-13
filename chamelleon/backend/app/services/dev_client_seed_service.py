"""Seed de cliente demo por estágio — espelha seed_dev_client.py do PanelDX."""

from __future__ import annotations

import os
import random
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from werkzeug.security import generate_password_hash

from app.core.dev_users import (
    DEV_DEFAULT_SECTOR,
    DEV_FRAMEWORK_CONSTRUCAO_ID,
    DEV_FRAMEWORK_ID,
    DEV_FRAMEWORK_TELECOM_ID,
    DEV_LEAD_CONSTRUCAO_TENANT_ID,
    DEV_LEAD_TENANT_ID,
    DEV_TEAM_TENANT_ID,
    DEV_USER_EXECUTOR_ID,
    DEV_USER_LEAD_CONSTRUCAO_ID,
    DEV_USER_LEAD_ID,
    DEV_USER_SYSADMIN_ID,
    EMAIL_EXECUTOR_TEST,
    EMAIL_LEAD_CONSTRUCAO,
    EMAIL_LEAD_TEST,
    EMAIL_SYSADMIN,
    EXECUTOR_PASSWORD,
    LEAD_ACCESS_CODE,
    LEAD_CONSTRUCAO_ACCESS_CODE,
    SECTOR_PROFILES,
    SYSADMIN_PASSWORD,
)
from app.core.rbac.constants import ROLE_EXECUTOR, ROLE_LED, ROLE_CONSULTOR, ROLE_SYSADMIN
from app.database.models import (
    ActionPlan,
    AssessmentItem,
    AssessmentResponse,
    AssessmentSubmission,
    Framework,
    LeadAccess,
    MaturityLevel,
    Tenant,
    TenantFramework,
    TenantUser,
    User,
    db,
)
from app.services.diagnostic_report_service import (
    build_diagnostic_report,
    persist_diagnostic_report,
)
from app.services.diagnostic_scoring_service import (
    apply_maturity_scores_to_submission,
    build_scoring_payload,
)

STAGE_LABELS = {
    1: "AGUARDANDO QUESTIONARIO",
    2: "QUESTIONARIO OK",
    3: "DIAGNOSTICO OK",
}

MOCK_ACTION_PLAN_MD = """## Plano de Ação (seed dev)

Plano simulado para demonstração local — sem chamada à IA.

### Prioridades imediatas
1. Consolidar governança de dados e indicadores de maturidade digital.
2. Alinhar visão estratégica com capacidades setoriais prioritárias.
3. Executar quick wins em colaboração e experiência do cliente/usuário.

### Próximos 90 dias
- Formalizar ritos de acompanhamento do gap Presente × Futuro.
- Priorizar blocos metodológicos com maior gap por domínio.
"""


def seed_environment_allowed() -> bool:
    url = os.getenv("DATABASE_URL", "")
    host = (urlparse(url).hostname or "").lower()
    if host in ("127.0.0.1", "localhost", "::1"):
        return True
    return os.getenv("SEED_DEV_ALLOW", "").strip() == "1"


def assert_seed_environment() -> None:
    if not seed_environment_allowed():
        raise RuntimeError(
            "Seed de demo bloqueado fora de localhost. "
            "Defina SEED_DEV_ALLOW=1 para ambientes remotos."
        )


def _ensure_membership(tenant_id: uuid.UUID, user_id: uuid.UUID, role: str) -> None:
    membership = TenantUser.query.filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not membership:
        db.session.add(TenantUser(tenant_id=tenant_id, user_id=user_id, role=role))
    elif membership.role != role:
        membership.role = role


def _upsert_user(
    user_id: uuid.UUID,
    name: str,
    email: str,
    *,
    password: str | None = None,
) -> User:
    email = email.lower().strip()
    user = db.session.get(User, user_id)
    if not user:
        user = User(id=user_id, name=name, email=email)
        db.session.add(user)
    else:
        user.name = name
        user.email = email
    if password:
        user.password_hash = generate_password_hash(password)
    return user


def _ensure_tenant_framework(tenant_id: uuid.UUID, framework_id: str) -> Framework:
    framework = db.session.get(Framework, framework_id)
    if not framework:
        framework = Framework.query.filter_by(is_active=True).order_by(Framework.id.asc()).first()
    if not framework:
        raise ValueError("Nenhum framework publicado. Execute o Estúdio de Criação primeiro.")

    for link in TenantFramework.query.filter_by(tenant_id=tenant_id).all():
        if link.framework_id != framework.id and link.status == "active":
            link.status = "inactive"

    link = TenantFramework.query.filter_by(
        tenant_id=tenant_id, framework_id=framework.id
    ).first()
    if not link:
        db.session.add(
            TenantFramework(
                tenant_id=tenant_id,
                framework_id=framework.id,
                status="active",
            )
        )
    elif link.status != "active":
        link.status = "active"
    return framework


def _ensure_lead_access(tenant_id: uuid.UUID, user_id: uuid.UUID, access_code: str) -> None:
    record = LeadAccess.query.filter_by(tenant_id=tenant_id, user_id=user_id).first()
    if not record:
        db.session.add(
            LeadAccess(
                tenant_id=tenant_id,
                user_id=user_id,
                access_code=access_code,
            )
        )
    else:
        record.access_code = access_code


def _resolve_sector_profile(sector: str | None, framework_id: str | None) -> dict[str, Any]:
    if sector:
        profile = SECTOR_PROFILES.get(sector)
        if not profile:
            raise ValueError(f"Setor invalido '{sector}'. Use: telecom, construcao.")
        return dict(profile)
    if framework_id == DEV_FRAMEWORK_CONSTRUCAO_ID:
        return dict(SECTOR_PROFILES["construcao"])
    if framework_id == DEV_FRAMEWORK_TELECOM_ID:
        return dict(SECTOR_PROFILES["telecom"])
    if framework_id in (None, DEV_FRAMEWORK_ID):
        return dict(SECTOR_PROFILES[DEV_DEFAULT_SECTOR])
    for profile in SECTOR_PROFILES.values():
        if profile["framework_id"] == framework_id:
            return dict(profile)
    raise ValueError(f"Framework '{framework_id}' sem perfil demo configurado.")


def ensure_demo_accounts(
    *,
    framework_id: str | None = None,
    sector: str | None = None,
) -> Framework:
    """Garante tenants, utilizadores demo e vinculo com framework setorial."""
    profile = _resolve_sector_profile(sector, framework_id)
    framework_id = profile["framework_id"]
    tenant_id = profile["tenant_id"]
    user_id = profile["user_id"]

    team_tenant = db.session.get(Tenant, DEV_TEAM_TENANT_ID)
    if not team_tenant:
        team_tenant = Tenant(
            id=DEV_TEAM_TENANT_ID,
            name="Equipe Chamelleon (Dev)",
            document="00000000000199",
        )
        db.session.add(team_tenant)

    lead_tenant = db.session.get(Tenant, tenant_id)
    if not lead_tenant:
        lead_tenant = Tenant(
            id=tenant_id,
            name=profile["tenant_name"],
            document="00.000.000/0001-99",
        )
        db.session.add(lead_tenant)
    else:
        lead_tenant.name = profile["tenant_name"]

    _upsert_user(
        DEV_USER_SYSADMIN_ID,
        "SysAdmin LeAction",
        EMAIL_SYSADMIN,
        password=SYSADMIN_PASSWORD,
    )
    _upsert_user(
        DEV_USER_EXECUTOR_ID,
        "Executor Teste",
        EMAIL_EXECUTOR_TEST,
        password=EXECUTOR_PASSWORD,
    )
    _upsert_user(user_id, profile["user_name"], profile["email"])

    if tenant_id == DEV_LEAD_CONSTRUCAO_TENANT_ID:
        _upsert_user(DEV_USER_LEAD_ID, SECTOR_PROFILES["telecom"]["user_name"], EMAIL_LEAD_TEST)

    _ensure_membership(DEV_TEAM_TENANT_ID, DEV_USER_SYSADMIN_ID, ROLE_SYSADMIN)
    _ensure_membership(DEV_TEAM_TENANT_ID, DEV_USER_EXECUTOR_ID, ROLE_EXECUTOR)
    _ensure_membership(tenant_id, user_id, ROLE_LED)

    _ensure_tenant_framework(DEV_TEAM_TENANT_ID, DEV_FRAMEWORK_CONSTRUCAO_ID)
    lead_framework = _ensure_tenant_framework(tenant_id, framework_id)
    _ensure_lead_access(tenant_id, user_id, profile["access_code"])

    if tenant_id == DEV_LEAD_TENANT_ID:
        construcao = SECTOR_PROFILES["construcao"]
        c_tenant = db.session.get(Tenant, construcao["tenant_id"])
        if not c_tenant:
            c_tenant = Tenant(
                id=construcao["tenant_id"],
                name=construcao["tenant_name"],
                document="00.000.000/0002-88",
            )
            db.session.add(c_tenant)
        _upsert_user(construcao["user_id"], construcao["user_name"], construcao["email"])
        _ensure_membership(construcao["tenant_id"], construcao["user_id"], ROLE_LED)
        _ensure_tenant_framework(construcao["tenant_id"], construcao["framework_id"])
        _ensure_lead_access(
            construcao["tenant_id"],
            construcao["user_id"],
            construcao["access_code"],
        )

    db.session.flush()
    from app.services.okr_service import ensure_canonical_okrs_for_tenant

    ensure_canonical_okrs_for_tenant(tenant_id, commit=False)
    if tenant_id == DEV_LEAD_TENANT_ID:
        ensure_canonical_okrs_for_tenant(SECTOR_PROFILES["construcao"]["tenant_id"], commit=False)
    ensure_canonical_okrs_for_tenant(DEV_TEAM_TENANT_ID, commit=False)
    return lead_framework


def reset_lead_diagnostic_data(
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> int:
    """Remove rascunhos, diagnósticos e planos do lead demo."""
    tenant_id = tenant_id or DEV_LEAD_TENANT_ID
    user_id = user_id or DEV_USER_LEAD_ID

    submissions = AssessmentSubmission.query.filter_by(
        tenant_id=tenant_id,
        user_id=user_id,
    ).all()
    submission_ids = [s.id for s in submissions]
    plan_ids = [s.action_plan_id for s in submissions if s.action_plan_id]

    deleted_responses = 0
    if submission_ids:
        deleted_responses = AssessmentResponse.query.filter(
            AssessmentResponse.submission_id.in_(submission_ids)
        ).delete(synchronize_session=False)

    deleted_submissions = AssessmentSubmission.query.filter(
        AssessmentSubmission.id.in_(submission_ids)
    ).delete(synchronize_session=False) if submission_ids else 0

    deleted_plans = 0
    if plan_ids:
        deleted_plans = ActionPlan.query.filter(ActionPlan.id.in_(plan_ids)).delete(
            synchronize_session=False
        )

    orphan_plans = ActionPlan.query.filter_by(tenant_id=tenant_id).delete(
        synchronize_session=False
    )

    return deleted_submissions + deleted_responses + deleted_plans + orphan_plans


def _pick_random_answer(options: list[dict[str, Any]]) -> tuple[float, int]:
    if not options:
        return 2.0, 0
    idx = random.randint(0, len(options) - 1)
    opt = options[idx]
    value = opt.get("grad_rubr", opt.get("weight", idx))
    try:
        return float(value), idx
    except (TypeError, ValueError):
        return float(idx), idx


def _build_random_answers(
    items: list[AssessmentItem],
) -> list[dict[str, Any]]:
    answers: list[dict[str, Any]] = []
    for item in items:
        value, option_index = _pick_random_answer(item.options or [])
        answers.append(
            {
                "assessment_item_id": item.id,
                "selected_value": value,
                "option_index": option_index,
            }
        )
    return answers


def _resolve_maturity_level(framework_id: str, global_score: float) -> MaturityLevel:
    levels = (
        MaturityLevel.query.filter_by(framework_id=framework_id)
        .order_by(MaturityLevel.level.asc())
        .all()
    )
    if not levels:
        raise ValueError(f"Níveis de maturidade não configurados para '{framework_id}'.")

    if global_score <= 1.5:
        target_level = 1
    elif global_score <= 2.5:
        target_level = 2
    elif global_score <= 3.5:
        target_level = 3
    else:
        target_level = 4

    for level in levels:
        if level.level == target_level:
            return level
    return levels[-1]


def _upsert_submission_responses(
    submission: AssessmentSubmission,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    answers: list[dict[str, Any]],
) -> None:
    for answer in answers:
        item_id = answer["assessment_item_id"]
        selected_value = float(answer["selected_value"])
        option_index = answer.get("option_index")
        raw_response = (
            {"option_index": option_index} if option_index is not None else None
        )

        existing = AssessmentResponse.query.filter_by(
            submission_id=submission.id,
            assessment_item_id=item_id,
        ).first()
        if existing:
            existing.selected_value = selected_value
            existing.raw_response = raw_response
        else:
            db.session.add(
                AssessmentResponse(
                    tenant_id=tenant_id,
                    submission_id=submission.id,
                    assessment_item_id=item_id,
                    user_id=user_id,
                    selected_value=selected_value,
                    raw_response=raw_response,
                )
            )


def _finalize_submission(
    submission: AssessmentSubmission,
    items: list[AssessmentItem],
) -> AssessmentSubmission:
    responses = AssessmentResponse.query.filter_by(submission_id=submission.id).all()
    items_by_id = {item.id: item for item in items}
    catalog_items = items

    scoring = build_scoring_payload(
        responses, items_by_id, catalog_items=catalog_items
    )
    maturity = scoring.get("maturity_scores")
    if maturity:
        apply_maturity_scores_to_submission(submission, maturity)

    score_global = scoring.get("score_global", 0.0)
    maturity_level = _resolve_maturity_level(submission.framework_id, score_global)

    submission.score_global = score_global
    submission.maturity_level_name = maturity_level.name
    submission.scores_por_eixo = scoring.get("scores_por_eixo") or {}
    submission.status = "completed"

    report = build_diagnostic_report(submission, generate_ai_plan=False)
    persist_diagnostic_report(submission, report)

    from app.services.client_journey_service import advance_after_assessment

    advance_after_assessment(submission.tenant_id)
    return submission


def resolve_lead_membership_by_email(email: str) -> tuple[uuid.UUID, uuid.UUID, str]:
    """Retorna (tenant_id, user_id, framework_id) do lead/consultor cliente pelo e-mail."""
    from app.core.tenant_framework_resolver import resolve_framework_for_tenant

    normalized = (email or "").strip().lower()
    if not normalized:
        raise ValueError("Informe o e-mail do utilizador.")

    user = User.query.filter_by(email=normalized).first()
    if not user:
        raise ValueError(f"Utilizador não encontrado: {normalized}")

    membership = (
        TenantUser.query.filter_by(user_id=user.id)
        .filter(TenantUser.role.in_([ROLE_LED, ROLE_CONSULTOR]))
        .first()
    )
    if not membership:
        raise ValueError(f"Nenhuma membership lead/consultor para {normalized}.")

    framework = resolve_framework_for_tenant(membership.tenant_id)
    if not framework:
        raise ValueError("Tenant sem framework ativo.")

    return membership.tenant_id, user.id, framework.id


def apply_dev_client_stage_for_email(
    stage: int,
    email: str,
) -> dict[str, Any]:
    """Posiciona qualquer lead/consultor cliente no estágio 1-3 pelo e-mail."""
    tenant_id, user_id, framework_id = resolve_lead_membership_by_email(email)
    return apply_dev_client_stage(
        stage,
        framework_id=framework_id,
        tenant_id=tenant_id,
        user_id=user_id,
    )


def apply_dev_client_stage(
    stage: int,
    *,
    framework_id: str | None = None,
    sector: str | None = None,
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """Aplica estagio 1-3 no lead demo de um setor ou num tenant/cliente específico."""
    if stage not in STAGE_LABELS:
        raise ValueError("Estagio invalido. Use 1, 2 ou 3.")

    assert_seed_environment()
    explicit_target = tenant_id is not None and user_id is not None

    if explicit_target:
        from app.core.tenant_framework_resolver import resolve_framework_for_tenant

        framework = db.session.get(Framework, framework_id) if framework_id else None
        if not framework:
            framework = resolve_framework_for_tenant(tenant_id)
        if not framework:
            raise ValueError("Nenhum framework ativo para o tenant informado.")
        framework_id = framework.id
        user = db.session.get(User, user_id)
        lead_email = user.email if user else ""
        access_code = None
        sector_label = sector or getattr(framework, "sector", None) or DEV_DEFAULT_SECTOR
    else:
        profile = _resolve_sector_profile(sector, framework_id)
        tenant_id = profile["tenant_id"]
        user_id = profile["user_id"]
        framework_id = profile["framework_id"]
        framework = ensure_demo_accounts(sector=sector or DEV_DEFAULT_SECTOR)
        lead_email = profile["email"]
        access_code = profile["access_code"]
        sector_label = sector or DEV_DEFAULT_SECTOR

    removed = reset_lead_diagnostic_data(tenant_id=tenant_id, user_id=user_id)

    result: dict[str, Any] = {
        "stage": stage,
        "status": STAGE_LABELS[stage],
        "sector": sector_label,
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "framework_id": framework.id,
        "lead_email": lead_email,
        "access_code": access_code,
        "removed_records": removed,
        "answers_count": 0,
        "submission_id": None,
    }

    if stage == 1:
        tenant = db.session.get(Tenant, tenant_id)
        if tenant:
            from app.core.journey_constants import JOURNEY_AGUARDANDO_CONTEXTO
            from app.services.client_journey_service import set_journey_status

            set_journey_status(tenant, JOURNEY_AGUARDANDO_CONTEXTO)
        db.session.commit()
        return result

    items = (
        AssessmentItem.query.filter_by(framework_id=framework.id)
        .order_by(AssessmentItem.axis.asc(), AssessmentItem.id.asc())
        .all()
    )
    if not items:
        raise ValueError(f"Framework '{framework.id}' não possui questões publicadas.")

    answers = _build_random_answers(items)
    result["answers_count"] = len(answers)

    submission = AssessmentSubmission(
        tenant_id=tenant_id,
        user_id=user_id,
        framework_id=framework.id,
        status="in_progress",
    )
    db.session.add(submission)
    db.session.flush()
    _upsert_submission_responses(submission, user_id, tenant_id, answers)

    if stage == 2:
        result["submission_id"] = str(submission.id)
        db.session.commit()
        return result

    _finalize_submission(submission, items)
    tenant = db.session.get(Tenant, submission.tenant_id)
    if tenant:
        tenant.has_active_project = True
        tenant.context_data = {
            "dados_clientes": (
                "Base corporativa e residencial em expansão; decisores em TI e operações; "
                "alta exigência de SLA e experiência digital."
            ),
            "dados_etnograficos": (
                "Base corporativa e residencial em expansão; decisores em TI e operações; "
                "alta exigência de SLA e experiência digital."
            ),
            "dados_mercado": (
                "Setor altamente competitivo e regulado; pressão de concorrentes digitais; "
                "demanda por fibra e serviços em nuvem em crescimento."
            ),
            "mercado_resumo": (
                "Setor altamente competitivo e regulado; pressão de concorrentes digitais; "
                "demanda por fibra e serviços em nuvem em crescimento."
            ),
            "clima_organizacional": (
                "Cultura orientada a resultados com resistência em processos legados; "
                "liderança aberta à transformação; equipes precisam de capacitação contínua."
            ),
            "clima_resumo": (
                "Cultura orientada a resultados com resistência em processos legados; "
                "liderança aberta à transformação; equipes precisam de capacitação contínua."
            ),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    result["submission_id"] = str(submission.id)
    result["score_global"] = submission.score_global
    result["nivel_maturidade"] = submission.maturity_level_name
    result["has_diagnostic_report"] = bool(submission.report_data)
    db.session.commit()
    return result
