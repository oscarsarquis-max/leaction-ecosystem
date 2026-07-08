"""Middleware de acesso por status de contrato — consulta em tempo real ao PostgreSQL."""

from __future__ import annotations

from flask import jsonify, request
from psycopg2.extras import RealDictCursor

from rbac.constants import ROLE_SYSADMIN
from rbac.context import resolve_rbac_context
from services.crm_engine import is_contract_access_allowed

_CONTRACT_EXEMPT_PREFIXES = (
    "/status",
    "/gatekeeper",
    "/manutencao",
    "/api/public/",
    "/api/webhooks/",
    "/api/login",
    "/api/auth/",
    "/api/cadastro",
    "/api/verificar-email",
    "/api/admin/crm",
    "/api/admin/cms",
    "/api/admin/esim",
    "/api/admin/usuarios",
    "/api/admin/mesas-inovacao",
    "/integrations/esim",
    "/inovador",
)


def _is_contract_exempt(path: str) -> bool:
    if request.method == "OPTIONS":
        return True
    for prefix in _CONTRACT_EXEMPT_PREFIXES:
        if path == prefix or path.startswith(prefix):
            return True
    return False


def crm_status_contrato_cliente(cursor, id_clie: int) -> str | None:
    """Contrato vigente do cliente — prioriza status operacional mais recente."""
    cursor.execute(
        """
        SELECT status
        FROM public.dx_contratos
        WHERE id_clie = %s
        ORDER BY
            CASE status
                WHEN 'ativo' THEN 0
                WHEN 'trial' THEN 1
                WHEN 'inadimplente' THEN 2
                WHEN 'cancelado' THEN 3
                ELSE 4
            END,
            data_inicio DESC,
            id DESC
        LIMIT 1;
        """,
        (id_clie,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return row.get("status") if isinstance(row, dict) else row[0]


def register_contract_access_middleware(flask_app) -> None:
    """Bloqueia API quando contrato do id_clie está inadimplente ou cancelado."""

    @flask_app.before_request
    def _enforce_contract_access():
        if _is_contract_exempt(request.path):
            return None

        ctx = resolve_rbac_context()
        if ctx.system_role == ROLE_SYSADMIN:
            return None

        id_clie = ctx.id_clie
        if not id_clie:
            return None

        from app import get_db_conn

        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            status = crm_status_contrato_cliente(cur, int(id_clie))
        except Exception:
            cur.close()
            return None
        finally:
            cur.close()

        if is_contract_access_allowed(status):
            return None

        return jsonify({
            "success": False,
            "status": "error",
            "error": "Acesso suspenso: contrato inadimplente ou cancelado.",
            "contract_status": status,
            "code": "CONTRACT_BLOCKED",
        }), 403
