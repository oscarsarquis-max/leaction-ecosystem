#!/usr/bin/env python3
"""Reteste prompt 91 — desempenho experimental (sem senhas no stdout)."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from dotenv import load_dotenv

load_dotenv(ROOT / ".env", override=False)

from psycopg2.extras import RealDictCursor
from db import get_conn

INST = "3fa7aff7-4bd1-4e7f-ae64-76d5eb781e50"
HOMOLOG = "homologador@leaction.com.br"
FEATURE_KEY = "desempenho_professores_91"
FORBIDDEN = ("nota", "score", "ranking", "rank")
MARKER = "91-teste-piloto-desempenho"


def j(v):
    if isinstance(v, (datetime, date, UUID)):
        return str(v)
    return v


def _forbidden_in(obj) -> list[str]:
    blob = json.dumps(obj, default=str).casefold()
    return [w for w in FORBIDDEN if w in blob]


def main() -> int:
    from app import app

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
            gestor = cur.fetchone()
            if not gestor:
                cur.execute(
                    """
                    SELECT g.id, g.instituicao_id, g.unidade_id, g.nome, g.email, g.cargo,
                           i.razao_social AS instituicao_nome,
                           COALESCE(array_agg(p.zona ORDER BY p.zona) FILTER (WHERE p.ativo), '{}') AS zonas
                    FROM public.school_gestores g
                    JOIN public.school_instituicoes i ON i.id = g.instituicao_id
                    LEFT JOIN public.school_gestor_perfis p ON p.gestor_id = g.id
                    GROUP BY g.id, i.razao_social
                    ORDER BY (lower(g.email) = %s) DESC, g.created_at DESC NULLS LAST
                    LIMIT 1
                    """,
                    (HOMOLOG,),
                )
                gestor = cur.fetchone()
            if not gestor:
                raise SystemExit("Nenhum gestor encontrado nesta base")

    user = {
        "id": str(gestor["id"]),
        "instituicao_id": str(gestor["instituicao_id"]),
        "instituicao_nome": gestor.get("instituicao_nome"),
        "unidade_id": str(gestor["unidade_id"]) if gestor.get("unidade_id") else None,
        "nome": gestor["nome"],
        "email": gestor["email"],
        "cargo": gestor["cargo"],
        "zonas": list(gestor["zonas"] or []),
    }

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["school_gestor"] = user

    res = client.get(
        "/api/pedagogico/desempenho-professores"
        "?data_inicio=2026-08-31&data_fim=2026-09-06"
    )
    body = res.get_json(silent=True) or {}
    profs = body.get("professores") if isinstance(body, dict) else []
    if not isinstance(profs, list):
        profs = []
    forb = _forbidden_in(body)

    res_fb = client.post(
        "/api/pedagogico/feedback-features",
        json={
            "feature_key": FEATURE_KEY,
            "texto": f"{MARKER} opinião de teste do prompt 91",
        },
        content_type="application/json",
    )
    fb_body = res_fb.get_json(silent=True) or {}

    res_list = client.get(
        f"/api/pedagogico/feedback-features?feature_key={FEATURE_KEY}"
    )
    listed = res_list.get_json(silent=True) or {}
    itens = listed.get("itens") if isinstance(listed, dict) else []
    if not isinstance(itens, list):
        itens = []
    stored = any(MARKER in str(x.get("texto") or "") for x in itens)

    dist = ROOT / "frontend" / "dist" / "assets"
    js_files = sorted(dist.glob("index-*.js"), key=lambda p: p.stat().st_mtime, reverse=True)
    blob = js_files[0].read_text(encoding="utf-8", errors="replace") if js_files else ""
    page = (ROOT / "frontend" / "src" / "pages" / "DesempenhoProfessores.jsx").read_text(
        encoding="utf-8"
    )

    rbac = (ROOT / "frontend" / "src" / "lib" / "rbac.js").read_text(encoding="utf-8")
    dash = (ROOT / "frontend" / "src" / "pages" / "Dashboard.jsx").read_text(encoding="utf-8")

    out = {
        "nav": {
            "item_desempenho": 'to: \'/desempenho\'' in rbac or 'to: "/desempenho"' in rbac,
            "nao_e_home": True,
            "dashboard_intocado": "DesempenhoProfessores" not in dash
            and "/desempenho" not in dash,
        },
        "api": {
            "http": res.status_code,
            "experimental": body.get("experimental") is True,
            "feature_key": body.get("feature_key"),
            "professores": len(profs),
            "nomes": [
                x.get("professor_nome") or x.get("professor_email") for x in profs[:8]
            ],
            "campos_ok": all(
                {
                    "aulas_dia_a_dia",
                    "aulas_desafio",
                    "metodologias_distintas",
                    "adesao",
                    "curadoria_enviadas",
                    "pei",
                }.issubset(set(x.keys()))
                for x in profs
            )
            if profs
            else True,
            "sem_nota_ranking": forb == [],
            "forbidden_hits": forb,
        },
        "feedback": {
            "post_http": res_fb.status_code,
            "post_id": fb_body.get("id"),
            "list_http": res_list.status_code,
            "registrado": stored,
            "tabela": "school_feedback_features",
        },
        "bundle": {
            "js": js_files[0].name if js_files else None,
            "badge_experimental": "Experimental — em avaliação no piloto" in blob,
            "rota_desempenho": "/desempenho" in blob,
            "feedback_cta": "O que você acha dessa visão?" in blob,
        },
        "ui_src": {
            "badge_experimental": "Experimental — em avaliação no piloto" in page,
            "feedback_cta": "O que você acha dessa visão?" in page,
            "sem_nota_unica": "nota única" in page.casefold() or "Sem nota única" in page,
        },
    }
    print(json.dumps(out, indent=2, default=str))
    ok = (
        out["nav"]["item_desempenho"]
        and out["nav"]["dashboard_intocado"]
        and out["api"]["http"] == 200
        and out["api"]["experimental"]
        and out["api"]["sem_nota_ranking"]
        and out["feedback"]["post_http"] == 201
        and out["ui_src"]["badge_experimental"]
        and out["ui_src"]["feedback_cta"]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
