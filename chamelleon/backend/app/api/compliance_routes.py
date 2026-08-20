"""API REST do módulo de Conformidade — treinamento, ASO e não-conformidade."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.core.middlewares import require_tenant_context
from app.core.rbac import ROLE_LED, ROLE_SYSADMIN, require_auth, require_role
from app.services.compliance_service import ComplianceService

compliance_bp = Blueprint("compliance", __name__)

_MANAGER_ROLES = (ROLE_SYSADMIN, ROLE_LED)


@compliance_bp.get("/training-records")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def list_training_records():
    professional_id = (request.args.get("professional_id") or "").strip()
    if not professional_id:
        return jsonify({"error": "Campo obrigatório: professional_id."}), 400
    try:
        rows = ComplianceService().list_training_records(professional_id)
        return jsonify({"status": "ok", "records": rows, "total": len(rows)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao listar treinamentos."}), 500


@compliance_bp.post("/training-records")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def create_training_record():
    payload = request.get_json(silent=True) or {}
    try:
        row = ComplianceService().create_training_record(payload)
        return jsonify({"status": "ok", "record": row}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao criar treinamento."}), 500


@compliance_bp.put("/training-records/<record_id>")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def update_training_record(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        row = ComplianceService().update_training_record(record_id, payload)
        return jsonify({"status": "ok", "record": row}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atualizar treinamento."}), 500


@compliance_bp.delete("/training-records/<record_id>")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def delete_training_record(record_id: str):
    try:
        ComplianceService().delete_training_record(record_id)
        return jsonify({"status": "ok"}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao excluir treinamento."}), 500


@compliance_bp.get("/health-records")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def list_health_records():
    professional_id = (request.args.get("professional_id") or "").strip()
    if not professional_id:
        return jsonify({"error": "Campo obrigatório: professional_id."}), 400
    try:
        rows = ComplianceService().list_health_records(professional_id)
        return jsonify({"status": "ok", "records": rows, "total": len(rows)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao listar exames."}), 500


@compliance_bp.post("/health-records")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def create_health_record():
    payload = request.get_json(silent=True) or {}
    try:
        row = ComplianceService().create_health_record(payload)
        return jsonify({"status": "ok", "record": row}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao criar exame."}), 500


@compliance_bp.put("/health-records/<record_id>")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def update_health_record(record_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        row = ComplianceService().update_health_record(record_id, payload)
        return jsonify({"status": "ok", "record": row}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atualizar exame."}), 500


@compliance_bp.delete("/health-records/<record_id>")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def delete_health_record(record_id: str):
    try:
        ComplianceService().delete_health_record(record_id)
        return jsonify({"status": "ok"}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao excluir exame."}), 500


@compliance_bp.get("/sites/<site_id>/status")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def get_site_compliance_status(site_id: str):
    try:
        status = ComplianceService().get_site_compliance_status(site_id)
        return jsonify({"status": "ok", **status}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao calcular conformidade do canteiro."}), 500


@compliance_bp.get("/non-conformities")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def list_non_conformities():
    site_id = (request.args.get("operational_site_id") or "").strip() or None
    status = (request.args.get("status") or "").strip() or None
    try:
        rows = ComplianceService().list_non_conformities(
            operational_site_id=site_id, status=status
        )
        return jsonify({"status": "ok", "non_conformities": rows, "total": len(rows)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao listar não conformidades."}), 500


@compliance_bp.put("/non-conformities/<nc_id>")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def update_non_conformity(nc_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        row = ComplianceService().update_non_conformity(nc_id, payload)
        return jsonify({"status": "ok", "non_conformity": row}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atualizar não conformidade."}), 500


@compliance_bp.patch("/non-conformities/<nc_id>/assign")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def assign_non_conformity(nc_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        row = ComplianceService().assign_non_conformity(nc_id, payload)
        return jsonify({"status": "ok", "non_conformity": row}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atribuir responsável/prazo."}), 500


@compliance_bp.get("/recurrence-signals")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def list_recurrence_signals():
    site_id = (request.args.get("operational_site_id") or "").strip() or None
    status = (request.args.get("status") or "").strip() or None
    try:
        rows = ComplianceService().list_recurrence_signals(
            operational_site_id=site_id, status=status
        )
        return jsonify({"status": "ok", "recurrence_signals": rows, "total": len(rows)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao listar sinais de recorrência."}), 500


@compliance_bp.post("/recurrence-signals/<signal_id>/mark-seen")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def mark_recurrence_signal_seen(signal_id: str):
    try:
        row = ComplianceService().mark_recurrence_signal_seen(signal_id)
        return jsonify({"status": "ok", "recurrence_signal": row}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao marcar sinal como visto."}), 500


@compliance_bp.post("/recurrence-signals/<signal_id>/dismiss")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def dismiss_recurrence_signal(signal_id: str):
    try:
        row = ComplianceService().dismiss_recurrence_signal(signal_id)
        return jsonify({"status": "ok", "recurrence_signal": row}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao dispensar sinal."}), 500


@compliance_bp.post("/recurrence-signals/<signal_id>/convert")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def convert_recurrence_signal(signal_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        result = ComplianceService().convert_recurrence_signal(signal_id, payload)
        return jsonify({"status": "ok", **result}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao converter sinal em projeto."}), 500


@compliance_bp.get("/corrective-action-projects")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def list_corrective_action_projects():
    try:
        rows = ComplianceService().list_corrective_action_projects()
        return jsonify(
            {"status": "ok", "corrective_action_projects": rows, "total": len(rows)}
        ), 200
    except Exception:
        return jsonify({"error": "Erro ao listar projetos de ação corretiva."}), 500


@compliance_bp.get("/corrective-action-projects/<project_id>")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def get_corrective_action_project(project_id: str):
    try:
        row = ComplianceService().get_corrective_action_project(project_id)
        return jsonify({"status": "ok", "corrective_action_project": row}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao obter projeto."}), 500


@compliance_bp.put("/corrective-action-projects/<project_id>")
@require_tenant_context
@require_auth
@require_role(*_MANAGER_ROLES)
def update_corrective_action_project(project_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        row = ComplianceService().update_corrective_action_project(project_id, payload)
        return jsonify({"status": "ok", "corrective_action_project": row}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atualizar projeto."}), 500
