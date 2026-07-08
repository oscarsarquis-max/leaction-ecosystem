"""Rotas do Estúdio de Criação — proposta e ingestão de frameworks via IA."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Callable

from flask import Blueprint, current_app, jsonify, request

from app.core.rbac import ROLE_SYSADMIN, require_auth, require_role
from app.data.legacy_framework_loader import build_full_methodology_document
from app.services.framework_builder_service import FrameworkBuilderService
from app.services.framework_question_import_service import FrameworkQuestionImportService

framework_bp = Blueprint("framework", __name__)

BUILD_PROPOSAL_TIMEOUT_S = 180
BUILD_FRAMEWORK_TIMEOUT_S = 120


def _architecture_guidelines_from_payload(payload: dict[str, Any]) -> dict[str, str | None]:
    strategic = (
        payload.get("strategic_guidelines")
        or payload.get("direcionadores_pesquisa")
        or payload.get("research_guidelines")
        or payload.get("research_guidelines_text")
    )
    operational = payload.get("operational_gemba")
    return {
        "strategic_guidelines": str(strategic).strip() if strategic else None,
        "operational_gemba": str(operational).strip() if operational else None,
    }


def _run_with_app_context(app, func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
    """Executa callable com contexto Flask (app capturado na thread da requisição)."""
    with app.app_context():
        return func(*args, **kwargs)


@framework_bp.get("")
@require_auth
@require_role(ROLE_SYSADMIN)
def list_frameworks():
    """Catálogo de frameworks analisados e aprovados."""
    service = FrameworkBuilderService()
    try:
        frameworks = service.list_frameworks()
        return jsonify({"status": "ok", "frameworks": frameworks}), 200
    except Exception as exc:
        return jsonify({"error": f"Erro ao listar frameworks: {exc}"}), 500


@framework_bp.get("/<framework_id>")
@require_auth
@require_role(ROLE_SYSADMIN)
def get_framework(framework_id: str):
    """Detalhe de um framework publicado (formato editável)."""
    service = FrameworkBuilderService()
    try:
        detail = service.get_framework_detail(framework_id)
        return jsonify({"status": "ok", "proposal": detail}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"Erro ao carregar framework: {exc}"}), 500


@framework_bp.put("/<framework_id>")
@require_auth
@require_role(ROLE_SYSADMIN)
def update_framework(framework_id: str):
    """Atualiza framework publicado."""
    payload = request.get_json(silent=True) or {}
    proposal = payload.get("proposal") or payload

    if not proposal or not isinstance(proposal, dict):
        return jsonify({"error": "Corpo inválido: envie a proposta revisada."}), 400

    service = FrameworkBuilderService()
    try:
        result = service.update_framework(framework_id, proposal)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Erro ao atualizar framework: {exc}"}), 500


@framework_bp.delete("/<framework_id>")
@require_auth
@require_role(ROLE_SYSADMIN)
def delete_framework(framework_id: str):
    """Remove framework do catálogo."""
    service = FrameworkBuilderService()
    try:
        result = service.delete_framework(framework_id)
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"Erro ao remover framework: {exc}"}), 500


@framework_bp.post("/publish")
@require_auth
@require_role(ROLE_SYSADMIN)
def publish_framework():
    """Publica proposta revisada no catálogo (aprovação)."""
    payload = request.get_json(silent=True) or {}
    proposal = payload.get("proposal") or payload
    replace_existing = bool(payload.get("replace"))

    if not proposal or not isinstance(proposal, dict):
        return jsonify({"error": "Corpo inválido: envie a proposta revisada."}), 400

    service = FrameworkBuilderService()

    try:
        result = service.publish_proposal(proposal, replace_existing=replace_existing)
        status_code = 201 if result.get("status") in ("approved", "replaced", "under_review") else 200
        return jsonify(result), status_code
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Erro ao publicar framework: {exc}"}), 500


@framework_bp.post("/build")
@require_auth
@require_role(ROLE_SYSADMIN)
def build_framework():
    """Pipeline completo: persiste framework no banco (catálogo universal + 5ª dimensão IA)."""
    payload = request.get_json(silent=True) or {}
    sector = payload.get("sector") or payload.get("sector_name")
    guidelines = _architecture_guidelines_from_payload(payload)

    if not sector or not str(sector).strip():
        return jsonify({"error": "Campo obrigatório: sector."}), 400

    service = FrameworkBuilderService()
    sector_name = str(sector).strip()
    app = current_app._get_current_object()

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_with_app_context,
                app,
                service.build_framework_for_sector,
                sector_name,
                strategic_guidelines=guidelines["strategic_guidelines"],
                operational_gemba=guidelines["operational_gemba"],
            )
            result = future.result(timeout=BUILD_FRAMEWORK_TIMEOUT_S)

        status_code = 201 if result.get("status") == "created" else 200
        return jsonify(result), status_code

    except FuturesTimeoutError:
        return jsonify(
            {"error": "Tempo esgotado ao construir o framework. Tente novamente."}
        ), 504
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": f"Erro interno ao construir o framework: {exc}"}), 500


@framework_bp.post("/build-proposal")
@require_auth
@require_role(ROLE_SYSADMIN)
def build_framework_proposal():
    payload = request.get_json(silent=True) or {}
    sector = payload.get("sector") or payload.get("sector_name")
    guidelines = _architecture_guidelines_from_payload(payload)

    if not sector or not str(sector).strip():
        return jsonify({"error": "Campo obrigatório: sector."}), 400

    service = FrameworkBuilderService()
    sector_name = str(sector).strip()
    app = current_app._get_current_object()

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                _run_with_app_context,
                app,
                service.research_and_propose,
                sector_name,
                strategic_guidelines=guidelines["strategic_guidelines"],
                operational_gemba=guidelines["operational_gemba"],
            )
            proposal = future.result(timeout=BUILD_PROPOSAL_TIMEOUT_S)

        return jsonify({"status": "ok", "proposal": proposal}), 200

    except FuturesTimeoutError:
        return jsonify(
            {"error": "Tempo esgotado ao pesquisar e gerar a proposta. Tente novamente."}
        ), 504
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception as exc:
        return jsonify({"error": f"Erro interno ao gerar proposta de framework: {exc}"}), 500


@framework_bp.get("/<framework_id>/taxonomy")
@require_auth
@require_role(ROLE_SYSADMIN)
def get_framework_taxonomy_route(framework_id: str):
    """Taxonomia completa PanelDX (dimensões, domínios, blocos, entregáveis)."""
    from app.services.framework_taxonomy_service import (
        ensure_framework_taxonomy,
        get_framework_taxonomy,
    )

    try:
        ensure_framework_taxonomy(framework_id)
        taxonomy = get_framework_taxonomy(framework_id)
        return jsonify({"status": "ok", "taxonomy": taxonomy}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"Erro ao carregar taxonomia: {exc}"}), 500


@framework_bp.get("/<framework_id>/methodology-document")
@require_auth
@require_role(ROLE_SYSADMIN)
def get_framework_methodology_document(framework_id: str):
    """Metodologia persistida (leaf_bloc/leaf_derv) — leitura do banco, sem IA."""
    service = FrameworkBuilderService()
    try:
        structure = service.get_persisted_methodology(framework_id)
        return jsonify({"status": "ok", "methodology_structure": structure}), 200
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404
    except Exception as exc:
        return jsonify({"error": f"Erro ao carregar metodologia: {exc}"}), 500


@framework_bp.post("/<framework_id>/questions/import-json")
@require_auth
@require_role(ROLE_SYSADMIN)
def import_framework_questions_json(framework_id: str):
    """Importa questões de arquivo JSON — apenas frameworks aprovados."""
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"error": "Envie um arquivo JSON no campo 'file' (multipart/form-data)."}), 400

    if not upload.filename.lower().endswith(".json"):
        return jsonify({"error": "O arquivo deve ter extensão .json."}), 400

    service = FrameworkQuestionImportService()
    try:
        result = service.import_json_file(framework_id, upload.read())
        return jsonify(result), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Erro ao importar questões: {exc}"}), 500


@framework_bp.post("/methodology-document")
@require_auth
@require_role(ROLE_SYSADMIN)
def framework_methodology_document():
    """Retorna metodologia — prioriza documento persistido quando framework_id informado."""
    payload = request.get_json(silent=True) or {}
    framework_id = payload.get("framework_id") or payload.get("framework_id_preview")

    service = FrameworkBuilderService()
    if framework_id:
        try:
            structure = service.get_persisted_methodology(str(framework_id))
            return jsonify({"methodology_structure": structure}), 200
        except ValueError:
            pass

    structure = build_full_methodology_document(
        operational_dimension=payload.get("operational_dimension"),
    )
    return jsonify({"methodology_structure": structure}), 200
