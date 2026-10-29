#!/usr/bin/env python3
"""116 — ativa versão da escola das condições AEE ainda não ativas.

Não mexe em TDAH (já ativo). Prefixo só em PEI de teste, não no texto AEE
(o conteúdo ativado é o da diretriz da escola + lote 79/81).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/var/www/inove4us-school")
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from aee_canonico import CONDICOES_ORDEM  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402
from db import get_conn  # noqa: E402

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"


def gestor():
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
            if not row:
                raise SystemExit("homologador não encontrado")
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


def client():
    from app import app

    user = gestor()
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["school_gestor"] = user
    return c


def slim(m):
    if not m:
        return None
    return {
        "id": m.get("id"),
        "versao": m.get("versao"),
        "status": m.get("status"),
        "coord": m.get("assinado_coordenador"),
        "psico": m.get("assinado_psicopedagogo"),
    }


def ativar(c, condicao: str) -> dict:
    r = c.get("/api/aee/matriz", query_string={"condicao": condicao})
    body = r.get_json(silent=True) or {}
    if r.status_code != 200:
        return {"condicao": condicao, "error": "get_matriz", "http": r.status_code, "body": body}
    if (body.get("ativa") or {}).get("status") == "ativo":
        return {"condicao": condicao, "skipped": "ja_ativo", "ativa": slim(body.get("ativa"))}
    edit = body.get("editavel") or body.get("atual")
    if not edit or not edit.get("id"):
        return {"condicao": condicao, "error": "sem_rascunho", "get": {k: slim(body.get(k)) for k in ("ativa", "aguardando", "editavel")}}
    texto = edit.get("texto_escola") or ""
    campos = edit.get("campos_experiencia_metodologica") or ""
    env = c.post(
        f"/api/aee/matriz/{edit['id']}/enviar-aprovacao",
        json={"texto_escola": texto, "campos_experiencia_metodologica": campos},
    )
    envb = env.get_json(silent=True) or {}
    mid = (envb.get("matriz") or {}).get("id")
    if env.status_code not in (200, 201) or not mid:
        return {
            "condicao": condicao,
            "error": "enviar",
            "http": env.status_code,
            "body": envb,
        }
    c1 = c.post(
        "/api/aee/matriz/assinar/coordenador",
        json={"matriz_id": mid, "condicao_categoria": condicao},
    )
    b1 = c1.get_json(silent=True) or {}
    dup = c.post(
        "/api/aee/matriz/assinar/coordenador",
        json={"matriz_id": mid, "condicao_categoria": condicao},
    )
    c2 = c.post(
        "/api/aee/matriz/assinar/psicopedagogo",
        json={"matriz_id": mid, "condicao_categoria": condicao},
    )
    b2 = c2.get_json(silent=True) or {}
    reload = c.get("/api/aee/matriz", query_string={"condicao": condicao}).get_json(silent=True) or {}
    return {
        "condicao": condicao,
        "enviar_http": env.status_code,
        "aguardando_id": mid,
        "coord": {"http": c1.status_code, "status": (b1.get("matriz") or {}).get("status"), "message": b1.get("message")},
        "coord_de_novo": {"http": dup.status_code, "error": (dup.get_json(silent=True) or {}).get("error")},
        "psico": {"http": c2.status_code, "status": (b2.get("matriz") or {}).get("status"), "message": b2.get("message")},
        "reload_ativa": slim(reload.get("ativa")),
        "reload_aguardando": slim(reload.get("aguardando")),
    }


def main() -> int:
    c = client()
    out = {"passos": []}
    for cond in CONDICOES_ORDEM:
        out["passos"].append(ativar(c, cond))
    final = []
    for cond in CONDICOES_ORDEM:
        body = c.get("/api/aee/matriz", query_string={"condicao": cond}).get_json(silent=True) or {}
        final.append({"condicao": cond, "ativa": slim(body.get("ativa"))})
    out["final"] = final
    out["todas_ativas"] = all((x.get("ativa") or {}).get("status") == "ativo" for x in final)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["todas_ativas"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
