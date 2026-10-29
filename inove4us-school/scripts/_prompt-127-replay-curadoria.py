#!/usr/bin/env python3
"""127 — reprocessar LESSON_RECORD_SYNC slim (nginx recusou JWT grande) + incorporar."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from webhook_b2c_routes import _handle_lesson_record_sync  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
DID = "3221a3a5-0a5b-4a7a-bb40-8de21bfd9097"
HOMOLOG = "homologador@leaction.com.br"
SUG = (
    "Na Auditoria de Divergência, o Minute Paper de saída funcionou melhor em duplas "
    "heterogêneas: um aluno mede, o outro registra na planta. Sugiro formalizar esse "
    "pareamento na diretriz da escola para a Abordagem Problematizadora."
)
RETORNO = (
    "Combinado: formalizamos o pareamento heterogêneo (um mede, outro registra) "
    "na diretriz da Abordagem Problematizadora da Escola Teste. Siga assim nas "
    "próximas aulas do Campus 2.0."
)


def gestor():
    from psycopg2.extras import RealDictCursor
    from db import get_conn

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT g.id, g.instituicao_id, g.unidade_id, g.nome, g.email, g.cargo,
                       i.razao_social AS instituicao_nome,
                       COALESCE(array_agg(p.zona ORDER BY p.zona) FILTER (WHERE p.ativo), '{}') AS zonas
                  FROM public.school_gestores g
                  JOIN public.school_instituicoes i ON i.id = g.instituicao_id
                  LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                 WHERE g.instituicao_id = %s AND lower(g.email) = %s
                 GROUP BY g.id, i.razao_social
                """,
                (INST, HOMOLOG),
            )
            row = cur.fetchone()
    return {
        "id": str(row["id"]),
        "instituicao_id": str(row["instituicao_id"]),
        "instituicao_nome": row.get("instituicao_nome"),
        "unidade_id": str(row["unidade_id"]) if row.get("unidade_id") else None,
        "nome": row["nome"],
        "email": row["email"],
        "cargo": row["cargo"],
        "zonas": list(row["zonas"] or []),
    }


def main():
    payload = {
        "instituicao_id": INST,
        "origem_plano_b2c_id": DID,
        "desafio_grupo_id": DID,
        "id_evento": 69,
        "origem_aula_b2c_id": "69",
        "tipo_aula": "desafio",
        "status": "aprovado",
        "professor_email": HOMOLOG,
        "email": HOMOLOG,
        "professor_b2c_id": "21",
        "professor_id": "21",
        "professor_nome": "Homologador",
        "turma_nome": "1ª Série A",
        "turma": "1ª Série A",
        "metodologia_nome": "Abordagem Problematizadora",
        "metodologia_usada": "Abordagem Problematizadora",
        "conteudo_resumo": "Operação Campus 2.0 — 1ª Série A — Noite",
        "semana_referencia": "2026-09-15",
        "has_teacher_adaptations": True,
        "teacher_adaptation_text": SUG,
        "texto_sugestao": SUG,
        "aula_contexto": "Operação Campus 2.0 — noite, 1ª Série A",
        "desafio_titulo": "Operação Campus 2.0 — Projeto Executivo",
        "mesa": {
            "id": "69",
            "origem_aula_b2c_id": "69",
            "titulo": "Operação Campus 2.0 — 1ª Série A — Noite",
            "tipo_aula": "desafio",
            "status": "concluido",
            "metodologia_nome": "Abordagem Problematizadora",
            "has_teacher_adaptations": True,
            "teacher_adaptation_text": SUG,
            "texto_sugestao": SUG,
            "aula_contexto": "Operação Campus 2.0 — noite, 1ª Série A",
            "professor_id": "21",
            "professor_nome": "Homologador",
            "desafio_grupo_id": DID,
            "turma_nome": "1ª Série A",
        },
    }
    sync = _handle_lesson_record_sync(payload)

    from app import app

    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = gestor()
    pend = c.get("/api/pedagogico/curadoria/pendentes").get_json(silent=True) or {}
    items = pend.get("items") or []
    grupos = pend.get("grouped") or pend.get("grupos") or []
    if not items:
        for g in grupos if isinstance(grupos, list) else []:
            if isinstance(g, dict):
                items.extend(g.get("items") or g.get("itens") or [])
        if isinstance(grupos, dict):
            for v in grupos.values():
                if isinstance(v, list):
                    items.extend(v)
    alvo = None
    for it in items:
        if isinstance(it, dict) and it.get("id"):
            alvo = it
            break
    cur_id = (sync or {}).get("curadoria_id") or (alvo or {}).get("id")
    inc = None
    if cur_id:
        r = c.post(
            f"/api/pedagogico/curadoria/{cur_id}/incorporar",
            json={"retorno_docente": RETORNO},
        )
        inc = {"http": r.status_code, "body": r.get_json(silent=True)}
    radar = c.get("/api/pedagogico/curadoria-pendente").get_json(silent=True) or {}
    print(json.dumps({
        "sync": sync,
        "pendentes_total": pend.get("total"),
        "alvo": (alvo or {}).get("id"),
        "cur_id": cur_id,
        "incorporar": inc,
        "radar_n": len(radar.get("itens") or radar.get("items") or []),
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
