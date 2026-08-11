"""Ponte School ↔ B2C — aceite de convite + alocações espelhadas (sessão professor)."""
from __future__ import annotations

from functools import wraps

from flask import Blueprint, jsonify, request, session

from psycopg2.extras import RealDictCursor

from db import ensure_instituicao_b2b_columns, get_conn
from services.school_academic_mirror import accept_invite_for_cliente, list_alocacoes_escola

school_bridge_bp = Blueprint("school_bridge", __name__)


def require_session(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = session.get("user")
        if not user or not user.get("id_clie"):
            return jsonify({"error": "Não autenticado"}), 401
        return view(*args, **kwargs)

    return wrapped


def _refresh_session_user(id_clie: int) -> dict | None:
    ensure_instituicao_b2b_columns()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id_clie, nome_clie, mail_clie, empresa_clie,
                       creditos_ia, plan_tier,
                       COALESCE(nina_onboarding_done, FALSE) AS nina_onboarding_done,
                       instituicao_b2b_id, institutional_name
                  FROM public.ctdi_clie
                 WHERE id_clie = %s
                 LIMIT 1
                """,
                (int(id_clie),),
            )
            row = cur.fetchone()
    if not row:
        return None
    inst_raw = row.get("instituicao_b2b_id")
    inst_id = str(inst_raw).strip() if inst_raw else None
    if inst_id in ("", "None", "null"):
        inst_id = None
    user = {
        "id_clie": int(row["id_clie"]),
        "nome_clie": row.get("nome_clie") or "",
        "mail_clie": row.get("mail_clie") or "",
        "empresa_clie": row.get("empresa_clie") or "",
        "creditos_ia": int(row.get("creditos_ia") or 0),
        "plan_tier": str(row.get("plan_tier") or "starter"),
        "nina_onboarding_done": bool(row.get("nina_onboarding_done")),
        "is_institutional": bool(inst_id),
        "instituicao_b2b_id": inst_id,
        "institutional_name": str(row.get("institutional_name") or "").strip() or None,
    }
    # preserva aulas_mes se já na sessão
    prev = session.get("user") or {}
    if prev.get("aulas_mes") is not None:
        user["aulas_mes"] = prev.get("aulas_mes")
    session["user"] = user
    return user


@school_bridge_bp.post("/api/school/aceitar-convite")
@require_session
def aceitar_convite():
    data = request.get_json(silent=True) or {}
    id_clie = int(session["user"]["id_clie"])
    result = accept_invite_for_cliente(
        id_clie=id_clie,
        email=str(data.get("email") or session["user"].get("mail_clie") or "").strip().lower()
        or None,
        instituicao_id=data.get("instituicao_id"),
        vinculo_id=data.get("vinculo_id"),
        institutional_name=data.get("institutional_name") or data.get("instituicao_nome"),
    )
    if not result.get("ok"):
        return jsonify({"error": result.get("reason") or "Falha ao aceitar convite.", **result}), 400
    user = _refresh_session_user(id_clie)
    return jsonify({"ok": True, "user": user, "result": result})


@school_bridge_bp.get("/api/me/alocacoes-escola")
@require_session
def me_alocacoes_escola():
    id_clie = int(session["user"]["id_clie"])
    items = list_alocacoes_escola(id_clie)
    return jsonify({"alocacoes": items, "count": len(items)})
