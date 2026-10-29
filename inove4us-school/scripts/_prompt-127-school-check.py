#!/usr/bin/env python3
"""127 — snapshot School + incorporar curadoria pendente (retorno ao docente)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
ADMIN = "admin@escolateste.edu.br"
OPER = "operacional@escolateste.edu.br"
OUT = Path("/tmp/prompt-127-school-check.json")
RETORNO = (
    "Combinado: formalizamos o pareamento heterogêneo (um mede, outro registra) "
    "na diretriz da Abordagem Problematizadora da Escola Teste. Siga assim nas "
    "próximas aulas do Campus 2.0."
)


def gestor(email: str) -> dict:
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
                (INST, email),
            )
            row = cur.fetchone()
    if not row:
        raise SystemExit(f"gestor ausente: {email}")
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


def slim(d, keys):
    return {k: d.get(k) for k in keys if k in d}


def main():
    from app import app

    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = gestor(OPER)

    turmas = c.get("/api/secretaria/turmas").get_json(silent=True) or {}
    alunos = c.get("/api/secretaria/alunos").get_json(silent=True) or {}
    aloc = c.get("/api/secretaria/alocacoes").get_json(silent=True) or {}
    coms = c.get("/api/secretaria/comunicacoes").get_json(silent=True) or {}
    peis = c.get("/api/pei/alunos").get_json(silent=True) or {}

    with c.session_transaction() as sess:
        sess["school_gestor"] = gestor(ADMIN)
    pend = c.get("/api/pedagogico/curadoria/pendentes").get_json(silent=True) or {}
    radar = c.get("/api/pedagogico/curadoria-pendente").get_json(silent=True) or {}

    itens = pend.get("itens") or pend.get("items") or []
    grupos = pend.get("grupos") or []
    flat = list(itens)
    if not flat and grupos:
        for g in grupos:
            flat.extend(g.get("itens") or g.get("items") or [])
    if not flat:
        flat = radar.get("itens") or []

    alvo = None
    for it in flat:
        if isinstance(it, dict) and it.get("id") and it.get("status_analise") in (None, "pendente"):
            alvo = it
            break
    if not alvo and flat:
        alvo = flat[0]

    incorporar = None
    if alvo and alvo.get("id"):
        r = c.post(
            f"/api/pedagogico/curadoria/{alvo['id']}/incorporar",
            json={"retorno_docente": RETORNO},
        )
        incorporar = {
            "http": r.status_code,
            "body": r.get_json(silent=True),
            "alvo": alvo.get("id"),
            "metodologia": alvo.get("metodologia_nome"),
        }

    radar2 = c.get("/api/pedagogico/curadoria-pendente").get_json(silent=True) or {}

    t_items = turmas.get("items") or turmas.get("turmas") or []
    a_items = alunos.get("items") or alunos.get("alunos") or []
    al_items = aloc.get("items") or aloc.get("alocacoes") or []
    c_items = coms.get("items") or coms.get("comunicados") or []
    p_items = peis.get("items") or peis.get("alunos") or peis.get("peis") or []

    out = {
        "turmas": [{"id": t.get("id"), "nome": t.get("nome"), "curso": t.get("curso_nome") or t.get("curso"), "curso_id": t.get("curso_id")} for t in t_items],
        "alunos_n": len(a_items),
        "alunos": [{"id": a.get("id"), "nome": a.get("nome"), "turma": a.get("turma_nome") or a.get("turma"), "matricula": a.get("matricula")} for a in a_items],
        "alocacoes": [
            {
                "id": x.get("id"),
                "professor": x.get("professor_email") or x.get("email"),
                "turma": x.get("turma_nome") or x.get("turma"),
                "disciplina": x.get("disciplina_nome") or x.get("disciplina"),
                "status": x.get("status"),
            }
            for x in al_items
        ],
        "comunicados": [{"id": x.get("id"), "titulo": x.get("titulo"), "publico_alvo": x.get("publico_alvo"), "status": x.get("status")} for x in c_items],
        "peis": [
            {
                "id": x.get("id") or x.get("pei_id"),
                "aluno": x.get("aluno_nome") or x.get("nome"),
                "condicao": x.get("condicao") or x.get("condicao_categoria") or x.get("categoria"),
                "status": x.get("status") or x.get("status_documento"),
                "turma": x.get("turma_nome"),
            }
            for x in p_items
        ],
        "curadoria_pendente_antes": {"n": len(flat), "ids": [i.get("id") for i in flat[:8]]},
        "incorporar": incorporar,
        "radar_depois_n": len(radar2.get("itens") or []),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
