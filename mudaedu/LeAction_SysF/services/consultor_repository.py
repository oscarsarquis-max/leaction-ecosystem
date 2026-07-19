"""Repositório — perfis de consultor (dx_consultores) e onboarding automático."""

from __future__ import annotations

from typing import Any

from rbac.constants import ROLE_CONSULTOR

TIPOS_CONSULTOR = frozenset({"agencia", "individual"})
DEFAULT_TAXA_VENDA = 10.00
DEFAULT_TAXA_TECNICA = 15.00


def _decimal_to_float(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def serializar_consultor(row: dict) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "nome": row.get("nome"),
        "email": row.get("email"),
        "tipo": row.get("tipo"),
        "id_agencia_pai": row.get("id_agencia_pai"),
        "nome_agencia_pai": row.get("nome_agencia_pai"),
        "taxa_comissao_venda": _decimal_to_float(row.get("taxa_comissao_venda")),
        "taxa_comissao_tecnica": _decimal_to_float(row.get("taxa_comissao_tecnica")),
        "ativo": bool(row.get("ativo", True)),
        "label": _montar_label(row),
    }


def _montar_label(row: dict) -> str:
    tipo_label = "Agência" if row.get("tipo") == "agencia" else "Individual"
    base = f"{row.get('nome')} ({tipo_label}"
    if row.get("nome_agencia_pai"):
        base += f" · {row['nome_agencia_pai']}"
    return base + ")"


def _select_consultor_sql(extra_where: str = "") -> str:
    return f"""
        SELECT c.id, c.user_id, c.tipo, c.id_agencia_pai,
               c.taxa_comissao_venda, c.taxa_comissao_tecnica, c.ativo,
               u.nome, u.email,
               pai.nome AS nome_agencia_pai
        FROM public.dx_consultores c
        INNER JOIN public.paneldx_usuarios u ON u.id_usuario = c.user_id
        LEFT JOIN public.dx_consultores ag ON ag.id = c.id_agencia_pai
        LEFT JOIN public.paneldx_usuarios pai ON pai.id_usuario = ag.user_id
        {extra_where}
    """


def buscar_consultor_por_id(cur, consultor_id: int) -> dict | None:
    cur.execute(
        _select_consultor_sql("WHERE c.id = %s"),
        (consultor_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def buscar_consultor_por_user_id(cur, user_id: int) -> dict | None:
    cur.execute(
        _select_consultor_sql("WHERE c.user_id = %s"),
        (user_id,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def listar_consultores(cur, *, incluir_inativos: bool = False) -> list[dict]:
    where = "" if incluir_inativos else "WHERE c.ativo = TRUE"
    cur.execute(
        f"""
        {_select_consultor_sql(where)}
        ORDER BY
            CASE c.tipo WHEN 'agencia' THEN 0 ELSE 1 END,
            u.nome ASC;
        """
    )
    return [serializar_consultor(dict(row)) for row in cur.fetchall()]


def listar_usuarios_sem_perfil_consultor(cur) -> list[dict]:
    cur.execute(
        """
        SELECT u.id_usuario, u.nome, u.email, u.ativo
        FROM public.paneldx_usuarios u
        LEFT JOIN public.dx_consultores c ON c.user_id = u.id_usuario
        WHERE u.system_role = %s
          AND u.ativo = TRUE
          AND c.id IS NULL
        ORDER BY u.nome ASC;
        """,
        (ROLE_CONSULTOR,),
    )
    return [dict(row) for row in cur.fetchall()]


def _validar_agencia_pai(cur, id_agencia_pai: int | None, tipo: str) -> str | None:
    if tipo == "agencia" and id_agencia_pai:
        return "Consultor do tipo agência não pode ter agência pai."
    if id_agencia_pai is None:
        return None
    cur.execute(
        """
        SELECT id FROM public.dx_consultores
        WHERE id = %s AND tipo = 'agencia' AND ativo = TRUE;
        """,
        (id_agencia_pai,),
    )
    if not cur.fetchone():
        return "Agência pai inválida ou inativa."
    return None


def validar_payload_consultor(
    cur,
    data: dict,
    *,
    criar: bool,
    consultor_id: int | None = None,
) -> tuple[dict | None, str | None]:
    if not isinstance(data, dict):
        return None, "JSON inválido."

    payload: dict[str, Any] = {}

    if criar and data.get("user_id") is None:
        return None, "user_id é obrigatório."

    if "user_id" in data and data.get("user_id") is not None:
        try:
            payload["user_id"] = int(data["user_id"])
        except (TypeError, ValueError):
            return None, "user_id inválido."

    tipo_atual = None
    if "tipo" in data:
        tipo_atual = (data.get("tipo") or "individual").strip().lower()
        if tipo_atual not in TIPOS_CONSULTOR:
            return None, "tipo inválido (agencia ou individual)."
        payload["tipo"] = tipo_atual
    elif criar:
        payload["tipo"] = "individual"
        tipo_atual = "individual"

    if "id_agencia_pai" in data:
        id_agencia_pai = data.get("id_agencia_pai")
        if id_agencia_pai in (None, "", "null"):
            payload["id_agencia_pai"] = None
        else:
            try:
                payload["id_agencia_pai"] = int(id_agencia_pai)
            except (TypeError, ValueError):
                return None, "id_agencia_pai inválido."

    tipo_validacao = tipo_atual
    if not tipo_validacao and consultor_id:
        cur.execute("SELECT tipo FROM public.dx_consultores WHERE id = %s;", (consultor_id,))
        row = cur.fetchone()
        if row:
            tipo_validacao = row["tipo"] if isinstance(row, dict) else row[0]

    if "id_agencia_pai" in payload and tipo_validacao:
        err_ag = _validar_agencia_pai(cur, payload.get("id_agencia_pai"), tipo_validacao)
        if err_ag:
            return None, err_ag

    for field, key in (
        ("taxa_comissao_venda", "taxa_comissao_venda"),
        ("taxa_comissao_tecnica", "taxa_comissao_tecnica"),
    ):
        if key in data:
            try:
                valor = float(data[key])
            except (TypeError, ValueError):
                return None, f"{field} inválido."
            if valor < 0 or valor > 100:
                return None, f"{field} deve estar entre 0 e 100."
            payload[key] = valor

    if "ativo" in data:
        payload["ativo"] = bool(data["ativo"])

    if criar:
        cur.execute(
            "SELECT id_usuario, system_role FROM public.paneldx_usuarios WHERE id_usuario = %s;",
            (payload["user_id"],),
        )
        usuario = cur.fetchone()
        if not usuario:
            return None, "Usuário não encontrado."
        if (usuario["system_role"] if isinstance(usuario, dict) else usuario[1]) != ROLE_CONSULTOR:
            return None, "Usuário deve ter system_role consultor."
        cur.execute(
            "SELECT id FROM public.dx_consultores WHERE user_id = %s;",
            (payload["user_id"],),
        )
        if cur.fetchone():
            return None, "Usuário já possui perfil de consultor."

    if consultor_id and payload.get("id_agencia_pai") == consultor_id:
        return None, "Consultor não pode ser agência pai de si mesmo."

    if criar:
        payload.setdefault("taxa_comissao_venda", DEFAULT_TAXA_VENDA)
        payload.setdefault("taxa_comissao_tecnica", DEFAULT_TAXA_TECNICA)
    return payload, None


def _fetch_scalar_id(row) -> int:
    if row is None:
        raise ValueError("Registro não encontrado.")
    return int(row["id"] if isinstance(row, dict) else row[0])


def ensure_consultor_profile(
    cur,
    user_id: int,
    *,
    tipo: str = "individual",
    id_agencia_pai: int | None = None,
    taxa_comissao_venda: float = DEFAULT_TAXA_VENDA,
    taxa_comissao_tecnica: float = DEFAULT_TAXA_TECNICA,
) -> int:
    """Garante registro em dx_consultores para usuário consultor. Retorna id do perfil."""
    cur.execute(
        "SELECT id FROM public.dx_consultores WHERE user_id = %s;",
        (user_id,),
    )
    existente = cur.fetchone()
    if existente:
        cur.execute(
            """
            UPDATE public.dx_consultores
            SET ativo = TRUE,
                atualizado_em = NOW()
            WHERE user_id = %s
            RETURNING id;
            """,
            (user_id,),
        )
        return _fetch_scalar_id(cur.fetchone())

    cur.execute(
        """
        INSERT INTO public.dx_consultores
            (user_id, tipo, id_agencia_pai, taxa_comissao_venda, taxa_comissao_tecnica, ativo)
        VALUES (%s, %s, %s, %s, %s, TRUE)
        RETURNING id;
        """,
        (
            user_id,
            tipo,
            id_agencia_pai,
            taxa_comissao_venda,
            taxa_comissao_tecnica,
        ),
    )
    return _fetch_scalar_id(cur.fetchone())


def criar_consultor(cur, payload: dict) -> dict:
    cur.execute(
        """
        INSERT INTO public.dx_consultores
            (user_id, tipo, id_agencia_pai, taxa_comissao_venda, taxa_comissao_tecnica, ativo)
        VALUES (%s, %s, %s, %s, %s, TRUE)
        RETURNING id;
        """,
        (
            payload["user_id"],
            payload["tipo"],
            payload.get("id_agencia_pai"),
            payload.get("taxa_comissao_venda", DEFAULT_TAXA_VENDA),
            payload.get("taxa_comissao_tecnica", DEFAULT_TAXA_TECNICA),
        ),
    )
    consultor_id = _fetch_scalar_id(cur.fetchone())
    row = buscar_consultor_por_id(cur, consultor_id)
    if not row:
        raise ValueError("Falha ao criar perfil de consultor.")
    return serializar_consultor(row)


def atualizar_consultor(cur, consultor_id: int, payload: dict) -> dict:
    sets = []
    values = []
    for key in ("tipo", "id_agencia_pai", "taxa_comissao_venda", "taxa_comissao_tecnica", "ativo"):
        if key in payload:
            sets.append(f"{key} = %s")
            values.append(payload[key])
    if not sets:
        row = buscar_consultor_por_id(cur, consultor_id)
        if not row:
            raise ValueError("Consultor não encontrado.")
        return serializar_consultor(row)

    sets.append("atualizado_em = NOW()")
    values.append(consultor_id)
    cur.execute(
        f"""
        UPDATE public.dx_consultores
        SET {", ".join(sets)}
        WHERE id = %s
        RETURNING id;
        """,
        tuple(values),
    )
    if not cur.fetchone():
        raise ValueError("Consultor não encontrado.")
    row = buscar_consultor_por_id(cur, consultor_id)
    return serializar_consultor(row)


def desativar_consultor(cur, consultor_id: int) -> None:
    cur.execute(
        """
        UPDATE public.dx_consultores
        SET ativo = FALSE, atualizado_em = NOW()
        WHERE id = %s
        RETURNING id;
        """,
        (consultor_id,),
    )
    if not cur.fetchone():
        raise ValueError("Consultor não encontrado.")
