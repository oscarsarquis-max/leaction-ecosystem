#!/usr/bin/env python3
"""127 — PEI + curadoria com sessão do homologador (zona pedagógico)."""
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
HOMOLOG = "homologador@leaction.com.br"
RETORNO = (
    "Combinado: formalizamos o pareamento heterogêneo (um mede, outro registra) "
    "na diretriz da Abordagem Problematizadora da Escola Teste. Siga assim nas "
    "próximas aulas do Campus 2.0."
)


def gestor() -> dict:
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


def db_curadoria():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id::text, metodologia_nome, status_analise, created_at,
                       left(coalesce(sugestao_professor_json->>'teacher_adaptation_text',
                                     sugestao_professor_json->>'texto', ''), 180) AS trecho
                  FROM public.school_curadoria_metodologias
                 WHERE instituicao_id = %s
                 ORDER BY created_at DESC
                 LIMIT 8
                """,
                (INST,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            cur.execute(
                """
                SELECT p.id::text, a.nome AS aluno, m.condicao_categoria, p.status,
                       p.assinado_coordenador AS ass_coord,
                       p.assinado_psicopedagogo AS ass_psico,
                       left(coalesce(m.texto_escola, ''), 80) AS texto_escola_ini,
                       m.versao AS aee_versao
                  FROM public.school_pei_alunos p
                  JOIN public.school_alunos a ON a.id = p.aluno_id
                  JOIN public.school_aee_matrizes m ON m.id = p.aee_matriz_id
                 WHERE p.instituicao_id = %s AND p.status <> 'arquivado'
                 ORDER BY p.created_at
                """,
                (INST,),
            )
            peis = [dict(r) for r in cur.fetchall()]
    return rows, peis


def main():
    from app import app

    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = gestor()

    r_pei = c.get("/api/pei/alunos")
    pei_body = r_pei.get_json(silent=True)
    r_pend = c.get("/api/pedagogico/curadoria/pendentes")
    pend = r_pend.get_json(silent=True) or {}
    r_radar = c.get("/api/pedagogico/curadoria-pendente")
    radar = r_radar.get_json(silent=True) or {}
    r_acoes = c.get("/api/pedagogico/radar-home")
    acoes = r_acoes.get_json(silent=True) or {}

    db_c, db_p = db_curadoria()
    grupos = pend.get("grupos") or []
    flat = list(pend.get("itens") or pend.get("items") or [])
    for g in grupos:
        flat.extend(g.get("itens") or g.get("items") or [])
    if not flat:
        flat = radar.get("itens") or []
    if not flat:
        flat = [{"id": r["id"], "metodologia_nome": r.get("metodologia_nome"), "status_analise": r.get("status_analise")} for r in db_c if r.get("status_analise") == "pendente"]

    alvo = next((it for it in flat if it.get("id") and it.get("status_analise") in (None, "pendente")), None)
    incorporar = None
    if alvo:
        r = c.post(
            f"/api/pedagogico/curadoria/{alvo['id']}/incorporar",
            json={"retorno_docente": RETORNO},
        )
        incorporar = {"http": r.status_code, "body": r.get_json(silent=True), "alvo": alvo.get("id")}

    print(json.dumps({
        "zonas": gestor().get("zonas"),
        "pei_http": r_pei.status_code,
        "pei_n": len(pei_body) if isinstance(pei_body, list) else None,
        "peis_api": [
            {
                "id": x.get("id"),
                "aluno": x.get("aluno_nome"),
                "condicao": x.get("condicao_categoria"),
                "status": x.get("status"),
                "aee_versao": x.get("aee_versao"),
            }
            for x in (pei_body or []) if isinstance(x, dict)
        ] if isinstance(pei_body, list) else pei_body,
        "peis_db": db_p,
        "pendentes_http": r_pend.status_code,
        "pendentes_keys": list(pend.keys())[:10],
        "radar_http": r_radar.status_code,
        "radar_n": len(radar.get("itens") or []),
        "radar_home_keys": list(acoes.keys())[:12],
        "curadoria_db": db_c,
        "flat_n": len(flat),
        "incorporar": incorporar,
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
