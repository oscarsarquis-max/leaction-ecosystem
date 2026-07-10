"""API REST do módulo Transformação Digital Inteligente (PanelDX)."""

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
from app.services.td_service import TdService

td_bp = Blueprint("td", __name__)

_TD_ROLES = (ROLE_LED, ROLE_CONSULTOR, ROLE_SYSADMIN)


@td_bp.get("/readiness-status")
@require_tenant_context
@require_auth
@require_role(*_TD_ROLES)
def readiness_status():
    try:
        status = TdService().get_readiness_status()
        return jsonify({"status": "ok", **status}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao verificar prontidão para o plano de TD."}), 500


@td_bp.get("/plan")
@require_tenant_context
@require_auth
@require_role(*_TD_ROLES)
def get_plan():
    try:
        plan = TdService().get_active_plan(include_sprints=True)
        return jsonify({"status": "ok", "plan": plan}), 200
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao carregar o plano de TD."}), 500


@td_bp.post("/plan")
@require_tenant_context
@require_auth
@require_role(*_TD_ROLES)
def create_or_update_plan():
    payload = request.get_json(silent=True) or {}
    try:
        plan = TdService().create_or_update_plan(payload)
        return (
            jsonify(
                {
                    "status": "ok",
                    "plan": plan.to_dict(include_sprints=True),
                    "message": "Plano de TD salvo.",
                }
            ),
            200,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao salvar o plano de TD."}), 500


@td_bp.put("/plan")
@require_tenant_context
@require_auth
@require_role(*_TD_ROLES)
def update_plan():
    return create_or_update_plan()


@td_bp.get("/genesis-status")
@require_tenant_context
@require_auth
@require_role(*_TD_ROLES)
def genesis_status():
    """Polling da Gênese IA — espelho PanelDX genese-status."""
    try:
        from app.core.journey_constants import JOURNEY_CONCLUIDO, JOURNEY_ERRO_IA
        from app.database.models import Tenant, db
        from flask import g

        from app.services.client_journey_service import build_journey_payload

        tenant = db.session.get(Tenant, g.tenant_id)
        if not tenant:
            return jsonify({"error": "Tenant não encontrado."}), 404

        journey = build_journey_payload(tenant)
        status_ia = (journey.get("status_ia") or "").strip().upper()
        ctx = tenant.context_data or {}
        fase_atual = str(ctx.get("_genesis_phase") or "").strip()

        service = TdService()
        plan = service.get_active_plan(include_sprints=True)
        sprints = (plan or {}).get("sprints") or []
        total_sprints = len(sprints)
        tem_sprints = total_sprints > 0
        plano_pronto = status_ia == JOURNEY_CONCLUIDO and tem_sprints
        em_processamento = status_ia in ("PENDENTE", "PROCESSANDO")

        return (
            jsonify(
                {
                    "status_ia": status_ia,
                    "fase_atual": fase_atual,
                    "tem_sprints": tem_sprints,
                    "total_sprints": total_sprints,
                    "plano_pronto": plano_pronto,
                    "em_processamento": em_processamento,
                    "erro": status_ia == JOURNEY_ERRO_IA,
                }
            ),
            200,
        )
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao consultar status da Gênese."}), 500


@td_bp.post("/plan/generate")
@require_tenant_context
@require_auth
@require_role(*_TD_ROLES)
def generate_plan():
    """Gênese TD sob comando do usuário — avança PENDENTE → PROCESSANDO → CONCLUIDO."""
    payload = request.get_json(silent=True) or {}
    force = bool(payload.get("force", True))
    try:
        from app.services.td_genesis_service import TdGenesisService

        result = TdGenesisService().generate_plan(force=force)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        return jsonify({"error": "Erro ao gerar o plano de Transformação Digital."}), 500


@td_bp.get("/sprints")
@require_tenant_context
@require_auth
@require_role(*_TD_ROLES)
def list_sprints():
    """
    Lista sprints do plano ativo.
    Filtros: ``?kanban_stage=Backlog`` ou ``?board=1`` (apenas colunas do Kanban).
    """
    try:
        service = TdService()
        board_flag = request.args.get("board", "").strip().lower() in ("1", "true", "yes")
        if board_flag or request.args.get("kanban", "").strip() in ("1", "true", "yes"):
            board = service.list_kanban()
            return jsonify({"status": "ok", "kanban": board}), 200

        stage = request.args.get("kanban_stage", "").strip() or None
        plan_id = request.args.get("plan_id", "").strip() or None
        sprints = service.list_sprints(kanban_stage=stage, plan_id=plan_id)
        return jsonify({"status": "ok", "sprints": sprints, "total": len(sprints)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao listar sprints de TD."}), 500


@td_bp.post("/sprints")
@require_tenant_context
@require_auth
@require_role(*_TD_ROLES)
def create_sprint():
    payload = request.get_json(silent=True) or {}
    try:
        sprint = TdService().create_sprint(payload)
        return jsonify({"status": "ok", "sprint": sprint.to_dict()}), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao criar sprint de TD."}), 500


@td_bp.put("/sprints/<sprint_id>")
@require_tenant_context
@require_auth
@require_role(*_TD_ROLES)
def update_sprint(sprint_id: str):
    payload = request.get_json(silent=True) or {}
    try:
        sprint = TdService().update_sprint(sprint_id, payload)
        return jsonify({"status": "ok", "sprint": sprint.to_dict()}), 200
    except ValueError as exc:
        msg = str(exc)
        status = 404 if "não encontrada" in msg.lower() else 400
        return jsonify({"error": msg}), status
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao atualizar sprint de TD."}), 500


@td_bp.post("/sprints/<sprint_id>/promote-planning")
@require_tenant_context
@require_auth
@require_role(*_TD_ROLES)
def promote_sprint_planning(sprint_id: str):
    """Promove sprint do Backlog (Plano Geral) para Planejadas no Kanban."""
    try:
        sprint = TdService().promote_sprint_to_planning(sprint_id)
        return (
            jsonify(
                {
                    "status": "ok",
                    "sprint": sprint.to_dict(),
                    "message": "Sprint promovida para Planejadas no Kanban.",
                }
            ),
            200,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao promover sprint para planejamento."}), 500
