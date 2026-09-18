"""153 — Evento único. Dual-write: broadcast → Comunicados (114); aula → Planejamento (104)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from auth_guards import current_gestor

TZ_ESCOLA = ZoneInfo("America/Sao_Paulo")

EVENTO_TIPOS = frozenset({"aula", "planejamento", "treinamento", "civico", "geral"})
BROADCAST_TIPOS = frozenset({"planejamento", "treinamento", "civico", "geral"})

EVENTO_TO_COM_TIPO = {
    "planejamento": "reuniao_pedagogica",
    "treinamento": "evento_escolar",
    "civico": "evento_escolar",
    "geral": "evento_escolar",
}
COM_TIPO_TO_EVENTO = {
    "reuniao_pedagogica": "planejamento",
    "evento_escolar": "geral",
}

EVENTO_TIPO_LABEL = {
    "aula": "Aula",
    "planejamento": "Planejamento",
    "treinamento": "Treinamento",
    "civico": "Cívico",
    "geral": "Geral",
}

PUBLICO_LABEL = {
    "toda_instituicao": "Toda a instituição",
    "unidade": "Unidade",
    "turma": "Turma",
    "professores": "Professores",
    "disciplina": "Disciplina",
    "administradores": "Administradores",
}


def normalize_tipo_evento(raw: Any) -> str | None:
    text = str(raw or "").strip().lower()
    if not text:
        return None
    folded = (
        text.replace("í", "i")
        .replace("ì", "i")
        .replace("î", "i")
        .replace("ï", "i")
    )
    if folded in EVENTO_TIPOS:
        return folded
    return None


def com_tipo_for_evento(tipo_evento: str) -> str:
    return EVENTO_TO_COM_TIPO.get(tipo_evento, "evento_escolar")


def evento_tipo_from_comunicado(tipo: str) -> str:
    return COM_TIPO_TO_EVENTO.get(str(tipo or ""), "geral")


def gestor_ve_administradores() -> bool:
    user = current_gestor() or {}
    raw = [str(z).strip() for z in (user.get("zonas") or []) if z]
    return "administrativo" in raw


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def serialize_evento(row: dict[str, Any]) -> dict[str, Any]:
    tipo = str(row.get("tipo_evento") or "")
    publico = row.get("publico_alvo")
    status = str(row.get("status") or "")
    return {
        "id": str(row["id"]),
        "tipo_evento": tipo,
        "tipo_label": EVENTO_TIPO_LABEL.get(tipo, tipo),
        "titulo": row.get("titulo") or "",
        "descricao": row.get("descricao") or "",
        "data_hora_inicio": _iso(row.get("data_hora_inicio")),
        "data_hora_fim": _iso(row.get("data_hora_fim")),
        "publico_alvo": publico,
        "publico_label": PUBLICO_LABEL.get(str(publico or ""), publico),
        "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
        "unidade_nome": row.get("unidade_nome"),
        "turma_id": str(row["turma_id"]) if row.get("turma_id") else None,
        "turma_nome": row.get("turma_nome"),
        "disciplina_id": str(row["disciplina_id"]) if row.get("disciplina_id") else None,
        "disciplina_nome": row.get("disciplina_nome"),
        "professor_vinculo_id": (
            str(row["professor_vinculo_id"]) if row.get("professor_vinculo_id") else None
        ),
        "professor_email": row.get("professor_email"),
        "professor_b2c_id": row.get("professor_b2c_id"),
        "substituicao": bool(row.get("substituicao")),
        "substitui_evento_id": (
            str(row["substitui_evento_id"]) if row.get("substitui_evento_id") else None
        ),
        "status": status,
        "origem_comunicado_id": (
            str(row["origem_comunicado_id"]) if row.get("origem_comunicado_id") else None
        ),
        "origem_planejamento_id": (
            str(row["origem_planejamento_id"]) if row.get("origem_planejamento_id") else None
        ),
        "replicado_b2c": bool(row.get("replicado_b2c")),
        "replicado_b2c_em": _iso(row.get("replicado_b2c_em")),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "source": "aula" if tipo == "aula" else "broadcast",
    }


EVENTO_SELECT = """
    SELECT e.*,
           u.nome AS unidade_nome,
           t.nome AS turma_nome,
           d.nome AS disciplina_nome,
           v.email_convite AS professor_email,
           v.professor_b2c_id
    FROM public.school_eventos e
    LEFT JOIN public.school_unidades u ON u.id = e.unidade_id
    LEFT JOIN public.school_turmas t ON t.id = e.turma_id
    LEFT JOIN public.school_disciplinas d ON d.id = e.disciplina_id
    LEFT JOIN public.school_professores_vinculo v ON v.id = e.professor_vinculo_id
"""


def fetch_evento(cur, inst: str, eid: str):
    cur.execute(
        EVENTO_SELECT + " WHERE e.id = %s AND e.instituicao_id = %s",
        (eid, inst),
    )
    return cur.fetchone()


def upsert_from_comunicado(cur, row: dict[str, Any], tipo_evento: str | None = None) -> None:
    tipo = tipo_evento or evento_tipo_from_comunicado(str(row.get("tipo") or ""))
    if tipo not in BROADCAST_TIPOS:
        tipo = "geral"
    cur.execute(
        """
        INSERT INTO public.school_eventos (
            instituicao_id, tipo_evento, titulo, descricao,
            data_hora_inicio, data_hora_fim, publico_alvo,
            unidade_id, turma_id, disciplina_id, status,
            origem_comunicado_id, replicado_b2c, replicado_b2c_em,
            criado_por_gestor_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (origem_comunicado_id) DO UPDATE SET
            tipo_evento = EXCLUDED.tipo_evento,
            titulo = EXCLUDED.titulo,
            descricao = EXCLUDED.descricao,
            data_hora_inicio = EXCLUDED.data_hora_inicio,
            data_hora_fim = EXCLUDED.data_hora_fim,
            publico_alvo = EXCLUDED.publico_alvo,
            unidade_id = EXCLUDED.unidade_id,
            turma_id = EXCLUDED.turma_id,
            disciplina_id = EXCLUDED.disciplina_id,
            status = EXCLUDED.status,
            replicado_b2c = EXCLUDED.replicado_b2c,
            replicado_b2c_em = EXCLUDED.replicado_b2c_em,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            str(row["instituicao_id"]),
            tipo,
            row["titulo"],
            row.get("descricao"),
            row.get("data_hora_inicio"),
            row.get("data_hora_fim"),
            row.get("publico_alvo"),
            row.get("unidade_id"),
            row.get("turma_id"),
            row.get("disciplina_id"),
            row.get("status") or "publicado",
            str(row["id"]),
            bool(row.get("replicado_b2c")),
            row.get("replicado_b2c_em"),
            str(row["criado_por_gestor_id"]) if row.get("criado_por_gestor_id") else None,
        ),
    )


def upsert_from_planejamento(cur, row: dict[str, Any]) -> None:
    data_ref = row.get("data")
    hi = row.get("hora_inicio")
    hf = row.get("hora_fim")
    inicio = None
    fim = None
    if data_ref:
        hi_s = str(hi)[:8] if hi else "12:00:00"
        hf_s = str(hf)[:8] if hf else "12:50:00"
        if len(hi_s) == 5:
            hi_s += ":00"
        if len(hf_s) == 5:
            hf_s += ":00"
        inicio = datetime.fromisoformat(f"{data_ref}T{hi_s}").replace(tzinfo=TZ_ESCOLA)
        fim = datetime.fromisoformat(f"{data_ref}T{hf_s}").replace(tzinfo=TZ_ESCOLA)
    if inicio is None:
        return
    status = {
        "enviado": "enviado",
        "erro": "erro",
        "rascunho": "rascunho",
        "cancelado": "cancelado",
    }.get(str(row.get("status_push") or ""), "rascunho")
    cur.execute(
        """
        INSERT INTO public.school_eventos (
            instituicao_id, tipo_evento, titulo, descricao,
            data_hora_inicio, data_hora_fim, publico_alvo,
            turma_id, disciplina_id, professor_vinculo_id,
            substituicao, status, origem_planejamento_id
        ) VALUES (
            %s, 'aula', %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (origem_planejamento_id) DO UPDATE SET
            titulo = EXCLUDED.titulo,
            descricao = EXCLUDED.descricao,
            data_hora_inicio = EXCLUDED.data_hora_inicio,
            data_hora_fim = EXCLUDED.data_hora_fim,
            turma_id = EXCLUDED.turma_id,
            disciplina_id = EXCLUDED.disciplina_id,
            professor_vinculo_id = EXCLUDED.professor_vinculo_id,
            substituicao = EXCLUDED.substituicao,
            status = EXCLUDED.status,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            str(row["instituicao_id"]),
            row["titulo"],
            row.get("observacoes"),
            inicio,
            fim,
            row.get("turma_id"),
            row.get("disciplina_id"),
            row.get("professor_vinculo_id"),
            bool(row.get("substituicao")),
            status,
            str(row["id"]),
        ),
    )
