"""Serviço de notificações operacionais."""

from __future__ import annotations

import json
from typing import Any

from psycopg2.extras import Json

from rbac.constants import NOTIF_NOVA_ATRIBUICAO
from rbac.users import rbac_resolver_id_usuario_por_member, rbac_sync_usuario_from_team_row


def rbac_criar_notificacao(
    cursor,
    *,
    user_id: int,
    tipo: str,
    mensagem: str,
    metadata: dict[str, Any] | None = None,
) -> int:
    cursor.execute(
        """
        INSERT INTO public.notificacoes (user_id, tipo, mensagem, metadata)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """,
        (user_id, tipo, mensagem, Json(metadata or {})),
    )
    row = cursor.fetchone()
    return int(row[0] if not isinstance(row, dict) else row["id"])


def rbac_notificar_nova_atribuicao(
    cursor,
    *,
    executor_id: int,
    nome_ativ: str,
    id_ativ: int,
    id_sprn: int | None = None,
    alteracao: bool = False,
) -> int | None:
    if not executor_id:
        return None

    id_usuario = rbac_resolver_id_usuario_por_member(cursor, executor_id)
    if not id_usuario:
        cursor.execute(
            "SELECT email, nome, role, position, password_hash FROM public.ctdi_team WHERE id_member = %s LIMIT 1;",
            (executor_id,),
        )
        row = cursor.fetchone()
        if row:
            if isinstance(row, dict):
                email, nome, role, position, pwd = (
                    row.get("email"), row.get("nome"), row.get("role"),
                    row.get("position"), row.get("password_hash"),
                )
            else:
                email, nome, role, position, pwd = row
            if email:
                id_usuario = rbac_sync_usuario_from_team_row(
                    cursor,
                    email=email,
                    nome=nome or email,
                    role=role,
                    position=position,
                    password_hash=pwd,
                )

    if not id_usuario:
        return None

    acao = "reatribuída" if alteracao else "atribuída"
    mensagem = f"Nova tarefa {acao}: «{nome_ativ}»."
    return rbac_criar_notificacao(
        cursor,
        user_id=id_usuario,
        tipo=NOTIF_NOVA_ATRIBUICAO,
        mensagem=mensagem,
        metadata={
            "id_ativ": id_ativ,
            "id_sprn": id_sprn,
            "alteracao": alteracao,
        },
    )


def rbac_sincronizar_executor_atividade(
    cursor,
    data: dict[str, Any],
    *,
    id_ativ_existente: int | None = None,
) -> tuple[dict[str, Any], int | None, bool]:
    """
    Garante executor_id, sincroniza id_team legado e dispara notificação se mudou.
    Retorna (data atualizado, executor_id anterior, notificação criada?).
    """
    executor_antigo = None
    if id_ativ_existente:
        cursor.execute(
            "SELECT executor_id, id_team, nome_ativ, id_sprn FROM public.ctdi_okr_atividades WHERE id_ativ = %s;",
            (id_ativ_existente,),
        )
        row = cursor.fetchone()
        if row:
            if isinstance(row, dict):
                executor_antigo = row.get("executor_id") or row.get("id_team")
                nome = row.get("nome_ativ") or data.get("nome_ativ") or "Tarefa"
                id_sprn = row.get("id_sprn")
            else:
                executor_antigo = row[0] or row[1]
                nome = row[2] or data.get("nome_ativ") or "Tarefa"
                id_sprn = row[3]
        else:
            nome = data.get("nome_ativ") or "Tarefa"
            id_sprn = data.get("id_sprn")
    else:
        nome = data.get("nome_ativ") or "Tarefa"
        id_sprn = data.get("id_sprn")

    executor_novo = data.get("executor_id") or data.get("id_team")
    if executor_novo is not None:
        try:
            executor_novo = int(executor_novo)
        except (TypeError, ValueError):
            executor_novo = None

    if executor_novo:
        data["executor_id"] = executor_novo
        data["id_team"] = executor_novo

    notif_id = None
    if executor_novo and executor_novo != executor_antigo:
        notif_id = rbac_notificar_nova_atribuicao(
            cursor,
            executor_id=executor_novo,
            nome_ativ=nome,
            id_ativ=id_ativ_existente or 0,
            id_sprn=id_sprn,
            alteracao=executor_antigo is not None,
        )

    return data, executor_antigo, notif_id is not None
