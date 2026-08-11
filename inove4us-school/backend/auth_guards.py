"""Autorização RBAC da Torre — lê a sessão Flask já emitida por auth_api.

Não cria sessão paralela. Uso:
  @require_zona("pedagogico")
  def handler(...):
      inst = resolve_instituicao_id(instituicao_id_da_url)  # str ou (resp, code)
"""
from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import jsonify, session

SESSION_KEY = "school_gestor"

ZONA_ADMINISTRATIVO = "administrativo"
ZONA_OPERACIONAL = "operacional"
ZONA_PEDAGOGICO = "pedagogico"


def current_gestor() -> dict[str, Any] | None:
    user = session.get(SESSION_KEY)
    return user if isinstance(user, dict) else None


def require_gestor(view: Callable):
    """Exige sessão com instituicao_id (sem checar zona)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_gestor()
        if not user or not user.get("instituicao_id"):
            return (
                jsonify(
                    {
                        "error": "Não autenticado",
                        "code": "UNAUTHENTICATED",
                    }
                ),
                401,
            )
        return view(*args, **kwargs)

    return wrapped


def require_zona(*zonas_required: str):
    """Exige sessão + ao menos uma das zonas listadas."""

    needed = tuple(z for z in zonas_required if z)

    def deco(view: Callable):
        @wraps(view)
        @require_gestor
        def wrapped(*args, **kwargs):
            user = current_gestor() or {}
            have = {str(z) for z in (user.get("zonas") or []) if z}
            if needed and not have.intersection(needed):
                labels = {
                    ZONA_ADMINISTRATIVO: "Administrativo",
                    ZONA_OPERACIONAL: "Operacional",
                    ZONA_PEDAGOGICO: "Pedagógico",
                }
                req_lbl = [labels.get(z, z) for z in needed]
                return (
                    jsonify(
                        {
                            "error": (
                                "Sem permissão para esta área. "
                                f"Zona necessária: {', '.join(req_lbl)}."
                            ),
                            "code": "FORBIDDEN_ZONA",
                            "zonas_requeridas": list(needed),
                            "zonas_usuario": sorted(have),
                        }
                    ),
                    403,
                )
            return view(*args, **kwargs)

        return wrapped

    return deco


def resolve_instituicao_id(claimed: Any = None):
    """
    Instituição da sessão. Se `claimed` (URL/query/body) vier preenchido,
    deve coincidir — senão 403 (anti vazamento multi-tenant).
    Retorna str ou (Response, status).
    """
    user = current_gestor() or {}
    sid = str(user.get("instituicao_id") or "").strip()
    if not sid:
        return (
            jsonify({"error": "Não autenticado", "code": "UNAUTHENTICATED"}),
            401,
        )
    if claimed is not None and str(claimed).strip():
        if str(claimed).strip() != sid:
            return (
                jsonify(
                    {
                        "error": "Instituição fora do escopo da sessão.",
                        "code": "FORBIDDEN_INSTITUICAO",
                    }
                ),
                403,
            )
    return sid


def gestor_unidade_id() -> str | None:
    user = current_gestor() or {}
    uid = user.get("unidade_id")
    if uid is None or uid == "":
        return None
    return str(uid).strip() or None


def resolve_unidade_id(claimed: Any = None):
    """
    Escopo de unidade do gestor (nullable).
    - Sem escopo: devolve claimed (ou None).
    - Com escopo: força a unidade do gestor; claimed divergente → 403.
    Retorna str|None ou (Response, status).
    """
    scope = gestor_unidade_id()
    claimed_s = str(claimed).strip() if claimed is not None and str(claimed).strip() else None
    if not scope:
        return claimed_s
    if claimed_s and claimed_s != scope:
        return (
            jsonify(
                {
                    "error": "Unidade fora do escopo do gestor.",
                    "code": "FORBIDDEN_UNIDADE",
                }
            ),
            403,
        )
    return scope
