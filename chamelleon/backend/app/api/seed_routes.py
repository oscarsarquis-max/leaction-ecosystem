"""Rotas de seed para popular o banco com dados de desenvolvimento."""

import uuid

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from app.core.dev_users import (
    DEV_FRAMEWORK_CONSTRUCAO_ID,
    DEV_FRAMEWORK_ID,
    DEV_FRAMEWORK_TELECOM_ID,
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
    MVP_TENANT_ID,
    MVP_USER_ID,
    SECTOR_PROFILES,
    SYSADMIN_PASSWORD,
)
from app.core.rbac.constants import ROLE_EXECUTOR, ROLE_LED, ROLE_SYSADMIN
from app.database.models import (
    AssessmentItem,
    Framework,
    LeadAccess,
    MaturityLevel,
    Tenant,
    TenantFramework,
    TenantUser,
    User,
    db,
)

seed_bp = Blueprint("seed", __name__)

TELECOM_FRAMEWORK_ID = "telecom-v1"


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

    link = TenantFramework.query.filter_by(
        tenant_id=tenant_id, framework_id=framework.id, status="active"
    ).first()
    if not link:
        db.session.add(
            TenantFramework(
                tenant_id=tenant_id,
                framework_id=framework.id,
                status="active",
            )
        )
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


@seed_bp.post("/seed/mvp")
def seed_mvp_context():
    """Cria tenants, utilizadores demo e vinculos com frameworks setoriais (telecom + engenharia)."""
    from app.services.dev_client_seed_service import ensure_demo_accounts, seed_environment_allowed

    if not seed_environment_allowed():
        return jsonify({"error": "Seed disponivel apenas em localhost ou com SEED_DEV_ALLOW=1."}), 403

    try:
        construcao_fw = ensure_demo_accounts(sector="construcao")
        telecom_fw = ensure_demo_accounts(sector="telecom")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    db.session.commit()

    telecom = SECTOR_PROFILES["telecom"]
    construcao = SECTOR_PROFILES["construcao"]

    return jsonify(
        {
            "status": "ok",
            "tenant_id": str(DEV_TEAM_TENANT_ID),
            "frameworks": {
                "telecom": telecom_fw.id,
                "construcao": construcao_fw.id,
            },
            "users": [
                {
                    "user_id": str(DEV_USER_SYSADMIN_ID),
                    "name": "SysAdmin LeAction",
                    "email": EMAIL_SYSADMIN,
                    "system_role": ROLE_SYSADMIN,
                    "tenant_id": str(DEV_TEAM_TENANT_ID),
                    "auth": "password",
                },
                {
                    "user_id": str(telecom["user_id"]),
                    "name": telecom["user_name"],
                    "email": telecom["email"],
                    "system_role": ROLE_LED,
                    "tenant_id": str(telecom["tenant_id"]),
                    "framework_id": telecom["framework_id"],
                    "auth": "access_code",
                    "access_code": telecom["access_code"],
                },
                {
                    "user_id": str(construcao["user_id"]),
                    "name": construcao["user_name"],
                    "email": construcao["email"],
                    "system_role": ROLE_LED,
                    "tenant_id": str(construcao["tenant_id"]),
                    "framework_id": construcao["framework_id"],
                    "auth": "access_code",
                    "access_code": construcao["access_code"],
                },
                {
                    "user_id": str(DEV_USER_EXECUTOR_ID),
                    "name": "Executor Teste",
                    "email": EMAIL_EXECUTOR_TEST,
                    "system_role": ROLE_EXECUTOR,
                    "tenant_id": str(DEV_TEAM_TENANT_ID),
                    "framework_id": construcao["framework_id"],
                    "auth": "password",
                },
            ],
            "credentials_hint": {
                "sysadmin": {"email": EMAIL_SYSADMIN, "password": SYSADMIN_PASSWORD},
                "telecom": {"email": EMAIL_LEAD_TEST, "access_code": LEAD_ACCESS_CODE},
                "construcao": {"email": EMAIL_LEAD_CONSTRUCAO, "access_code": LEAD_CONSTRUCAO_ACCESS_CODE},
                "executor": {"email": EMAIL_EXECUTOR_TEST, "password": EXECUTOR_PASSWORD},
            },
            "message": "Utilizadores demo prontos (padrao: construcao civil).",
        }
    ), 200


@seed_bp.post("/seed/sector-frameworks")
def seed_sector_frameworks():
    """Importa bundles JSON dos frameworks telecom e construcao civil."""
    import os

    from app.services.dev_client_seed_service import seed_environment_allowed
    from app.services.framework_bundle_service import import_framework_bundle, load_framework_bundle_file

    if not seed_environment_allowed():
        return jsonify({"error": "Seed disponivel apenas em localhost ou com SEED_DEV_ALLOW=1."}), 403

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    bundle_dir = os.path.join(repo_root, "infra", "data", "bundles")
    candidates = []
    for framework_id in (DEV_FRAMEWORK_TELECOM_ID, DEV_FRAMEWORK_CONSTRUCAO_ID):
        for suffix in (".json.gz", ".json"):
            path = os.path.join(bundle_dir, f"{framework_id}{suffix}")
            if os.path.isfile(path):
                candidates.append(path)
                break

    if not candidates:
        return jsonify(
            {
                "error": "Bundles nao encontrados.",
                "expected_dir": bundle_dir,
                "hint": "Rode backend/scripts/export_framework_bundle.py localmente.",
            }
        ), 400

    imported = []
    for path in candidates:
        bundle = load_framework_bundle_file(path)
        result = import_framework_bundle(bundle, replace=True)
        imported.append(result)

    for framework_id in (DEV_FRAMEWORK_TELECOM_ID, DEV_FRAMEWORK_CONSTRUCAO_ID):
        fw = db.session.get(Framework, framework_id)
        if fw:
            fw.is_active = True

    db.session.commit()
    return jsonify({"status": "ok", "imported": imported}), 200


@seed_bp.post("/seed/telecom")
def seed_telecom_framework():
    existing = Framework.query.get(TELECOM_FRAMEWORK_ID)
    if existing:
        return jsonify(
            {
                "status": "ok",
                "message": "Framework Telecom já existia.",
                "framework_id": TELECOM_FRAMEWORK_ID,
            }
        ), 200

    framework = Framework(
        id=TELECOM_FRAMEWORK_ID,
        name="Framework de Maturidade — Telecomunicações",
        industry="Telecommunications",
        version="1.0",
        rules_metadata={
            "scale_min": 1,
            "scale_max": 5,
            "axis_weights": {
                "Infraestrutura de Rede": 0.35,
                "Experiência do Cliente": 0.35,
                "Governança Operacional": 0.30,
            },
        },
        is_active=True,
    )

    maturity_levels = [
        MaturityLevel(
            framework_id=TELECOM_FRAMEWORK_ID,
            level=1,
            name="Reativo",
            description="Processos ad hoc; baixa visibilidade de indicadores.",
        ),
        MaturityLevel(
            framework_id=TELECOM_FRAMEWORK_ID,
            level=2,
            name="Estruturado",
            description="Práticas básicas documentadas; métricas parciais.",
        ),
        MaturityLevel(
            framework_id=TELECOM_FRAMEWORK_ID,
            level=3,
            name="Gerenciado",
            description="Operação monitorada com melhoria contínua iniciada.",
        ),
        MaturityLevel(
            framework_id=TELECOM_FRAMEWORK_ID,
            level=4,
            name="Otimizado",
            description="Alta maturidade; decisões orientadas por dados e automação.",
        ),
    ]

    assessment_items = [
        AssessmentItem(
            framework_id=TELECOM_FRAMEWORK_ID,
            axis="Infraestrutura de Rede",
            question_text="Como a operadora monitora a qualidade da rede em tempo real?",
            question_type="multiple_choice",
            options=[
                {"text": "Não há monitoramento estruturado", "weight": 1},
                {"text": "Monitoramento manual e reativo", "weight": 2},
                {"text": "Dashboards com alertas automáticos", "weight": 4},
                {"text": "Observabilidade preditiva com IA", "weight": 5},
            ],
        ),
        AssessmentItem(
            framework_id=TELECOM_FRAMEWORK_ID,
            axis="Experiência do Cliente",
            question_text="Qual o nível de integração dos canais de atendimento (app, call center, loja)?",
            question_type="multiple_choice",
            options=[
                {"text": "Canais isolados sem histórico compartilhado", "weight": 1},
                {"text": "Integração parcial entre canais", "weight": 3},
                {"text": "Jornada omnichannel com contexto unificado", "weight": 5},
            ],
        ),
        AssessmentItem(
            framework_id=TELECOM_FRAMEWORK_ID,
            axis="Governança Operacional",
            question_text="Com que frequência a empresa revisa SLAs e indicadores operacionais?",
            question_type="multiple_choice",
            options=[
                {"text": "Raramente ou nunca", "weight": 1},
                {"text": "Revisão trimestral", "weight": 2},
                {"text": "Revisão mensal com plano de ação", "weight": 4},
                {"text": "Revisão semanal com governança executiva", "weight": 5},
            ],
        ),
    ]

    db.session.add(framework)
    db.session.add_all(maturity_levels)
    db.session.add_all(assessment_items)
    db.session.commit()

    return jsonify(
        {
            "status": "ok",
            "message": "Framework Telecom criado com sucesso.",
            "framework_id": TELECOM_FRAMEWORK_ID,
            "maturity_levels": len(maturity_levels),
            "assessment_items": len(assessment_items),
        }
    ), 200


@seed_bp.post("/seed/dev-client/<int:stage>")
def seed_dev_client_stage(stage: int):
    """
    Posiciona o lead demo (engenharia@paneldx.com.br por padrao) em um estagio do funil.

    1 — sem questionário | 2 — rascunho completo | 3 — diagnóstico + dashboard
    """
    from app.services.dev_client_seed_service import (
        STAGE_LABELS,
        apply_dev_client_stage,
        seed_environment_allowed,
    )

    if not seed_environment_allowed():
        return jsonify(
            {
                "error": "Seed de demo disponível apenas em localhost ou com SEED_DEV_ALLOW=1.",
            }
        ), 403

    if stage not in STAGE_LABELS:
        return jsonify({"error": "Estágio inválido. Use 1, 2 ou 3."}), 400

    body = request.get_json(silent=True) or {}
    framework_id = body.get("framework_id")
    sector = body.get("sector")
    email = (body.get("email") or "").strip().lower() or None

    try:
        if email:
            from app.services.dev_client_seed_service import apply_dev_client_stage_for_email

            payload = apply_dev_client_stage_for_email(stage, email)
        else:
            payload = apply_dev_client_stage(stage, framework_id=framework_id, sector=sector)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 403

    return jsonify(
        {
            "status": "ok",
            "message": f"Lead demo posicionado no estágio {stage}.",
            **payload,
            "credentials_hint": {
                "telecom": {"email": EMAIL_LEAD_TEST, "access_code": LEAD_ACCESS_CODE},
                "construcao": {"email": EMAIL_LEAD_CONSTRUCAO, "access_code": LEAD_CONSTRUCAO_ACCESS_CODE},
                "sysadmin": {"email": EMAIL_SYSADMIN, "password": SYSADMIN_PASSWORD},
                "executor": {"email": EMAIL_EXECUTOR_TEST, "password": EXECUTOR_PASSWORD},
            },
        }
    ), 200
