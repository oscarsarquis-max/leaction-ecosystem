"""API REST do módulo operacional — unidades, planejamento e relatórios."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, g, jsonify, request

from app.core.middlewares import require_tenant_context
from app.core.rbac import (
    ROLE_CONSULTOR,
    ROLE_LED,
    ROLE_SYSADMIN,
    require_auth,
    require_role,
)
from app.services.operational_service import OperationalService, week_dates
from app.services.operational_users_service import OperationalUsersService

operational_bp = Blueprint("operational", __name__)

_MANAGER_ROLES = (ROLE_SYSADMIN, ROLE_LED, ROLE_CONSULTOR)


@operational_bp.get("/sites/industry-types")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def list_industry_types():
    from app.models.operational_models import IndustryType

    return (
        jsonify(
            {
                "status": "ok",
                "industry_types": [
                    {"value": member.value, "label": member.value}
                    for member in IndustryType
                ],
            }
        ),
        200,
    )


@operational_bp.get("/sites")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def list_sites():
    try:
        sites = OperationalService().list_sites()
        return jsonify({"status": "ok", "sites": sites, "total": len(sites)}), 200
    except Exception:
        return jsonify({"error": "Erro ao listar unidades operacionais."}), 500


@operational_bp.post("/sites")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def create_site():
    payload = request.get_json(silent=True) or {}
    try:
        site = OperationalService().create_site(payload)
        return jsonify({"status": "ok", "site": site}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        return jsonify({"error": "Erro ao criar unidade operacional."}), 500


@operational_bp.put("/sites/<site_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def update_site(site_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        site = OperationalService().update_site(site_id, payload)
        return jsonify({"status": "ok", "site": site}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atualizar unidade operacional."}), 500


@operational_bp.delete("/sites/<site_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def delete_site(site_id: str):
    try:
        OperationalService().delete_site(site_id)
        return jsonify({"status": "ok"}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao desativar unidade operacional."}), 500


@operational_bp.post("/sites/<site_id>/sync-satellite")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def sync_site_satellite(site_id: str):
    try:
        site = OperationalService().sync_site_to_satellite(site_id)
        return jsonify({"status": "ok", "site": site}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        return jsonify({"error": "Erro ao sincronizar unidade com o satélite."}), 500


@operational_bp.post("/planning/weekly-goals")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def push_weekly_goals():
    payload = request.get_json(silent=True) or {}
    try:
        result = OperationalService().push_weekly_plan(payload)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        return jsonify({"error": "Erro ao enviar planejamento ao satélite."}), 500


@operational_bp.get("/planning/week-dates")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def get_week_dates():
    ref = request.args.get("date", "").strip()
    try:
        base = date.fromisoformat(ref[:10]) if ref else date.today()
    except ValueError:
        base = date.today()
    dates = [d.isoformat() for d in week_dates(base)]
    return jsonify({"status": "ok", "dates": dates}), 200


@operational_bp.get("/reports/summary")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def reports_summary():
    start_raw = request.args.get("start_date", "").strip()
    end_raw = request.args.get("end_date", "").strip()
    site_id = request.args.get("site_id", "").strip() or None
    try:
        today = date.today()
        start_date = date.fromisoformat(start_raw[:10]) if start_raw else today.replace(day=1)
        end_date = date.fromisoformat(end_raw[:10]) if end_raw else today
        summary = OperationalService().reports_summary(
            start_date=start_date, end_date=end_date, site_id=site_id
        )
        return jsonify({"status": "ok", **summary}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao consolidar relatórios operacionais."}), 500


@operational_bp.get("/reports")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def list_reports():
    report_date_raw = request.args.get("date", "").strip()
    site_id = request.args.get("site_id", "").strip() or None
    try:
        report_date = date.fromisoformat(report_date_raw[:10]) if report_date_raw else date.today()
        reports = OperationalService().list_execution_reports(
            report_date=report_date, site_id=site_id
        )
        return jsonify({"status": "ok", "reports": reports, "date": report_date.isoformat()}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao carregar relatórios operacionais."}), 500


@operational_bp.post("/reports/reopen")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def reopen_report_day():
    payload = request.get_json(silent=True) or {}
    site_id = (payload.get("site_id") or payload.get("operational_site_id") or "").strip()
    raw_date = (payload.get("date") or payload.get("report_date") or "").strip()
    if not site_id:
        return jsonify({"error": "Campo obrigatório: site_id."}), 400
    try:
        report_date = date.fromisoformat(raw_date[:10]) if raw_date else date.today()
        result = OperationalService().reopen_execution_day(
            site_id=site_id,
            report_date=report_date,
            reopened_by=payload.get("reopened_by"),
        )
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc) or "Erro ao reabrir dia."}), 500


@operational_bp.get("/users")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def list_tenant_users():
    try:
        users = OperationalUsersService().list_users()
        return jsonify({"status": "ok", "users": users, "total": len(users)}), 200
    except Exception:
        return jsonify({"error": "Erro ao listar utilizadores do tenant."}), 500


@operational_bp.post("/users")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def create_tenant_user():
    payload = request.get_json(silent=True) or {}
    try:
        result = OperationalUsersService().create_user(payload)
        return jsonify({"status": "ok", **result}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao criar utilizador."}), 500


@operational_bp.put("/users/<user_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def update_tenant_user(user_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        result = OperationalUsersService().update_user(user_id, payload)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atualizar utilizador."}), 500


@operational_bp.post("/users/<user_id>/regenerate-code")
@require_tenant_context
@require_auth
@require_role(ROLE_SYSADMIN, ROLE_LED)
def regenerate_tenant_user_code(user_id: str):
    try:
        result = OperationalUsersService().regenerate_lead_code(user_id)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao regenerar código."}), 500
