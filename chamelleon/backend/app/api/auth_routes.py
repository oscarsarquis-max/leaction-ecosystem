"""Rotas de autenticação — cadastro lead, login LA-* e contexto de sessão."""

import logging

from flask import Blueprint, g, jsonify, request

logger = logging.getLogger(__name__)

from app.core.middlewares import require_tenant_membership
from app.core.rbac.constants import ROLE_LABELS
from app.core.rbac.decorators import require_auth
from app.core.tenant_framework_resolver import resolve_framework_for_tenant
from app.services.client_journey_service import build_journey_payload
from app.database.models import Tenant, TenantUser, User, db
from app.services.lead_auth_service import LeadAuthService

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/sectors")
def list_sectors():
    """Setores/frameworks disponíveis para cadastro (público)."""
    try:
        from app.core.bootstrap import ensure_published_framework

        ensure_published_framework()
        service = LeadAuthService()
        sectors = service.list_sectors()
        return jsonify({"status": "ok", "sectors": sectors}), 200
    except Exception as exc:
        logger.exception("Falha ao listar setores para cadastro")
        return jsonify({"error": f"Erro ao listar setores: {exc}"}), 500


@auth_bp.post("/register-lead")
def register_lead():
    """Cadastro inicial do lead com escolha de setor/framework."""
    payload = request.get_json(silent=True) or {}
    try:
        service = LeadAuthService()
        result = service.register_lead(
            name=payload.get("name"),
            email=payload.get("email"),
            company_name=payload.get("company_name"),
            framework_id=payload.get("framework_id"),
            document=payload.get("document"),
        )
        status_code = 201 if result.get("status") == "created" else 200
        return jsonify({"status": "ok", **result}), status_code
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        logger.exception("Falha no cadastro de lead")
        return jsonify({"error": "Erro ao processar cadastro."}), 500


@auth_bp.post("/resend-code")
def resend_access_code():
    """Reenvia código LA-* para lead já cadastrado."""
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    try:
        service = LeadAuthService()
        result = service.resend_access_code(email)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Falha ao reenviar código de acesso")
        return jsonify({"error": "Erro ao reenviar código."}), 500


@auth_bp.post("/reset-lead")
def reset_lead_registration():
    """Remove cadastro lead para recomeçar o fluxo (desenvolvimento)."""
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    try:
        service = LeadAuthService()
        result = service.reset_lead_registration(email)
        status_code = 404 if result.get("status") == "not_found" else 200
        return jsonify(result), status_code
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Falha ao resetar cadastro lead")
        return jsonify({"error": "Erro ao resetar cadastro."}), 500


@auth_bp.get("/dev/lead-access")
def dev_lookup_lead_access():
    """Consulta user_id, tenant_id e código LA-* (desenvolvimento)."""
    email = (request.args.get("email") or "").strip()
    try:
        service = LeadAuthService()
        result = service.lookup_access_code(email)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        logger.exception("Falha na consulta dev de lead_access")
        return jsonify({"error": "Erro na consulta."}), 500


@auth_bp.post("/check-email")
def check_email():
    """Verifica tipo de credencial (lead ou equipe)."""
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    try:
        service = LeadAuthService()
        result = service.check_email(email)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao verificar e-mail."}), 500


@auth_bp.post("/login")
def login():
    """Login unificado: código LA-* (lead) ou senha (equipe)."""
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    credential = payload.get("credential") or payload.get("codigo")
    try:
        service = LeadAuthService()
        result = service.login(email, credential)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc), "success": False}), 401
    except Exception:
        logger.exception("Falha no login: email=%s", email)
        return jsonify({"error": "Erro interno no login.", "success": False}), 500


@auth_bp.get("/me")
@require_tenant_membership
@require_auth
def get_current_user():
    tenant = db.session.get(Tenant, g.tenant_id)
    membership = TenantUser.query.filter_by(
        tenant_id=g.tenant_id, user_id=g.user_id
    ).first()

    framework = resolve_framework_for_tenant(g.tenant_id)
    sector = None
    if framework:
        metadata = framework.rules_metadata or {}
        sector = metadata.get("sector") or framework.industry

    journey = build_journey_payload(tenant) if tenant else None

    return jsonify(
        {
            "status": "ok",
            "user_id": str(g.user_id),
            "user_name": getattr(g, "user_name", None),
            "user_email": getattr(g, "user_email", None),
            "system_role": g.system_role,
            "role_label": ROLE_LABELS.get(g.system_role, g.system_role),
            "tenant_id": str(g.tenant_id),
            "tenant_name": tenant.name if tenant else None,
            "framework_id": getattr(g, "framework_id", None),
            "sector": sector,
            "membership_role": membership.role if membership else None,
            "journey": journey,
        }
    ), 200


@auth_bp.get("/users")
@require_tenant_membership
@require_auth
def list_tenant_users():
    """Lista utilizadores do tenant — útil para troca de perfil em desenvolvimento."""
    rows = (
        TenantUser.query.filter_by(tenant_id=g.tenant_id)
        .join(User, TenantUser.user_id == User.id)
        .all()
    )
    users = [
        {
            "user_id": str(m.user_id),
            "name": m.user.name,
            "email": m.user.email,
            "system_role": m.role,
            "role_label": ROLE_LABELS.get(m.role, m.role),
        }
        for m in rows
    ]
    return jsonify({"status": "ok", "users": users}), 200
