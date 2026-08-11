"""PEI legado (planos-gerais) — removido na consolidação do modelo (migration 032).

O Editor Pedagógico usa `/api/aee/*` e `/api/pei/alunos` (`pei_documental_routes`).
Este blueprint permanece registrado só para responder 410 nas rotas antigas e
evitar reabertura acidental de superfície multi-tenant sem sessão.
"""
from __future__ import annotations

from flask import Blueprint, jsonify

bp = Blueprint("pei", __name__)

_GONE = {
    "error": (
        "Endpoint PEI legado removido. "
        "Use /api/aee/* e /api/pei/alunos (modelo consolidado)."
    ),
    "code": "PEI_LEGACY_GONE",
}


def _gone():
    return jsonify(_GONE), 410


@bp.get("/api/instituicoes/<instituicao_id>/pei/planos-gerais")
@bp.post("/api/instituicoes/<instituicao_id>/pei/planos-gerais")
def planos_gerais_collection(instituicao_id: str):
    return _gone()


@bp.get("/api/pei/planos-gerais/<pei_id>")
@bp.put("/api/pei/planos-gerais/<pei_id>")
def planos_gerais_item(pei_id: str):
    return _gone()


@bp.post("/api/pei/planos-gerais/<pei_id>/campos-experiencia")
def planos_gerais_campos(pei_id: str):
    return _gone()


@bp.put("/api/pei/campos-experiencia/<campo_id>")
def campos_experiencia_item(campo_id: str):
    return _gone()
