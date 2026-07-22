"""
MAtivas - Rotas administrativas
=================================================================
Autenticação, CRUD de regras de vocabulário e auditoria de roteiros.
"""

import os
import sys
import csv
import io
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import jwt
from dotenv import load_dotenv
from flask import Blueprint, Response, jsonify, request
from sqlalchemy import text
from werkzeug.security import check_password_hash

# Carrega backend/.env apenas em desenvolvimento (não sobrescreve vars do Docker/produção).
_backend_dir = Path(__file__).resolve().parent.parent
_project_root = _backend_dir.parent
_env_file = _backend_dir / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=False)

for _path in (str(_backend_dir), str(_project_root)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from database.models import AdminUser, VocabularyRule, get_db_session
from ui_content_service import atualizar_ui_content, listar_ui_content_admin

logger = logging.getLogger("mativas.admin")

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


JWT_SECRET = _env("JWT_SECRET", "mativas-dev-secret-change-me")
JWT_EXPIRES_HOURS = int(_env("JWT_EXPIRES_HOURS", "24"))


@contextmanager
def db_session(commit: bool = False):
    """Abre sessão SQLAlchemy e garante fechamento ao final."""
    session = get_db_session()
    try:
        yield session
        if commit:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _create_token(username: str = "admin") -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRES_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _verify_token(token: str) -> dict | None:
    if not token:
        return None
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        if not _verify_token(token):
            return jsonify({"erro": "Não autorizado."}), 401
        return f(*args, **kwargs)

    return decorated


def _rule_to_dict(rule: VocabularyRule) -> dict:
    return {
        "id": rule.id,
        "keyword": rule.keyword,
        "rule_type": rule.rule_type,
        "replacement": rule.replacement,
        "is_active": bool(rule.is_active),
    }


def _authenticate(password: str) -> str | None:
    """Valida senha via ADMIN_PASSWORD (.env) ou tabela admin_users."""
    admin_password = _env("ADMIN_PASSWORD")
    if admin_password and password == admin_password:
        return "admin"

    with db_session() as session:
        users = session.query(AdminUser).all()
        for user in users:
            if check_password_hash(user.password_hash, password):
                return user.username

    return None


@admin_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    password = (data.get("password") or "").strip()

    if not password:
        return jsonify({"erro": "O campo 'password' é obrigatório."}), 400

    username = _authenticate(password)
    if not username:
        return jsonify({"erro": "Senha inválida."}), 401

    token = _create_token(username)
    logger.info("Login admin bem-sucedido (username=%s)", username)
    return jsonify({"sucesso": True, "token": token, "username": username}), 200


@admin_bp.route("/rules", methods=["GET"])
@require_admin
def list_rules():
    with db_session() as session:
        rules = (
            session.query(VocabularyRule)
            .order_by(VocabularyRule.id.asc())
            .all()
        )
        return jsonify([_rule_to_dict(r) for r in rules]), 200


@admin_bp.route("/rules", methods=["POST"])
@require_admin
def create_rule():
    data = request.get_json(silent=True) or {}
    keyword = (data.get("keyword") or "").strip()
    rule_type = (data.get("rule_type") or "").strip()
    replacement = (data.get("replacement") or "").strip() or None

    if not keyword or not rule_type:
        return jsonify({"erro": "Os campos 'keyword' e 'rule_type' são obrigatórios."}), 400

    if rule_type not in ("bloqueada", "substituir", "obrigatoria"):
        return jsonify({"erro": "rule_type deve ser bloqueada, substituir ou obrigatoria."}), 400

    with db_session(commit=True) as session:
        existente = (
            session.query(VocabularyRule)
            .filter(VocabularyRule.keyword == keyword)
            .first()
        )
        if existente:
            return jsonify({"erro": "Já existe uma regra com esta keyword."}), 409

        rule = VocabularyRule(
            keyword=keyword,
            rule_type=rule_type,
            replacement=replacement,
            is_active=1,
        )
        session.add(rule)
        session.flush()
        session.refresh(rule)
        logger.info("Regra criada (id=%s, keyword=%s)", rule.id, rule.keyword)
        return jsonify(_rule_to_dict(rule)), 201


@admin_bp.route("/rules", methods=["PUT"])
@require_admin
def update_rule():
    data = request.get_json(silent=True) or {}
    rule_id = data.get("id")

    if not rule_id:
        return jsonify({"erro": "O campo 'id' é obrigatório para edição."}), 400

    with db_session(commit=True) as session:
        rule = session.query(VocabularyRule).filter(VocabularyRule.id == rule_id).first()
        if not rule:
            return jsonify({"erro": "Regra não encontrada."}), 404

        if "keyword" in data:
            keyword = (data.get("keyword") or "").strip()
            if keyword:
                rule.keyword = keyword
        if "rule_type" in data:
            rule_type = (data.get("rule_type") or "").strip()
            if rule_type:
                if rule_type not in ("bloqueada", "substituir", "obrigatoria"):
                    return jsonify({"erro": "rule_type inválido."}), 400
                rule.rule_type = rule_type
        if "replacement" in data:
            rule.replacement = (data.get("replacement") or "").strip() or None
        if "is_active" in data:
            rule.is_active = 1 if data.get("is_active") else 0

        session.flush()
        session.refresh(rule)
        logger.info("Regra atualizada (id=%s)", rule.id)
        return jsonify(_rule_to_dict(rule)), 200


@admin_bp.route("/rules/<int:rule_id>", methods=["DELETE"])
@require_admin
def delete_rule(rule_id):
    with db_session(commit=True) as session:
        rule = session.query(VocabularyRule).filter(VocabularyRule.id == rule_id).first()
        if not rule:
            return jsonify({"erro": "Regra não encontrada."}), 404

        rule.is_active = 0
        logger.info("Regra desativada (id=%s)", rule_id)
        return jsonify({"id": rule_id, "is_active": False, "mensagem": "Regra desativada."}), 200


@admin_bp.route("/auditoria", methods=["GET"])
@require_admin
def auditoria():
    """Lista projetos recentes com diagnóstico e histórico de interações com a IA.

    Query opcional:
      ?q=termo  — busca seletiva (ILIKE) em metodologia, justificativa, passos,
                  diagnóstico/contexto, dados do professor e o que o professor
                  digitou no diálogo com a IA (prompt_usuario).

    Não busca em prompt_sistema nem resposta_ia: esses campos repetem o
    catálogo/vocabulário da plataforma (ex.: "World Café", "Aprendizagem")
    e fariam termos comuns retornar quase todos os projetos.
    """
    limite = request.args.get("limit", 50, type=int)
    limite = max(1, min(limite, 200))
    # Remove caracteres invisíveis (ZWSP, BOM, etc.) que poluem a caixa de busca
    termo_busca = (request.args.get("q") or "").strip()
    termo_busca = "".join(
        ch for ch in termo_busca if ch.isprintable() and ord(ch) not in (0x200B, 0x200C, 0x200D, 0xFEFF)
    ).strip()

    params = {"limite": limite}
    where_clause = ""

    if termo_busca:
        where_clause = """
                WHERE (
                    COALESCE(r.metodologia_recomendada, '') ILIKE :termo
                    OR COALESCE(r.justificativa, '') ILIKE :termo
                    OR CAST(r.passos_json AS TEXT) ILIKE :termo
                    OR COALESCE(r.status, '') ILIKE :termo
                    OR COALESCE(r.feedback_autora, '') ILIKE :termo
                    OR COALESCE(d.conteudo_desafio, '') ILIKE :termo
                    OR COALESCE(d.sintese, '') ILIKE :termo
                    OR COALESCE(d.opcoes_selecionadas, '') ILIKE :termo
                    OR COALESCE(d.nivel_ensino, '') ILIKE :termo
                    OR COALESCE(d.formato_aula, '') ILIKE :termo
                    OR COALESCE(p.nome, '') ILIKE :termo
                    OR COALESCE(p.email, '') ILIKE :termo
                    OR EXISTS (
                        SELECT 1
                          FROM historico_interacoes_ia hi
                         WHERE hi.professor_id = p.id
                           AND (
                             r.data_geracao IS NULL
                             OR hi.data_registro BETWEEN r.data_geracao - INTERVAL '2 hours'
                                                    AND r.data_geracao + INTERVAL '2 hours'
                           )
                           AND COALESCE(hi.prompt_usuario, '') ILIKE :termo
                    )
                )
                """
        params["termo"] = f"%{termo_busca}%"

    with db_session() as session:
        rows = session.execute(
            text(
                f"""
                SELECT
                    r.id                    AS roteiro_id,
                    r.status,
                    r.metodologia_recomendada,
                    r.justificativa,
                    r.feedback_autora,
                    r.curtido_em,
                    (r.curtido_em IS NOT NULL) AS curtido,
                    r.data_geracao,
                    r.passos_json,
                    p.id                    AS professor_id,
                    p.nome                  AS professor_nome,
                    p.email                 AS professor_email,
                    p.estado                AS professor_estado,
                    d.id                    AS desafio_id,
                    d.conteudo_desafio,
                    d.opcoes_selecionadas,
                    d.nivel_ensino,
                    d.formato_aula,
                    d.sintese,
                    COALESCE(hist.interaction_history, '[]'::json) AS interaction_history
                FROM roteiros r
                JOIN desafios d ON d.id = r.desafio_id
                JOIN professores p ON p.id = d.professor_id
                LEFT JOIN LATERAL (
                    SELECT json_agg(
                        json_build_object(
                            'id', hi.id,
                            'tipo_acao', hi.tipo_acao,
                            'prompt_sistema', hi.prompt_sistema,
                            'prompt_usuario', hi.prompt_usuario,
                            'resposta_ia', hi.resposta_ia,
                            'modelo_ia', hi.modelo_ia,
                            'tokens_prompt', hi.tokens_prompt,
                            'tokens_resposta', hi.tokens_resposta,
                            'data_registro', hi.data_registro
                        ) ORDER BY hi.data_registro DESC
                    ) AS interaction_history
                    FROM historico_interacoes_ia hi
                    WHERE hi.professor_id = p.id
                      AND (
                        r.data_geracao IS NULL
                        OR hi.data_registro BETWEEN r.data_geracao - INTERVAL '2 hours'
                                               AND r.data_geracao + INTERVAL '2 hours'
                      )
                ) hist ON TRUE
                {where_clause}
                ORDER BY r.data_geracao DESC NULLS LAST, r.id DESC
                LIMIT :limite
                """
            ),
            params,
        ).mappings().all()

        logger.info(
            "Auditoria listada (q=%r, resultados=%d)",
            termo_busca or None,
            len(rows),
        )
        payload = []
        for row in rows:
            item = dict(row)
            if item.get("curtido_em") is not None and hasattr(item["curtido_em"], "isoformat"):
                item["curtido_em"] = item["curtido_em"].isoformat(sep=" ", timespec="seconds")
            if item.get("data_geracao") is not None and hasattr(item["data_geracao"], "isoformat"):
                item["data_geracao"] = item["data_geracao"].isoformat(sep=" ", timespec="seconds")
            item["curtido"] = bool(item.get("curtido"))
            payload.append(item)
        return jsonify(payload), 200


# Colunas da planilha completa de auditoria (relatório + usuário + diálogo).
_PLANILHA_COLUNAS = (
    ("roteiro_id", "Projeto ID"),
    ("status", "Status"),
    ("metodologia_recomendada", "Metodologia"),
    ("justificativa", "Justificativa"),
    ("feedback_autora", "Feedback da autora"),
    ("curtido", "Curtido"),
    ("curtido_em", "Data da curtida"),
    ("data_geracao", "Data geracao do roteiro"),
    ("passos_json", "Passos (JSON)"),
    ("professor_id", "Professor ID"),
    ("professor_nome", "Professor nome"),
    ("professor_email", "Professor email"),
    ("professor_estado", "Professor estado"),
    ("desafio_id", "Desafio ID"),
    ("conteudo_desafio", "Desafio"),
    ("opcoes_selecionadas", "Opcoes selecionadas"),
    ("nivel_ensino", "Nivel de ensino"),
    ("formato_aula", "Formato da aula"),
    ("qtd_participantes", "Qtd participantes"),
    ("sintese", "Sintese"),
    ("data_envio_desafio", "Data envio do desafio"),
    ("dialogo_ia_json", "Dialogo IA (JSON)"),
)


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Sim" if value else "Nao"
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


@admin_bp.route("/auditoria/planilha", methods=["GET"])
@require_admin
def auditoria_planilha():
    """Gera CSV (planilha) com o conteúdo completo dos relatórios.

    Inclui dados do professor/usuário, contexto do desafio, roteiro (passos)
    e o diálogo IA↔professor em uma coluna JSON.
    """
    limite = request.args.get("limit", 500, type=int)
    limite = max(1, min(limite, 2000))

    with db_session() as session:
        rows = session.execute(
            text(
                """
                SELECT
                    r.id                    AS roteiro_id,
                    r.status,
                    r.metodologia_recomendada,
                    r.justificativa,
                    r.feedback_autora,
                    (r.curtido_em IS NOT NULL) AS curtido,
                    r.curtido_em,
                    r.data_geracao,
                    r.passos_json,
                    p.id                    AS professor_id,
                    p.nome                  AS professor_nome,
                    p.email                 AS professor_email,
                    p.estado                AS professor_estado,
                    d.id                    AS desafio_id,
                    d.conteudo_desafio,
                    d.opcoes_selecionadas,
                    d.nivel_ensino,
                    d.formato_aula,
                    d.qtd_participantes,
                    d.sintese,
                    d.data_envio            AS data_envio_desafio,
                    COALESCE(hist.dialogo_ia_json, '[]'::json) AS dialogo_ia_json
                FROM roteiros r
                JOIN desafios d ON d.id = r.desafio_id
                JOIN professores p ON p.id = d.professor_id
                LEFT JOIN LATERAL (
                    SELECT json_agg(
                        json_build_object(
                            'id', hi.id,
                            'tipo_acao', hi.tipo_acao,
                            'prompt_sistema', hi.prompt_sistema,
                            'prompt_usuario', hi.prompt_usuario,
                            'resposta_ia', hi.resposta_ia,
                            'modelo_ia', hi.modelo_ia,
                            'tokens_prompt', hi.tokens_prompt,
                            'tokens_resposta', hi.tokens_resposta,
                            'data_registro', hi.data_registro
                        ) ORDER BY hi.data_registro DESC
                    ) AS dialogo_ia_json
                    FROM historico_interacoes_ia hi
                    WHERE hi.professor_id = p.id
                      AND (
                        r.data_geracao IS NULL
                        OR hi.data_registro BETWEEN r.data_geracao - INTERVAL '2 hours'
                                               AND r.data_geracao + INTERVAL '2 hours'
                      )
                ) hist ON TRUE
                ORDER BY r.data_geracao DESC NULLS LAST, r.id DESC
                LIMIT :limite
                """
            ),
            {"limite": limite},
        ).mappings().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow([label for _, label in _PLANILHA_COLUNAS])
    for row in rows:
        item = dict(row)
        item["curtido"] = bool(item.get("curtido"))
        writer.writerow([_cell(item.get(key)) for key, _ in _PLANILHA_COLUNAS])

    # BOM UTF-8 para abrir corretamente no Excel / Google Sheets
    payload = "\ufeff" + buffer.getvalue()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"mativas-auditoria-relatorios-{stamp}.csv"

    logger.info("Planilha de auditoria gerada (%d linhas)", len(rows))
    return Response(
        payload,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@admin_bp.route("/me", methods=["GET"])
@require_admin
def admin_me():
    """Confirma a credencial/sessão administrativa associada ao token."""
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "").strip()
    payload = _verify_token(token) or {}
    username = payload.get("sub") or "admin"
    return jsonify(
        {
            "username": username,
            "auth_mode": "ADMIN_PASSWORD" if _env("ADMIN_PASSWORD") else "admin_users",
            "authenticated": True,
        }
    ), 200


@admin_bp.route("/ui-content", methods=["GET"])
@require_admin
def list_ui_content():
    with db_session() as session:
        return jsonify(listar_ui_content_admin(session)), 200


@admin_bp.route("/ui-content", methods=["PUT"])
@require_admin
def upsert_ui_content():
    data = request.get_json(silent=True) or {}
    key = (data.get("key") or data.get("content_key") or "").strip()
    value = data.get("value")
    if value is None:
        value = data.get("content_value")
    if value is None:
        return jsonify({"erro": "O campo 'value' é obrigatório."}), 400
    value = str(value)
    if not key:
        return jsonify({"erro": "O campo 'key' é obrigatório."}), 400

    content_type = (data.get("type") or data.get("content_type") or "text").strip()
    if content_type not in ("text", "image_url"):
        return jsonify({"erro": "type deve ser text ou image_url."}), 400

    label = data.get("label")

    with db_session(commit=True) as session:
        item = atualizar_ui_content(session, key, value, content_type, label)
        logger.info("Conteúdo UI atualizado (key=%s)", key)
        return jsonify(item), 200
