"""Auth interina da Torre de Controle (pré-Etapa 12 completa).

POST /api/auth/login — e-mail + senha do gestor.
GET  /api/auth/me    — sessão atual.
POST /api/auth/logout
POST /api/auth/alterar-senha — troca da senha (temporária ou posterior).

Zonas vêm de school_gestor_perfis. Sem zona ativa = login ok, zonas=[].
"""
from __future__ import annotations

import os
import uuid
from typing import Any

from flask import Blueprint, jsonify, request, session
from psycopg2.extras import RealDictCursor
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_conn

bp = Blueprint("auth", __name__)

SESSION_KEY = "school_gestor"


def _text(value: Any) -> str:
    return str(value or "").strip()


def _serialize_gestor(row: dict[str, Any], zonas: list[str]) -> dict:
    unidade = row.get("unidade_id")
    nome_inst = row.get("instituicao_nome") or row.get("razao_social")
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "instituicao_nome": (str(nome_inst).strip() if nome_inst else None) or None,
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
    # Trim evita 401 por espaço colado ao copiar a senha demo.
    password = str(body.get("password") or "").strip()
    if not email or not password:
        return jsonify({"error": "Informe e-mail e senha"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT g.*, i.razao_social AS instituicao_nome
                FROM public.school_gestores g
                JOIN public.school_instituicoes i ON i.id = g.instituicao_id
                WHERE lower(g.email) = %s AND g.ativo = TRUE
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
    # Atualiza nome da instituição / zonas ativas sem forçar relogin
    # (implicação RBAC é avaliada em runtime; isto só sincroniza o payload).
    try:
        gid = uuid.UUID(str(user.get("id") or ""))
    except (ValueError, TypeError, AttributeError):
        return jsonify({"authenticated": True, "user": user})
    try:
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT g.*, i.razao_social AS instituicao_nome
                    FROM public.school_gestores g
                    JOIN public.school_instituicoes i ON i.id = g.instituicao_id
                    WHERE g.id = %s AND g.ativo = TRUE
                    LIMIT 1
                    """,
                    (str(gid),),
                )
                row = cur.fetchone()
                if not row:
                    session.pop(SESSION_KEY, None)
                    return jsonify({"authenticated": False, "user": None})
                zonas = _load_zonas(cur, gid)
                user = _serialize_gestor(row, zonas)
                session[SESSION_KEY] = user
    except Exception:
        pass
    return jsonify({"authenticated": True, "user": user})


@bp.post("/api/auth/logout")
def logout():
    session.pop(SESSION_KEY, None)
    return jsonify({"ok": True})


def _password_ok(hash_val: str, password: str) -> bool:
    if hash_val.startswith(("pbkdf2:", "scrypt:", "argon2:")):
        return bool(check_password_hash(hash_val, password))
    if hash_val == password:
        return True
    dev_pass = os.getenv("AUTH_DEV_PASSWORD", "").strip()
    return bool(dev_pass and password == dev_pass)


@bp.post("/api/auth/alterar-senha")
def alterar_senha():
    user = session.get(SESSION_KEY)
    if not user or not user.get("id"):
        return jsonify({"error": "UNAUTHENTICATED"}), 401
    body = request.get_json(silent=True) or {}
    atual = str(body.get("senha_atual") or body.get("password") or "").strip()
    nova = str(body.get("senha_nova") or body.get("nova_senha") or "").strip()
    if not atual or not nova:
        return jsonify({"error": "Informe a senha atual e a nova senha"}), 400
    if len(nova) < 8:
        return jsonify({"error": "A nova senha precisa ter pelo menos 8 caracteres"}), 400
    if atual == nova:
        return jsonify({"error": "A nova senha deve ser diferente da atual"}), 400

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, senha_hash, created_at, updated_at
                  FROM public.school_gestores
                 WHERE id = %s AND ativo = TRUE
                 LIMIT 1
                """,
                (str(user["id"]),),
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "UNAUTHENTICATED"}), 401
            if not _password_ok(str(row.get("senha_hash") or ""), atual):
                return jsonify({"error": "Senha atual inválida"}), 401
            created = row.get("created_at")
            updated = row.get("updated_at")
            primeira = bool(created and updated and created == updated)
            cur.execute(
                """
                UPDATE public.school_gestores
                   SET senha_hash = %s, updated_at = CURRENT_TIMESTAMP
                 WHERE id = %s
                """,
                (generate_password_hash(nova), str(row["id"])),
            )
    return jsonify({"ok": True, "primeira": primeira})

