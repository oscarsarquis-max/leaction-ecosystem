"""Rotas HTTP do módulo de Assessment."""

from flask import Blueprint, g, jsonify, request

from app.core.middlewares import require_tenant_context
from app.core.rbac import ROLE_CONSULTOR, ROLE_LED, ROLE_SYSADMIN, require_auth, require_role
from app.services.assessment_service import AssessmentService

assessment_bp = Blueprint("assessment", __name__)


_ASSESSMENT_FORM_ROLES = (ROLE_LED, ROLE_CONSULTOR, ROLE_SYSADMIN)


@assessment_bp.get("/surveys")
@require_tenant_context
@require_auth
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def list_surveys():
    search = request.args.get("q", "").strip() or None
    try:
        service = AssessmentService()
        surveys = service.list_surveys(search=search)
        return jsonify({"status": "ok", "surveys": surveys, "total": len(surveys)}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao listar surveys."}), 500


@assessment_bp.get("/my-result")
@require_tenant_context
@require_auth
@require_role(ROLE_LED, ROLE_CONSULTOR)
def get_my_latest_result():
    """Último diagnóstico do lead autenticado — para exibir em Meu Resultado."""
    try:
        service = AssessmentService()
        survey = service.get_my_latest_submission()
        if not survey:
            return jsonify({"status": "ok", "result": None}), 200
        return jsonify({"status": "ok", "result": survey}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao carregar resultado."}), 500


@assessment_bp.get("/surveys/<submission_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_CONSULTOR, ROLE_SYSADMIN)
def get_survey(submission_id: str):
    try:
        service = AssessmentService()
        survey = service.get_survey(submission_id)
        return jsonify({"status": "ok", **survey}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao carregar survey."}), 500


@assessment_bp.get("/questions")
@require_tenant_context
@require_auth
@require_role(*_ASSESSMENT_FORM_ROLES)
def get_assessment_questions():
    """Questionário do framework ativo — somente leitura; não cria questões."""
    try:
        service = AssessmentService()
        questionnaire = service.get_questionnaire()
        return jsonify({"status": "ok", **questionnaire}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao carregar questionário."}), 500


@assessment_bp.get("/diagnostic-report/<submission_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_LED, ROLE_CONSULTOR, ROLE_SYSADMIN)
def get_diagnostic_report(submission_id: str):
    try:
        service = AssessmentService()
        report = service.get_diagnostic_report(submission_id)
        return jsonify({"status": "ok", "report": report}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao carregar relatório de diagnóstico."}), 500


@assessment_bp.get("/action-plan/<action_plan_id>")
@require_tenant_context
@require_auth
@require_role(ROLE_LED, ROLE_CONSULTOR, ROLE_SYSADMIN)
def get_action_plan(action_plan_id: str):
    try:
        service = AssessmentService()
        plan = service.get_action_plan(action_plan_id)
        return jsonify({"status": "ok", **plan}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except Exception:
        return jsonify({"error": "Erro ao carregar plano de ação."}), 500


@assessment_bp.get("/draft")
@require_tenant_context
@require_auth
@require_role(*_ASSESSMENT_FORM_ROLES)
def get_assessment_draft():
    try:
        service = AssessmentService()
        draft = service.get_draft(g.user_id)
        if not draft:
            return jsonify({"status": "ok", "draft": None}), 200
        return jsonify({"status": "ok", "draft": draft}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao carregar rascunho."}), 500


@assessment_bp.post("/draft")
@require_tenant_context
@require_auth
@require_role(*_ASSESSMENT_FORM_ROLES)
def save_assessment_draft():
    payload = request.get_json(silent=True) or {}
    respostas = payload.get("respostas")
    if not respostas:
        return jsonify({"error": "Campo obrigatório: respostas."}), 400
    if not isinstance(respostas, list):
        return jsonify({"error": "O campo 'respostas' deve ser uma lista."}), 400

    try:
        service = AssessmentService()
        result = service.save_draft(user_id=g.user_id, answers_list=respostas)
        return jsonify({"status": "ok", **result}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao gravar rascunho."}), 500


@assessment_bp.delete("/draft")
@require_tenant_context
@require_auth
@require_role(*_ASSESSMENT_FORM_ROLES)
def reset_assessment_draft():
    try:
        service = AssessmentService()
        service.reset_draft(g.user_id)
        return jsonify({"status": "ok"}), 200
    except Exception:
        return jsonify({"error": "Erro ao limpar rascunho."}), 500


@assessment_bp.post("/update-present")
@require_tenant_context
@require_auth
@require_role(*_ASSESSMENT_FORM_ROLES)
def update_present_responses():
    """Atualiza Realidade (Presente) no diagnóstico concluído e recalcula o relatório."""
    payload = request.get_json(silent=True) or {}
    respostas = payload.get("respostas")
    if not respostas:
        return jsonify({"error": "Campo obrigatório: respostas."}), 400
    if not isinstance(respostas, list):
        return jsonify({"error": "O campo 'respostas' deve ser uma lista."}), 400

    try:
        service = AssessmentService()
        result = service.update_present_responses(user_id=g.user_id, answers_list=respostas)
        return jsonify({"status": "ok", **result}), 200
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro ao atualizar respostas de realidade."}), 500


@assessment_bp.post("/submit")
@require_tenant_context
@require_auth
@require_role(*_ASSESSMENT_FORM_ROLES)
def submit_assessment():
    """Persiste respostas do diagnóstico — não altera o catálogo de questões."""
    payload = request.get_json(silent=True) or {}

    respostas = payload.get("respostas")
    if not respostas:
        return jsonify({"error": "Campo obrigatório: respostas."}), 400

    if not isinstance(respostas, list):
        return jsonify({"error": "O campo 'respostas' deve ser uma lista."}), 400

    user_id = g.user_id

    try:
        service = AssessmentService()
        result = service.process_submission(
            user_id=user_id,
            answers_list=respostas,
        )
        result["framework_id"] = g.framework_id
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        return jsonify({"error": "Erro interno ao processar o assessment."}), 500
