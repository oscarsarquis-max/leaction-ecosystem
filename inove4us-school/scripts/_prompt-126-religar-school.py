#!/usr/bin/env python3
"""126 — mínimo institucional: convite Equipe + 1 turma + 1 alocação (Escola Teste)."""
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
GESTOR_SESSION = "admin@escolateste.edu.br"


def gestor_session(email: str) -> dict:
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
        raise SystemExit(f"gestor não encontrado: {email}")
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


def catalog() -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT u.id::text AS unidade_id, u.nome AS unidade_nome
                  FROM public.school_unidades u
                 WHERE u.instituicao_id = %s AND u.ativo IS NOT FALSE
                 ORDER BY u.nome LIMIT 1
                """,
                (INST,),
            )
            unidade = dict(cur.fetchone() or {})
            cur.execute(
                """
                SELECT id::text AS periodo_id, rotulo, ano_letivo
                  FROM public.school_periodos_letivos
                 WHERE instituicao_id = %s AND ativo IS NOT FALSE
                 ORDER BY ano_letivo DESC LIMIT 1
                """,
                (INST,),
            )
            periodo = dict(cur.fetchone() or {})
            cur.execute(
                """
                SELECT c.id::text AS curso_id, c.nome AS curso_nome, c.nivel, c.turma_turno,
                       d.id::text AS disciplina_id, d.nome AS disciplina_nome
                  FROM public.school_curso_disciplinas cd
                  JOIN public.school_cursos c ON c.id = cd.curso_id
                  JOIN public.school_disciplinas d ON d.id = cd.disciplina_id
                  JOIN public.school_periodos_letivos p ON p.id = c.periodo_letivo_id
                 WHERE p.instituicao_id = %s AND p.id = %s::uuid
                 ORDER BY
                    CASE WHEN d.nome ILIKE 'matem%%' THEN 0 ELSE 1 END,
                    CASE WHEN c.nome ILIKE '%%6%%' OR c.nivel ILIKE '%%6%%' THEN 0 ELSE 1 END,
                    c.nome, d.nome
                 LIMIT 1
                """,
                (INST, periodo["periodo_id"]),
            )
            pick = dict(cur.fetchone() or {})
    return {"unidade": unidade, "periodo": periodo, "pick": pick}


def slim(resp):
    body = resp.get_json(silent=True) or {}
    return {"http": resp.status_code, "body": body}


def main() -> int:
    from app import app

    cat = catalog()
    pick = cat["pick"]
    if not pick.get("curso_id") or not pick.get("disciplina_id"):
        print(json.dumps({"ok": False, "reason": "catalogo_sem_curso_disciplina", "cat": cat}, default=str))
        return 2

    admin = gestor_session(GESTOR_SESSION)
    oper = gestor_session("operacional@escolateste.edu.br")
    out = {"prompt": 126, "catalog": cat}

    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = admin

    r_inv = c.post(
        f"/api/instituicoes/{INST}/equipe/convites",
        json={"email": HOMOLOG},
    )
    inv = slim(r_inv)
    out["convite"] = inv
    membro = (inv.get("body") or {}).get("membro") or {}
    vinculo_id = membro.get("id")
    if inv["http"] not in (200, 201) or not vinculo_id:
        print(json.dumps({"ok": False, "reason": "convite_falhou", **out}, default=str, ensure_ascii=False, indent=2))
        return 3

    r_disp = c.post(f"/api/instituicoes/{INST}/equipe/{vinculo_id}/disparar-convite")
    out["disparar"] = slim(r_disp)

    with c.session_transaction() as sess:
        sess["school_gestor"] = oper

    serie = (pick.get("nivel") or pick.get("curso_nome") or "6º ano")[:40]
    r_turma = c.post(
        "/api/secretaria/turmas",
        json={
            "nome": "6º Ano A",
            "serie_ano": serie if serie else "6º ano",
            "turno": "manha",
            "unidade_id": cat["unidade"]["unidade_id"],
            "periodo_letivo_id": cat["periodo"]["periodo_id"],
            "curso_id": pick["curso_id"],
        },
    )
    turma_j = slim(r_turma)
    out["turma"] = turma_j
    item = (turma_j.get("body") or {}).get("item") or {}
    turma_id = item.get("id")
    if turma_j["http"] == 409:
        r_list = c.get("/api/secretaria/turmas")
        items = (r_list.get_json(silent=True) or {}).get("items") or []
        hit = next((t for t in items if (t.get("nome") or "") == "6º Ano A"), None)
        out["turma_existing"] = hit
        turma_id = (hit or {}).get("id")
    if not turma_id:
        print(json.dumps({"ok": False, "reason": "turma_falhou", **out}, default=str, ensure_ascii=False, indent=2))
        return 4

    r_aloc = c.post(
        "/api/secretaria/alocacoes",
        json={
            "unidade_id": cat["unidade"]["unidade_id"],
            "periodo_id": cat["periodo"]["periodo_id"],
            "disciplina_id": pick["disciplina_id"],
            "professor_id": vinculo_id,
            "turma_id": turma_id,
        },
    )
    out["alocacao"] = slim(r_aloc)
    aloc_ok = r_aloc.status_code in (200, 201)
    out["ok"] = bool(vinculo_id and turma_id and aloc_ok)
    out["ids"] = {
        "vinculo_id": vinculo_id,
        "turma_id": turma_id,
        "curso_id": pick["curso_id"],
        "curso_nome": pick.get("curso_nome"),
        "disciplina_id": pick["disciplina_id"],
        "disciplina_nome": pick.get("disciplina_nome"),
        "alocacao_id": ((out["alocacao"].get("body") or {}).get("item") or {}).get("id"),
    }
    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
    return 0 if out["ok"] else 5


if __name__ == "__main__":
    raise SystemExit(main())
