"""Auth interina da Torre de Controle (pré-Etapa 12 completa).

POST /api/auth/login — e-mail + senha do gestor.
GET  /api/auth/me    — sessão atual.
POST /api/auth/logout

Zonas vêm de school_gestor_perfis. Sem zona ativa = login ok, zonas=[].
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash

from db import get_conn

bp = Blueprint("auth", __name__)

SESSION_KEY = "school_gestor"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _serialize_gestor(row: dict[str, Any], zonas: list[str]) -> dict:
    unidade = row.get("unidade_id")
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "unidade_id": str(unidade) if unidade else None,
        "nome": row["nome"],
        "email": row["email"],
        "cargo": row["cargo"],
        "zonas": zonas,
    }


def _load_zonas(cur: Any, gestor_id: uuid.UUID) -> list[str]:
    cur.execute(
        """
        SELECT zona
        FROM public.school_gestor_perfis
        WHERE gestor_id = %s AND ativo = TRUE
        ORDER BY zona
        """,
        (str(gestor_id),),
    )
    return [r["zona"] for r in cur.fetchall()]


@bp.post("/api/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    email = _text(body.get("email")).lower()
    password = str(body.get("password") or "")
    if not email or not password:
        return jsonify({"error": "Informe e-mail e senha"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT *
                FROM public.school_gestores
                WHERE lower(email) = %s AND ativo = TRUE
                LIMIT 1
                """,
                (email,),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "E-mail ou senha inválidos"}), 401

            hash_val = row.get("senha_hash") or ""
            ok = False
            if hash_val.startswith(("pbkdf2:", "scrypt:", "argon2:")):
                ok = check_password_hash(hash_val, password)
            else:
                # Seed / legado em claro (só até Etapa 12 fechar o cadastro de senhas).
                ok = hash_val == password

            if not ok:
                # Bypass de desenvolvimento explícito
                dev_pass = os.getenv("AUTH_DEV_PASSWORD", "").strip()
                if not (dev_pass and password == dev_pass):
                    return jsonify({"error": "E-mail ou senha inválidos"}), 401

            zonas = _load_zonas(cur, uuid.UUID(str(row["id"])))
            user = _serialize_gestor(row, zonas)

    session[SESSION_KEY] = user
    session.permanent = True
    return jsonify({"ok": True, "user": user})


@bp.get("/api/auth/me")
def me():
    user = session.get(SESSION_KEY)
    if not user:
        # 200 (não 401): visita anônima é estado normal; evita ruído no DevTools.
        return jsonify({"authenticated": False, "user": None})
    return jsonify({"authenticated": True, "user": user})


@bp.post("/api/auth/logout")
def logout():
    session.pop(SESSION_KEY, None)
    return jsonify({"ok": True})
