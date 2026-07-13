"""API REST — Planejamento Estratégico (OKR)."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.core.middlewares import require_tenant_context
from app.core.rbac import (
    ROLE_CONSULTOR,
    ROLE_LED,
    ROLE_SYSADMIN,
    require_auth,
    require_role,
)
from app.services.okr_service import OkrService

okr_bp = Blueprint("okr", __name__)

_OKR_ROLES = (ROLE_LED, ROLE_CONSULTOR, ROLE_SYSADMIN)


@okr_bp.get("/dashboard")
@require_tenant_context
@require_auth
@require_role(*_OKR_ROLES)
def get_dashboard():
    try:
        data = OkrService().list_dashboard()
        return jsonify({"status": "ok", **data}), 200
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao carregar o painel de OKRs."}), 500


@okr_bp.post("/seed")
@require_tenant_context
@require_auth
@require_role(*_OKR_ROLES)
def seed_okrs():
    try:
        seeded = OkrService().ensure_canonical_seed()
        data = OkrService().list_dashboard()
        return (
            jsonify(
                {
                    "status": "ok",
                    "seeded": seeded,
                    "message": (
                        "Matriz canônica PanelDX aplicada."
                        if seeded
                        else "Tenant já possui OKRs — seed ignorado."
                    ),
                    "drivers": data["drivers"],
                }
            ),
            200,
        )
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao aplicar seed de OKRs."}), 500


@okr_bp.post("/drivers")
@require_tenant_context
@require_auth
@require_role(*_OKR_ROLES)
def create_driver():
    payload = request.get_json(silent=True) or {}
    try:
        driver = OkrService().create_driver(payload)
        return jsonify({"status": "ok", "driver": driver.to_dict(include_tree=True)}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao criar direcionador."}), 500


@okr_bp.post("/objectives")
@require_tenant_context
@require_auth
@require_role(*_OKR_ROLES)
def create_objective():
    payload = request.get_json(silent=True) or {}
    try:
        objective = OkrService().create_objective(payload)
        return jsonify({"status": "ok", "objective": objective.to_dict(include_krs=True)}), 201
    except ValueError as exc:
        msg = str(exc)
        status = 404 if "não encontrado" in msg.lower() else 400
        return jsonify({"error": msg}), status
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao criar objetivo."}), 500


@okr_bp.post("/key-results")
@require_tenant_context
@require_auth
@require_role(*_OKR_ROLES)
def create_key_result():
    payload = request.get_json(silent=True) or {}
    try:
        kr = OkrService().create_key_result(payload)
        return jsonify({"status": "ok", "key_result": kr.to_dict()}), 201
    except ValueError as exc:
        msg = str(exc)
        status = 404 if "não encontrado" in msg.lower() else 400
        return jsonify({"error": msg}), status
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao criar Key Result."}), 500


@okr_bp.put("/key-results/<kr_id>")
@require_tenant_context
@require_auth
@require_role(*_OKR_ROLES)
def update_key_result(kr_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        kr = OkrService().update_key_result(kr_id, payload)
        return jsonify({"status": "ok", "key_result": kr.to_dict()}), 200
    except ValueError as exc:
        msg = str(exc)
        status = 404 if "não encontrado" in msg.lower() else 400
        return jsonify({"error": msg}), status
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao atualizar Key Result."}), 500


@okr_bp.post("/kpis")
@require_tenant_context
@require_auth
@require_role(*_OKR_ROLES)
def create_kpi():
    payload = request.get_json(silent=True) or {}
    try:
        kpi = OkrService().create_kpi(payload)
        return jsonify({"status": "ok", "kpi": kpi.to_dict()}), 201
    except ValueError as exc:
        msg = str(exc)
        status = 404 if "não encontrado" in msg.lower() else 400
        return jsonify({"error": msg}), status
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao criar KPI."}), 500


@okr_bp.put("/kpis/<kpi_id>")
@require_tenant_context
@require_auth
@require_role(*_OKR_ROLES)
def update_kpi(kpi_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        kpi = OkrService().update_kpi(kpi_id, payload)
        return jsonify({"status": "ok", "kpi": kpi.to_dict()}), 200
    except ValueError as exc:
        msg = str(exc)
        status = 404 if "não encontrado" in msg.lower() else 400
        return jsonify({"error": msg}), status
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao atualizar KPI."}), 500
