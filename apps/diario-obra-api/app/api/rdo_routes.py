"""Rotas REST do RDO — Gemba mobile-first."""

from flask import Blueprint, jsonify, request

from app.services.rdo_service import RdoService

rdo_bp = Blueprint("rdo", __name__, url_prefix="/api/rdo")


@rdo_bp.post("/sites")
def create_site():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON inválido."}), 400
    try:
        service = RdoService()
        site = service.create_site(payload)
        return jsonify({"status": "ok", "site": service.serialize_site(site)}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao cadastrar canteiro."}), 500


@rdo_bp.get("/sites")
def list_sites():
    tenant_id = request.args.get("tenant_id")
    try:
        service = RdoService()
        sites = service.list_sites(tenant_id=tenant_id)
        return jsonify(
            {"status": "ok", "total": len(sites), "sites": [service.serialize_site(s) for s in sites]}
        ), 200
    except Exception:
        return jsonify({"error": "Erro ao listar canteiros."}), 500


@rdo_bp.get("/logs/<project_id>/month")
def month_calendar(project_id: str):
    try:
        year = int(request.args.get("year", "0"))
        month = int(request.args.get("month", "0"))
        service = RdoService()
        data = service.get_month_calendar(project_id, year, month)
        return jsonify({"status": "ok", **data}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao carregar calendário."}), 500


@rdo_bp.get("/logs/<project_id>/day")
def log_by_day(project_id: str):
    from datetime import date as date_cls

    raw = request.args.get("date", "")
    try:
        log_date = date_cls.fromisoformat(raw[:10])
    except ValueError:
        return jsonify({"error": "Parâmetro date inválido (YYYY-MM-DD)."}), 400

    try:
        service = RdoService()
        log = service.get_log_by_date(project_id, log_date)
        if not log:
            return jsonify(
                {
                    "status": "ok",
                    "log": None,
                    "date": log_date.isoformat(),
                    "is_editable": service.is_log_editable(None, log_date),
                }
            ), 200
        return jsonify({"status": "ok", "log": service.serialize_log(log)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao carregar RDO do dia."}), 500


@rdo_bp.post("/logs")
def create_daily_log_draft():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON inválido."}), 400
    try:
        service = RdoService()
        daily_log = service.create_draft_log(payload)
        return jsonify({"status": "ok", "log": service.serialize_log(daily_log)}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao criar rascunho de RDO."}), 500


@rdo_bp.put("/logs/<log_id>")
def update_daily_log(log_id: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON inválido."}), 400
    try:
        service = RdoService()
        daily_log = service.update_log(log_id, payload)
        return jsonify({"status": "ok", "log": service.serialize_log(daily_log)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atualizar RDO."}), 500


@rdo_bp.get("/logs/<project_id>")
def list_daily_logs(project_id: str):
    try:
        service = RdoService()
        logs = service.list_logs_by_project(project_id)
        return jsonify(
            {
                "status": "ok",
                "project_id": project_id,
                "total": len(logs),
                "logs": [service.serialize_log(log) for log in logs],
            }
        ), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception:
        return jsonify({"error": "Erro ao listar histórico de RDO."}), 500
