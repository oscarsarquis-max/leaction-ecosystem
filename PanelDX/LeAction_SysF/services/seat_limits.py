"""Cotas de usuários (seat-based pricing) por plano contratado."""

from __future__ import annotations

SEAT_LIMIT_MESSAGE = (
    "Limite de usuários do plano atingido. Faça um upgrade para adicionar mais membros."
)
DEFAULT_MAX_USUARIOS_SEM_CONTRATO = 5
SEAT_UNLIMITED_THRESHOLD = 999

_CONTRATO_VIGENTE_ORDER = """
    ORDER BY
        CASE c.status
            WHEN 'ativo' THEN 0
            WHEN 'trial' THEN 1
            WHEN 'inadimplente' THEN 2
            WHEN 'cancelado' THEN 3
            ELSE 4
        END,
        c.data_inicio DESC,
        c.id DESC
    LIMIT 1
"""


def _row_val(row, key: str, index: int = 0):
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    return row[index] if len(row) > index else None


def rbac_tem_tabela_usuarios(cursor) -> bool:
    try:
        from rbac.users import rbac_paneldx_usuarios_disponivel
        return rbac_paneldx_usuarios_disponivel(cursor)
    except Exception:
        return False


def contar_usuarios_ativos_cliente(cursor, id_clie: int) -> int:
    if not rbac_tem_tabela_usuarios(cursor):
        return 0
    cursor.execute(
        """
        SELECT COUNT(*)::int
        FROM public.paneldx_usuarios
        WHERE ativo = TRUE
          AND id_clie = %s
          AND system_role NOT IN ('consultor', 'sysadmin');
        """,
        (int(id_clie),),
    )
    row = cursor.fetchone()
    return int(_row_val(row, "count", 0) or 0)


def obter_plano_vigente_cliente(cursor, id_clie: int) -> dict | None:
    from services.addon_engine import obter_contrato_vigente_row

    contrato = obter_contrato_vigente_row(cursor, int(id_clie))
    if not contrato:
        return None
    return {
        "id_contrato": contrato.get("id_contrato"),
        "id_plano": contrato.get("id_plano"),
        "nome_plano": contrato.get("nome_plano"),
        "max_usuarios": int(contrato.get("max_usuarios") or DEFAULT_MAX_USUARIOS_SEM_CONTRATO),
        "status_contrato": contrato.get("status"),
    }


def obter_cota_usuarios(cursor, id_clie: int) -> dict:
    from services.addon_engine import obter_addon_padrao, somar_usuarios_addons_ativos

    plano = obter_plano_vigente_cliente(cursor, int(id_clie))
    usado = contar_usuarios_ativos_cliente(cursor, int(id_clie))

    if plano:
        max_base = int(plano.get("max_usuarios") or DEFAULT_MAX_USUARIOS_SEM_CONTRATO)
        nome_plano = plano.get("nome_plano")
        id_plano = plano.get("id_plano")
        id_contrato = plano.get("id_contrato")
        status_contrato = plano.get("status_contrato")
        max_addons = somar_usuarios_addons_ativos(cursor, int(id_contrato)) if id_contrato else 0
    else:
        max_base = DEFAULT_MAX_USUARIOS_SEM_CONTRATO
        max_addons = 0
        nome_plano = None
        id_plano = None
        id_contrato = None
        status_contrato = None

    max_usuarios = max_base + max_addons
    ilimitado = max_base >= SEAT_UNLIMITED_THRESHOLD
    pode_adicionar = ilimitado or usado < max_usuarios

    addon_padrao = obter_addon_padrao(cursor)
    addon_sugerido = None
    if addon_padrao:
        addon_sugerido = {
            "id": addon_padrao["id"],
            "nome": addon_padrao["nome"],
            "max_usuarios": int(addon_padrao.get("max_usuarios") or 0),
            "valor_mensal": float(addon_padrao.get("valor_mensal") or 0),
            "periodicidade": addon_padrao.get("periodicidade") or "Mensal",
        }

    return {
        "id_clie": int(id_clie),
        "usado": usado,
        "max_base_usuarios": max_base,
        "max_addons_usuarios": max_addons,
        "max_usuarios": max_usuarios,
        "ilimitado": ilimitado,
        "pode_adicionar": pode_adicionar,
        "nome_plano": nome_plano,
        "id_plano": id_plano,
        "id_contrato": id_contrato,
        "status_contrato": status_contrato,
        "addon_sugerido": addon_sugerido,
    }


def validar_pode_adicionar_usuario(cursor, id_clie: int) -> tuple[bool, str | None]:
    cota = obter_cota_usuarios(cursor, int(id_clie))
    if cota.get("pode_adicionar"):
        return True, None
    return False, SEAT_LIMIT_MESSAGE
