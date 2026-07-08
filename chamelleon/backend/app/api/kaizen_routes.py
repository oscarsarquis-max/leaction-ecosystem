"""API REST do módulo Gemba-Kaizen — tickets Lean e Kanban."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.core.middlewares import require_tenant_context
from app.core.rbac import (
    ROLE_CONSULTOR,
    ROLE_EXECUTOR,
    ROLE_LED,
    ROLE_SYSADMIN,
    require_auth,
    require_role,
)
from app.services.gemba_walk_service import GembaWalkService
from app.services.kaizen_service import KaizenService

kaizen_bp = Blueprint("kaizen", __name__)

_KAIZEN_ROLES = (ROLE_EXECUTOR, ROLE_LED, ROLE_CONSULTOR, ROLE_SYSADMIN)


@kaizen_bp.get("/tickets")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def list_tickets():
    """
    Lista tickets do tenant — use ``?kanban=1`` para agrupar por workflow_stage (Kanban).
    Filtro opcional: ``?workflow_stage=Contencao``.
    """
    try:
        service = KaizenService()
        if request.args.get("kanban", "").strip() in ("1", "true", "yes"):
            board = service.list_tickets_kanban()
            return jsonify({"status": "ok", "kanban": board}), 200

        stage = request.args.get("workflow_stage", "").strip() or None
        tickets = service.list_tickets(workflow_stage=stage)
        return jsonify({"status": "ok", "tickets": tickets, "total": len(tickets)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao listar tickets Kaizen."}), 500


@kaizen_bp.get("/tickets/<ticket_id>")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def get_ticket(ticket_id: str):
    try:
        ticket = KaizenService().get_ticket(ticket_id)
        return jsonify({"status": "ok", "ticket": ticket}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao carregar ticket Kaizen."}), 500


@kaizen_bp.post("/tickets")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def create_ticket():
    payload = request.get_json(silent=True) or {}
    try:
        ticket = KaizenService().create_ticket(payload)
        return jsonify({"status": "ok", "ticket": ticket.to_dict()}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao criar ticket Kaizen."}), 500


@kaizen_bp.put("/tickets/<ticket_id>")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def update_ticket(ticket_id: str):
    """Atualiza campos do ticket e avança ``workflow_stage`` na jornada Lean."""
    payload = request.get_json(silent=True) or {}
    try:
        ticket = KaizenService().update_ticket(ticket_id, payload)
        return jsonify({"status": "ok", "ticket": ticket.to_dict()}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao atualizar ticket Kaizen."}), 500


@kaizen_bp.post("/tickets/<ticket_id>/five-whys")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def save_five_whys(ticket_id: str):
    """
    Persiste a análise de causa raiz (5 Porquês).

    Body esperado::
        {
          "why_1": "...",
          "why_2": "...",
          "why_3": "...",
          "why_4": "...",
          "why_5": "...",
          "root_cause": "..."
        }
    """
    payload = request.get_json(silent=True) or {}
    try:
        ticket = KaizenService().save_five_whys(ticket_id, payload)
        return jsonify({"status": "ok", "ticket": ticket.to_dict()}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao salvar análise 5 Porquês."}), 500


@kaizen_bp.delete("/tickets/<ticket_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def delete_ticket(ticket_id: str):
    try:
        KaizenService().delete_ticket(ticket_id)
        return jsonify({"status": "ok"}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao excluir ticket Kaizen."}), 500


@kaizen_bp.get("/walks")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def list_walks():
    """Lista Gemba Walks — filtros: ``?status=Agendado`` e ``?date=2026-07-07``."""
    try:
        status = request.args.get("status", "").strip() or None
        date_raw = request.args.get("date", "").strip() or None
        scheduled_date = None
        if date_raw:
            from datetime import date as date_cls

            scheduled_date = date_cls.fromisoformat(date_raw[:10])
        walks = GembaWalkService().list_walks(status=status, scheduled_date=scheduled_date)
        return jsonify({"status": "ok", "walks": walks, "total": len(walks)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao listar Gemba Walks."}), 500


@kaizen_bp.post("/walks")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def create_walk():
    payload = request.get_json(silent=True) or {}
    try:
        walk = GembaWalkService().create_walk(payload)
        return jsonify({"status": "ok", "walk": walk.to_dict()}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao agendar Gemba Walk."}), 500


@kaizen_bp.get("/walks/<walk_id>")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def get_walk(walk_id: str):
    try:
        walk = GembaWalkService().get_walk(walk_id)
        return jsonify({"status": "ok", "walk": walk}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao carregar Gemba Walk."}), 500


@kaizen_bp.post("/walks/<walk_id>/items")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def add_walk_checklist_items(walk_id: str):
    """
    Adiciona lote de itens ao checklist.

    Body: ``{"items": [{"question": "..."}, ...]}``
    """
    payload = request.get_json(silent=True) or {}
    try:
        walk = GembaWalkService().add_checklist_items(walk_id, payload)
        return (
            jsonify({"status": "ok", "walk": walk.to_dict(include_checklist=True)}),
            200,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao adicionar itens ao checklist."}), 500


@kaizen_bp.put("/walks/<walk_id>/items/<item_id>")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def update_walk_checklist_item(walk_id: str, item_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        item = GembaWalkService().update_checklist_item(walk_id, item_id, payload)
        return jsonify({"status": "ok", "item": item.to_dict()}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao atualizar item do checklist."}), 500


@kaizen_bp.put("/walks/<walk_id>/complete")
@require_tenant_context
@require_auth
@require_role(*_KAIZEN_ROLES)
def complete_walk(walk_id: str):
    try:
        walk = GembaWalkService().complete_walk(walk_id)
        return jsonify({"status": "ok", "walk": walk.to_dict(include_checklist=True)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao concluir Gemba Walk."}), 500
