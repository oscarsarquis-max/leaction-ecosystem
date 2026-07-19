"""Repositório de usuários globais (paneldx_usuarios)."""

from __future__ import annotations

from typing import Any

from rbac.auth_helpers import rbac_infer_system_role_from_team
from rbac.constants import ROLE_LED, SYSTEM_ROLES


def _scalar(row: Any, key: str | None = None) -> Any:
    """Lê primeira coluna ou chave — compatível com tuple e RealDictCursor."""
    if row is None:
        return None
    if isinstance(row, dict):
        if key and key in row:
            return row[key]
        return next(iter(row.values()), None)
    return row[0]


def rbac_normalizar_email(email: str | None) -> str:
    return (email or "").strip().lower()


def rbac_paneldx_usuarios_disponivel(cursor) -> bool:
    cursor.execute("SELECT to_regclass('public.paneldx_usuarios')")
    row = cursor.fetchone()
    return bool(_scalar(row))


def rbac_buscar_usuario_por_email(cursor, email: str) -> dict[str, Any] | None:
    if not rbac_paneldx_usuarios_disponivel(cursor):
        return None
    chave = rbac_normalizar_email(email)
    if not chave:
        return None
    cursor.execute(
        """
        SELECT id_usuario, email, password_hash, nome, system_role, ativo, id_clie
        FROM public.paneldx_usuarios
        WHERE LOWER(TRIM(email)) = %s
        LIMIT 1;
        """,
        (chave,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {
        "id_usuario": row[0],
        "email": row[1],
        "password_hash": row[2],
        "nome": row[3],
        "system_role": row[4],
        "ativo": row[5],
        "id_clie": row[6],
    }


def rbac_buscar_usuario_por_id(cursor, id_usuario: int) -> dict[str, Any] | None:
    if not rbac_paneldx_usuarios_disponivel(cursor):
        return None
    cursor.execute(
        """
        SELECT id_usuario, email, password_hash, nome, system_role, ativo, id_clie
        FROM public.paneldx_usuarios
        WHERE id_usuario = %s
        LIMIT 1;
        """,
        (id_usuario,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {
        "id_usuario": row[0],
        "email": row[1],
        "password_hash": row[2],
        "nome": row[3],
        "system_role": row[4],
        "ativo": row[5],
        "id_clie": row[6],
    }


def rbac_criar_ou_atualizar_usuario(
    cursor,
    *,
    email: str,
    nome: str,
    system_role: str,
    password_hash: str | None = None,
    id_clie: int | None = None,
) -> int:
    chave = rbac_normalizar_email(email)
    role = system_role if system_role in SYSTEM_ROLES else "executor"
    existente = rbac_buscar_usuario_por_email(cursor, chave)
    if existente:
        cursor.execute(
            """
            UPDATE public.paneldx_usuarios
            SET nome = COALESCE(%s, nome),
                system_role = %s,
                password_hash = COALESCE(%s, password_hash),
                id_clie = COALESCE(%s, id_clie),
                ativo = TRUE
            WHERE id_usuario = %s
            RETURNING id_usuario;
            """,
            (nome, role, password_hash, id_clie, existente["id_usuario"]),
        )
        return int(_scalar(cursor.fetchone(), "id_usuario"))

    cursor.execute(
        """
        INSERT INTO public.paneldx_usuarios (email, nome, password_hash, system_role, id_clie)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id_usuario;
        """,
        (chave, nome, password_hash, role, id_clie),
    )
    return int(_scalar(cursor.fetchone(), "id_usuario"))


def rbac_ensure_usuario_lead(cursor, *, id_clie: int, email: str, nome: str) -> int:
    return rbac_criar_ou_atualizar_usuario(
        cursor,
        email=email,
        nome=nome,
        system_role=ROLE_LED,
        id_clie=id_clie,
    )


def rbac_sync_usuario_from_team_row(
    cursor,
    *,
    email: str,
    nome: str,
    role: str | None,
    position: str | None,
    password_hash: str | None,
    admin_email: str | None = None,
) -> int:
    """Cria usuário global a partir de ctdi_team; não rebaixa system_role em updates."""
    chave = rbac_normalizar_email(email)
    existente = rbac_buscar_usuario_por_email(cursor, chave)
    if existente:
        cursor.execute(
            """
            UPDATE public.paneldx_usuarios
            SET nome = COALESCE(%s, nome),
                password_hash = COALESCE(%s, password_hash),
                ativo = TRUE
            WHERE id_usuario = %s
            RETURNING id_usuario;
            """,
            (nome, password_hash, existente["id_usuario"]),
        )
        return int(_scalar(cursor.fetchone(), "id_usuario"))

    system_role = rbac_infer_system_role_from_team(
        role=role,
        position=position,
        email=email,
        admin_email=admin_email,
    )
    return rbac_criar_ou_atualizar_usuario(
        cursor,
        email=email,
        nome=nome,
        system_role=system_role,
        password_hash=password_hash,
    )


def rbac_resolver_id_usuario_por_member(cursor, id_member: int) -> int | None:
    cursor.execute(
        "SELECT id_usuario FROM public.ctdi_team WHERE id_member = %s LIMIT 1;",
        (id_member,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    id_usuario = _scalar(row, "id_usuario")
    return int(id_usuario) if id_usuario else None


def rbac_vincular_team_ao_usuario(cursor, *, id_member: int, id_usuario: int) -> None:
    cursor.execute(
        "UPDATE public.ctdi_team SET id_usuario = %s WHERE id_member = %s;",
        (id_usuario, id_member),
    )


def rbac_buscar_membership_ativa(cursor, id_usuario: int) -> dict[str, Any] | None:
    """Retorna vínculo squad opcional (executores/consultores em squad)."""
    cursor.execute(
        """
        SELECT t.id_member, t.id_squad, t.position, sq.id_proj, p.id_clie
        FROM public.ctdi_team t
        LEFT JOIN public.ctdi_squads sq ON sq.id_squad = t.id_squad
        LEFT JOIN public.ctdi_projetos p ON p.id_proj = sq.id_proj
        WHERE t.id_usuario = %s AND t.ativo = true
        ORDER BY t.id_member DESC
        LIMIT 1;
        """,
        (id_usuario,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return dict(row)
    return {
        "id_member": row[0],
        "id_squad": row[1],
        "position": row[2],
        "id_proj": row[3],
        "id_clie": row[4],
    }


def rbac_formatar_empresa_grupo(row: dict[str, Any] | None) -> str | None:
    """Rótulo legível de empresa ou grupo (rede/holding) vinculado ao usuário."""
    if not row:
        return None
    id_rede = (row.get("id_rede") or "").strip()
    is_holding = bool(row.get("is_holding"))
    empresa = (row.get("empresa_clie") or "").strip()
    nome = (row.get("nome_clie") or "").strip()

    if is_holding and id_rede:
        return f"Grupo {id_rede}"
    partes: list[str] = []
    if empresa:
        partes.append(empresa)
    elif nome:
        partes.append(nome)
    if id_rede and not is_holding:
        partes.append(f"Rede {id_rede}")
    return " · ".join(partes) if partes else None


def rbac_listar_opcoes_empresa_grupo(cursor) -> dict[str, list[dict[str, Any]]]:
    """Opções para filtro admin — empresas (id_clie) e grupos/redes (id_rede)."""
    cursor.execute(
        """
        SELECT c.id_clie,
               c.nome_clie,
               c.empresa_clie,
               c.id_rede,
               COALESCE(c.is_holding, false) AS is_holding,
               COUNT(u.id_usuario) AS qtd_usuarios
        FROM public.ctdi_clie c
        LEFT JOIN public.paneldx_usuarios u ON u.id_clie = c.id_clie
        GROUP BY c.id_clie, c.nome_clie, c.empresa_clie, c.id_rede, c.is_holding
        ORDER BY COALESCE(NULLIF(TRIM(c.empresa_clie), ''), c.nome_clie) ASC, c.nome_clie ASC;
        """
    )
    empresas = []
    for row in cursor.fetchall():
        item = dict(row) if isinstance(row, dict) else {
            "id_clie": row[0],
            "nome_clie": row[1],
            "empresa_clie": row[2],
            "id_rede": row[3],
            "is_holding": row[4],
            "qtd_usuarios": row[5],
        }
        item["label"] = rbac_formatar_empresa_grupo(item) or item.get("nome_clie") or f"Cliente #{item['id_clie']}"
        empresas.append(item)

    cursor.execute(
        """
        SELECT UPPER(TRIM(c.id_rede)) AS id_rede,
               COUNT(DISTINCT c.id_clie) AS qtd_empresas,
               COUNT(DISTINCT u.id_usuario) AS qtd_usuarios,
               BOOL_OR(COALESCE(c.is_holding, false)) AS tem_holding
        FROM public.ctdi_clie c
        LEFT JOIN public.paneldx_usuarios u ON u.id_clie = c.id_clie
        WHERE c.id_rede IS NOT NULL AND TRIM(c.id_rede) <> ''
        GROUP BY UPPER(TRIM(c.id_rede))
        ORDER BY UPPER(TRIM(c.id_rede)) ASC;
        """
    )
    grupos = []
    for row in cursor.fetchall():
        item = dict(row) if isinstance(row, dict) else {
            "id_rede": row[0],
            "qtd_empresas": row[1],
            "qtd_usuarios": row[2],
            "tem_holding": row[3],
        }
        rede = (item.get("id_rede") or "").strip()
        prefixo = "Grupo" if item.get("tem_holding") else "Rede"
        item["label"] = f"{prefixo} {rede}"
        grupos.append(item)

    return {"empresas": empresas, "grupos": grupos}


def rbac_listar_usuarios(
    cursor,
    *,
    incluir_inativos: bool = True,
    busca: str | None = None,
    system_role: str | None = None,
    id_clie: int | None = None,
    id_rede: str | None = None,
) -> list[dict[str, Any]]:
    if not rbac_paneldx_usuarios_disponivel(cursor):
        return []

    clauses: list[str] = []
    params: list[Any] = []

    if not incluir_inativos:
        clauses.append("u.ativo = true")

    termo = (busca or "").strip()
    if termo:
        like = f"%{termo}%"
        clauses.append(
            """(
                u.nome ILIKE %s OR u.email ILIKE %s OR u.system_role ILIKE %s
                OR c.nome_clie ILIKE %s OR c.empresa_clie ILIKE %s
                OR COALESCE(c.id_rede, '') ILIKE %s
            )"""
        )
        params.extend([like, like, like, like, like, like])

    papel = (system_role or "").strip().lower()
    if papel and papel in SYSTEM_ROLES:
        clauses.append("u.system_role = %s")
        params.append(papel)

    if id_clie is not None:
        clauses.append("u.id_clie = %s")
        params.append(int(id_clie))

    rede = (id_rede or "").strip().upper()
    if rede:
        clauses.append(
            """u.id_clie IN (
                SELECT c2.id_clie FROM public.ctdi_clie c2
                WHERE UPPER(TRIM(COALESCE(c2.id_rede, ''))) = %s
            )"""
        )
        params.append(rede)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    cursor.execute(
        f"""
        SELECT u.id_usuario, u.email, u.nome, u.system_role, u.ativo, u.id_clie, u.criado_em,
               c.nome_clie, c.empresa_clie, c.id_rede, COALESCE(c.is_holding, false) AS is_holding
        FROM public.paneldx_usuarios u
        LEFT JOIN public.ctdi_clie c ON c.id_clie = u.id_clie
        {where}
        ORDER BY u.nome ASC, u.id_usuario ASC;
        """,
        tuple(params),
    )
    rows = cursor.fetchall()
    result = []
    for row in rows:
        if isinstance(row, dict):
            item = dict(row)
        else:
            item = {
                "id_usuario": row[0],
                "email": row[1],
                "nome": row[2],
                "system_role": row[3],
                "ativo": row[4],
                "id_clie": row[5],
                "criado_em": row[6],
                "nome_clie": row[7],
                "empresa_clie": row[8],
                "id_rede": row[9],
                "is_holding": row[10],
            }
        item["empresa_grupo"] = rbac_formatar_empresa_grupo(item)
        result.append(item)
    return result


def rbac_listar_usuarios_por_cliente(
    cursor,
    *,
    id_clie: int,
    apenas_empresa: bool = True,
) -> list[dict[str, Any]]:
    """Usuários elegíveis para alocação em squad de um cliente."""
    if not rbac_paneldx_usuarios_disponivel(cursor):
        return []
    if apenas_empresa:
        cursor.execute(
            """
            SELECT id_usuario, email, nome, system_role, ativo, id_clie
            FROM public.paneldx_usuarios
            WHERE ativo = true
              AND id_clie = %s
              AND system_role NOT IN ('consultor', 'sysadmin')
            ORDER BY nome ASC;
            """,
            (id_clie,),
        )
    else:
        cursor.execute(
            """
            SELECT id_usuario, email, nome, system_role, ativo, id_clie
            FROM public.paneldx_usuarios
            WHERE ativo = true
              AND (
                id_clie = %s
                OR (
                    id_clie IS NULL
                    AND system_role IN ('executor', 'consultor')
                )
              )
            ORDER BY nome ASC;
            """,
            (id_clie,),
        )
    rows = cursor.fetchall()
    result = []
    for row in rows:
        if isinstance(row, dict):
            result.append(dict(row))
        else:
            result.append({
                "id_usuario": row[0],
                "email": row[1],
                "nome": row[2],
                "system_role": row[3],
                "ativo": row[4],
                "id_clie": row[5],
            })
    return result


def rbac_id_clie_da_squad(cursor, id_squad: int) -> int | None:
    """Retorna id_clie do projeto ao qual a squad pertence."""
    cursor.execute(
        """
        SELECT p.id_clie
        FROM public.ctdi_squads sq
        JOIN public.ctdi_projetos p ON p.id_proj = sq.id_proj
        WHERE sq.id_squad = %s
        LIMIT 1
        """,
        (int(id_squad),),
    )
    row = cursor.fetchone()
    if not row:
        return None
    if isinstance(row, dict):
        return row.get("id_clie")
    return row[0]
